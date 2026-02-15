#!/usr/bin/env python3
"""
Water Balance API Module
Backend API for physics-informed water balance calculations

Implements the FAO water balance equation:
ET = P + I - R - ΔS

Where:
- ET: Evapotranspiration (Kc × ET₀)
- P: Precipitation
- I: Irrigation
- R: Runoff (SCS-CN method)
- ΔS: Change in soil water storage

Also provides VPD stress calculations and crop growth modeling
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import numpy as np
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Import physics layer components
from ml_pipeline.physics_layer import (
    PhysicsInformedLayer,
    WaterBalanceModule,
    CropGrowthModule,
    VPDStressModule,
    PhysicsConstants,
    calculate_vpd_numpy,
    calculate_et0_numpy,
    calculate_kc_from_ndvi_numpy,
    calculate_gdd_numpy,
    calculate_water_balance_numpy
)

# Import GEE service for satellite data
try:
    from gee_service import get_gee_service, GEEService
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class WaterBalanceResult:
    """Water balance calculation result"""
    date: str
    et0: float  # Reference ET (mm/day)
    etc: float  # Crop ET (mm/day)
    precipitation: float  # Rainfall (mm)
    irrigation: float  # Irrigation (mm)
    runoff: float  # Estimated runoff (mm)
    delta_s: float  # Change in soil storage (mm)
    water_balance: float  # Net balance (mm)
    vpd: float  # Vapor pressure deficit (kPa)
    vpd_stress: float  # VPD stress factor (0-1)
    kc: float  # Crop coefficient
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CropGrowthResult:
    """Crop growth calculation result"""
    date: str
    gdd: float  # Growing degree days
    accumulated_gdd: float  # Cumulative GDD
    lai: float  # Leaf area index
    kc: float  # Crop coefficient
    growth_stage: str  # Growth stage name
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PhysicsData:
    """Complete physics data for a location"""
    water_balance: List[Dict]
    crop_growth: List[Dict]
    vpd_analysis: List[Dict]
    yield_stress_factors: List[Dict]
    summary: Dict
    recommendations: List[str]


class WaterBalanceAPI:
    """
    API class for water balance and physics calculations
    Integrates IoT sensor data with satellite data from GEE
    """
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """
        Initialize Water Balance API
        
        Args:
            mongodb_uri: MongoDB connection URI
        """
        self.mongodb_uri = mongodb_uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.db_name = os.getenv('MONGODB_DATABASE', 'cropiot')
        
        # Initialize MongoDB connection
        self.mongo_client = None
        self.db = None
        self._init_mongodb()
        
        # Initialize GEE service
        self.gee_service: Optional[GEEService] = None
        if GEE_AVAILABLE:
            try:
                self.gee_service = get_gee_service()
                logger.info("GEE service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GEE service: {e}")
        
        # Physics modules (PyTorch-free for API use)
        self.physics_constants = PhysicsConstants()
        
        logger.info("Water Balance API initialized")
    
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.db_name]
            logger.info(f"Connected to MongoDB: {self.db_name}")
        except ConnectionFailure as e:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            self.db = None
    
    def get_sensor_data(self, start_date: str, end_date: str,
                        sensor_id: Optional[str] = None) -> List[Dict]:
        """
        Fetch sensor data from MongoDB
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sensor_id: Optional specific sensor ID
            
        Returns:
            List of sensor readings
        """
        if self.db is None:
            return []
        
        try:
            collection = self.db['sensor_data']
            
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            
            query = {
                'timestamp': {
                    '$gte': start_dt,
                    '$lt': end_dt
                }
            }
            
            if sensor_id:
                query['sensor_id'] = sensor_id
            
            cursor = collection.find(query).sort('timestamp', 1)
            
            data = []
            for doc in cursor:
                data.append({
                    'timestamp': doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'date': doc['timestamp'].strftime('%Y-%m-%d'),
                    'sensor_id': doc['sensor_id'],
                    'temperature': doc.get('temperature'),
                    'humidity': doc.get('humidity'),
                    'soil_moisture': doc.get('soil_moisture'),
                    'ph': doc.get('ph')
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching sensor data: {e}")
            return []
    
    def get_irrigation_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch irrigation data from MongoDB
        Currently returns mock data - integrate with irrigation sensors
        """
        if self.db is None:
            return []
        
        try:
            collection = self.db.get_collection('irrigation_events')
            if collection is None:
                return []
            
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            
            cursor = collection.find({
                'timestamp': {'$gte': start_dt, '$lt': end_dt}
            }).sort('timestamp', 1)
            
            return [{
                'date': doc['timestamp'].strftime('%Y-%m-%d'),
                'amount_mm': doc.get('amount_mm', 0)
            } for doc in cursor]
            
        except Exception:
            return []
    
    def calculate_water_balance(self, lat: float, lng: float,
                                 start_date: str, end_date: str,
                                 sensor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive water balance
        
        Integrates:
        - IoT sensor data (temperature, humidity, soil moisture)
        - GEE satellite data (NDVI, rainfall, ET, LST)
        - Physics calculations (VPD, Kc, GDD)
        
        Args:
            lat: Latitude
            lng: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sensor_id: Optional sensor ID filter
            
        Returns:
            Comprehensive water balance data
        """
        logger.info(f"Calculating water balance for ({lat}, {lng}) "
                   f"from {start_date} to {end_date}")
        
        # Fetch sensor data
        sensor_data = self.get_sensor_data(start_date, end_date, sensor_id)
        
        # Aggregate sensor data by date
        daily_sensor_data = self._aggregate_daily_sensor_data(sensor_data)
        
        # Fetch GEE data if available
        gee_data = {}
        if self.gee_service:
            try:
                gee_data = self.gee_service.fetch_comprehensive_data(
                    lat, lng, start_date, end_date
                )
            except Exception as e:
                logger.warning(f"Failed to fetch GEE data: {e}")
        
        # Calculate water balance
        water_balance = self._compute_water_balance(
            daily_sensor_data, gee_data, start_date, end_date
        )
        
        # Calculate crop growth parameters
        crop_growth = self._compute_crop_growth(
            daily_sensor_data, gee_data, start_date, end_date
        )
        
        # Calculate VPD analysis
        vpd_analysis = self._compute_vpd_analysis(
            daily_sensor_data, gee_data
        )
        
        # Calculate yield stress factors
        yield_stress = self._compute_yield_stress_factors(
            water_balance, vpd_analysis
        )
        
        # Generate summary and recommendations
        summary = self._generate_summary(water_balance, crop_growth, vpd_analysis)
        recommendations = self._generate_recommendations(summary)
        
        return {
            'success': True,
            'data': {
                'waterBalance': water_balance,
                'cropGrowth': crop_growth,
                'vpdAnalysis': vpd_analysis,
                'yieldStress': yield_stress,
                'ndvi': gee_data.get('ndvi', []),
                'rainfall': gee_data.get('rainfall', []),
                'et': gee_data.get('et', []),
                'kc': gee_data.get('kc', []),
                'deltaS': self._calculate_delta_s(daily_sensor_data),
            },
            'summary': summary,
            'recommendations': recommendations,
            'metadata': {
                'location': {'lat': lat, 'lng': lng},
                'dateRange': {'start': start_date, 'end': end_date},
                'dataSources': {
                    'sensors': len(sensor_data),
                    'gee': bool(gee_data)
                }
            }
        }
    
    def _aggregate_daily_sensor_data(self, sensor_data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate sensor readings by date"""
        daily = {}
        
        for reading in sensor_data:
            date = reading['date']
            if date not in daily:
                daily[date] = {
                    'temperature': [],
                    'humidity': [],
                    'soil_moisture': []
                }
            
            if reading.get('temperature') is not None:
                daily[date]['temperature'].append(reading['temperature'])
            if reading.get('humidity') is not None:
                daily[date]['humidity'].append(reading['humidity'])
            if reading.get('soil_moisture') is not None:
                daily[date]['soil_moisture'].append(reading['soil_moisture'])
        
        # Calculate daily averages
        for date in daily:
            for key in ['temperature', 'humidity', 'soil_moisture']:
                values = daily[date][key]
                daily[date][key] = np.mean(values) if values else None
        
        return daily
    
    def _compute_water_balance(self, daily_sensor: Dict, gee_data: Dict,
                                start_date: str, end_date: str) -> List[Dict]:
        """Compute daily water balance"""
        water_balance = []
        
        # Get data arrays
        rainfall_data = {d['date']: d['value'] for d in gee_data.get('rainfall', [])}
        et_data = {d['date']: d['value'] for d in gee_data.get('et', [])}
        kc_data = {d['date']: d['value'] for d in gee_data.get('kc', [])}
        
        # Generate date range
        dates = self._generate_date_range(start_date, end_date)
        
        prev_soil_moisture = None
        
        for date in dates:
            sensor = daily_sensor.get(date, {})
            
            # Get values with fallbacks
            temperature = sensor.get('temperature') or 25.0
            humidity = sensor.get('humidity') or 60.0
            soil_moisture = sensor.get('soil_moisture')
            
            precipitation = rainfall_data.get(date, 0)
            et_value = et_data.get(date, 0)
            kc = kc_data.get(date, 0.8)
            
            # Calculate VPD
            vpd = calculate_vpd_numpy(np.array([temperature]), np.array([humidity]))[0]
            
            # Calculate ET0 (reference ET)
            et0 = calculate_et0_numpy(np.array([temperature]), np.array([humidity]))[0]
            
            # Calculate ETc (crop ET)
            etc = et0 * kc
            
            # Calculate delta S (change in soil moisture)
            if soil_moisture is not None and prev_soil_moisture is not None:
                # Convert soil moisture % to mm (assuming 100mm root zone)
                delta_s = (soil_moisture - prev_soil_moisture) * 1.0
            else:
                delta_s = 0
            
            prev_soil_moisture = soil_moisture
            
            # Estimate runoff (simplified SCS-CN)
            runoff = self._estimate_runoff(precipitation)
            
            # Water balance: Balance = P + I - ET - R - ΔS
            irrigation = 0  # TODO: Get from irrigation sensors
            balance = precipitation + irrigation - etc - runoff - delta_s
            
            # VPD stress factor
            vpd_stress = self._calculate_vpd_stress(vpd)
            
            water_balance.append({
                'date': date,
                'et0': float(et0),
                'etc': float(etc),
                'precipitation': float(precipitation),
                'irrigation': float(irrigation),
                'runoff': float(runoff),
                'deltaS': float(delta_s),
                'value': float(balance),  # For chart compatibility
                'vpd': float(vpd),
                'vpdStress': float(vpd_stress),
                'kc': float(kc),
                'components': {
                    'p': float(precipitation),
                    'i': float(irrigation),
                    'et': float(etc),
                    'r': float(runoff),
                    'ds': float(delta_s)
                }
            })
        
        return water_balance
    
    def _compute_crop_growth(self, daily_sensor: Dict, gee_data: Dict,
                              start_date: str, end_date: str) -> List[Dict]:
        """Compute crop growth parameters"""
        crop_growth = []
        
        ndvi_data = {d['date']: d['value'] for d in gee_data.get('ndvi', [])}
        
        dates = self._generate_date_range(start_date, end_date)
        accumulated_gdd = 0
        
        for date in dates:
            sensor = daily_sensor.get(date, {})
            temperature = sensor.get('temperature') or 25.0
            
            # Calculate GDD
            gdd = calculate_gdd_numpy(
                np.array([temperature + 5]),  # Estimate max
                np.array([temperature - 5]),   # Estimate min
                self.physics_constants.TOBACCO_BASE_TEMP
            )[0]
            
            accumulated_gdd += gdd
            
            # Estimate LAI from accumulated GDD
            gdd_50 = 800.0
            max_lai = 5.0
            growth_rate = 0.02
            lai = max_lai / (1 + np.exp(-growth_rate * (accumulated_gdd - gdd_50)))
            
            # Get or calculate Kc
            ndvi = ndvi_data.get(date)
            if ndvi is not None:
                kc = calculate_kc_from_ndvi_numpy(np.array([ndvi]))[0]
            else:
                kc = 0.3 + 0.7 * (lai / max_lai)
            
            # Determine growth stage
            growth_stage = self._get_growth_stage(accumulated_gdd)
            
            crop_growth.append({
                'date': date,
                'gdd': float(gdd),
                'accumulatedGdd': float(accumulated_gdd),
                'lai': float(lai),
                'kc': float(kc),
                'growthStage': growth_stage
            })
        
        return crop_growth
    
    def _compute_vpd_analysis(self, daily_sensor: Dict, gee_data: Dict) -> List[Dict]:
        """Compute VPD analysis"""
        vpd_analysis = []
        
        lst_data = {d['date']: d['value'] for d in gee_data.get('lst', [])}
        
        for date, sensor in daily_sensor.items():
            temperature = sensor.get('temperature')
            humidity = sensor.get('humidity')
            
            # Use LST if sensor data unavailable
            if temperature is None:
                temperature = lst_data.get(date, 25.0)
            if humidity is None:
                humidity = 60.0
            
            vpd = calculate_vpd_numpy(np.array([temperature]), np.array([humidity]))[0]
            stress = self._calculate_vpd_stress(vpd)
            
            # Categorize VPD
            if vpd < 0.5:
                category = 'low'
            elif vpd <= 2.0:
                category = 'optimal'
            else:
                category = 'high'
            
            vpd_analysis.append({
                'date': date,
                'vpd': float(vpd),
                'stressFactor': float(stress),
                'category': category,
                'temperature': float(temperature),
                'humidity': float(humidity)
            })
        
        return sorted(vpd_analysis, key=lambda x: x['date'])
    
    def _compute_yield_stress_factors(self, water_balance: List[Dict],
                                       vpd_analysis: List[Dict]) -> List[Dict]:
        """Compute combined yield stress factors"""
        vpd_by_date = {d['date']: d for d in vpd_analysis}
        
        yield_stress = []
        for wb in water_balance:
            date = wb['date']
            vpd_data = vpd_by_date.get(date, {})
            
            vpd_stress = vpd_data.get('stressFactor', 1.0)
            
            # Water stress from water balance
            balance = wb['value']
            if balance < -10:  # Deficit
                water_stress = max(0.5, 1.0 + balance / 50.0)
            elif balance > 20:  # Excess
                water_stress = max(0.7, 1.0 - (balance - 20) / 100.0)
            else:
                water_stress = 1.0
            
            # Combined stress factor
            combined_stress = vpd_stress * water_stress
            
            yield_stress.append({
                'date': date,
                'vpdStress': float(vpd_stress),
                'waterStress': float(water_stress),
                'combinedStress': float(combined_stress),
                'yieldImpact': float((1 - combined_stress) * 100)  # % yield reduction
            })
        
        return yield_stress
    
    def _calculate_delta_s(self, daily_sensor: Dict) -> List[Dict]:
        """Calculate change in soil moisture storage"""
        delta_s = []
        dates = sorted(daily_sensor.keys())
        
        for i in range(1, len(dates)):
            prev_date = dates[i - 1]
            curr_date = dates[i]
            
            prev_sm = daily_sensor[prev_date].get('soil_moisture')
            curr_sm = daily_sensor[curr_date].get('soil_moisture')
            
            if prev_sm is not None and curr_sm is not None:
                change = (curr_sm - prev_sm) * 1.0  # Convert to mm
            else:
                change = 0
            
            delta_s.append({
                'date': curr_date,
                'value': float(change)
            })
        
        return delta_s
    
    def _estimate_runoff(self, precipitation: float, cn: float = 70.0) -> float:
        """
        Estimate runoff using SCS Curve Number method
        
        Q = (P - 0.2S)² / (P + 0.8S) for P > 0.2S
        Where S = (25400/CN) - 254
        """
        if precipitation <= 0:
            return 0
        
        S = (25400 / cn) - 254
        Ia = 0.2 * S
        
        if precipitation <= Ia:
            return 0
        
        return ((precipitation - Ia) ** 2) / (precipitation + 0.8 * S)
    
    def _calculate_vpd_stress(self, vpd: float) -> float:
        """Calculate VPD stress factor (0-1, where 1 = no stress)"""
        vpd_min = self.physics_constants.TOBACCO_VPD_MIN
        vpd_max = self.physics_constants.TOBACCO_VPD_MAX
        
        if vpd < vpd_min:
            return 0.9 + 0.1 * (vpd / vpd_min)
        elif vpd <= vpd_max:
            return 1.0
        else:
            return max(0.1, np.exp(-0.5 * (vpd - vpd_max)))
    
    def _get_growth_stage(self, accumulated_gdd: float) -> str:
        """Determine tobacco growth stage from accumulated GDD"""
        if accumulated_gdd < 200:
            return "Transplant/Establishment"
        elif accumulated_gdd < 500:
            return "Vegetative Growth"
        elif accumulated_gdd < 900:
            return "Rapid Growth"
        elif accumulated_gdd < 1200:
            return "Topping/Flowering"
        elif accumulated_gdd < 1500:
            return "Maturation"
        else:
            return "Harvest Ready"
    
    def _generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of dates between start and end"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return dates
    
    def _generate_summary(self, water_balance: List[Dict],
                          crop_growth: List[Dict],
                          vpd_analysis: List[Dict]) -> Dict:
        """Generate summary statistics"""
        if not water_balance:
            return {}
        
        balances = [wb['value'] for wb in water_balance]
        et_values = [wb['etc'] for wb in water_balance]
        precip_values = [wb['precipitation'] for wb in water_balance]
        vpd_values = [v['vpd'] for v in vpd_analysis]
        
        latest_growth = crop_growth[-1] if crop_growth else {}
        
        return {
            'totalWaterBalance': sum(balances),
            'averageWaterBalance': np.mean(balances),
            'totalPrecipitation': sum(precip_values),
            'totalET': sum(et_values),
            'averageVPD': np.mean(vpd_values) if vpd_values else 0,
            'maxVPD': max(vpd_values) if vpd_values else 0,
            'waterDeficitDays': sum(1 for b in balances if b < -5),
            'waterExcessDays': sum(1 for b in balances if b > 10),
            'currentGrowthStage': latest_growth.get('growthStage', 'Unknown'),
            'accumulatedGDD': latest_growth.get('accumulatedGdd', 0),
            'currentLAI': latest_growth.get('lai', 0)
        }
    
    def _generate_recommendations(self, summary: Dict) -> List[str]:
        """Generate irrigation and management recommendations"""
        recommendations = []
        
        total_balance = summary.get('totalWaterBalance', 0)
        avg_vpd = summary.get('averageVPD', 0)
        deficit_days = summary.get('waterDeficitDays', 0)
        growth_stage = summary.get('currentGrowthStage', '')
        
        # Water balance recommendations
        if total_balance < -20:
            recommendations.append(
                f"Significant water deficit detected ({total_balance:.1f}mm). "
                "Consider increasing irrigation frequency."
            )
        elif total_balance > 30:
            recommendations.append(
                f"Water excess detected ({total_balance:.1f}mm). "
                "Reduce irrigation to prevent waterlogging and disease."
            )
        
        # VPD recommendations
        if avg_vpd > 2.0:
            recommendations.append(
                f"High VPD stress (avg {avg_vpd:.2f} kPa). "
                "Consider irrigation during peak heat hours to reduce plant stress."
            )
        elif avg_vpd < 0.5:
            recommendations.append(
                f"Low VPD conditions (avg {avg_vpd:.2f} kPa). "
                "Monitor for fungal diseases and improve ventilation if possible."
            )
        
        # Growth stage specific
        if 'Rapid Growth' in growth_stage:
            recommendations.append(
                "Crop is in rapid growth phase. "
                "Ensure adequate water and nutrient supply for optimal yield."
            )
        elif 'Maturation' in growth_stage:
            recommendations.append(
                "Crop is maturing. "
                "Gradually reduce irrigation to improve leaf quality."
            )
        
        # Deficit days
        if deficit_days > 7:
            recommendations.append(
                f"Water deficit detected on {deficit_days} days. "
                "Review irrigation scheduling to prevent yield loss."
            )
        
        if not recommendations:
            recommendations.append(
                "Water balance appears optimal. Continue current management practices."
            )
        
        return recommendations


# Singleton instance
_water_balance_api = None


def get_water_balance_api() -> WaterBalanceAPI:
    """Get Water Balance API singleton"""
    global _water_balance_api
    if _water_balance_api is None:
        _water_balance_api = WaterBalanceAPI()
    return _water_balance_api


if __name__ == "__main__":
    # Test the API
    logging.basicConfig(level=logging.INFO)
    
    api = get_water_balance_api()
    
    # Test coordinates
    lat = -18.30252535
    lng = 31.56415345
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"\nCalculating water balance for ({lat}, {lng})")
    print(f"Date range: {start_date} to {end_date}")
    
    result = api.calculate_water_balance(lat, lng, start_date, end_date)
    
    print(f"\nSuccess: {result['success']}")
    print(f"Water balance data points: {len(result['data']['waterBalance'])}")
    print(f"Summary: {result['summary']}")
    print(f"Recommendations: {result['recommendations']}")
