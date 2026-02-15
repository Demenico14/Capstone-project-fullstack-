#!/usr/bin/env python3
"""
Google Earth Engine Service Module
Fetches satellite data for physics-informed ST-GNN model including:
- NDVI from Sentinel-2
- Rainfall from CHIRPS
- ET from MODIS
- Land Surface Temperature from MODIS
- Soil Moisture from NASA SMAP

This module provides the environmental data needed for water balance,
VPD calculations, and crop growth equations.
"""

import ee
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class GEEConfig:
    """Configuration for GEE service"""
    service_account_email: str
    private_key: str
    project_id: str = "tobaccomarondera"

class GEEService:
    """
    Google Earth Engine service for fetching satellite data
    for physics-informed yield prediction
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not GEEService._initialized:
            self.config = None
            self._load_credentials()
    
    def _load_credentials(self):
        """Load GEE credentials from environment or file"""
        try:
            # Try environment variable first (base64 encoded JSON)
            service_account_json = os.getenv('GEE_SERVICE_ACCOUNT_JSON')
            
            if service_account_json:
                import base64
                decoded = base64.b64decode(service_account_json).decode('utf-8')
                key_data = json.loads(decoded)
            else:
                # Try file path
                key_path = os.getenv('GEE_PRIVATE_KEY_PATH', 
                                     os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                                  'gee-service-account.json'))
                with open(key_path, 'r') as f:
                    key_data = json.load(f)
            
            self.config = GEEConfig(
                service_account_email=key_data.get('client_email'),
                private_key=key_data.get('private_key'),
                project_id=key_data.get('project_id', 'tobaccomarondera')
            )
            
            logger.info(f"GEE credentials loaded for: {self.config.service_account_email}")
            
        except Exception as e:
            logger.error(f"Failed to load GEE credentials: {e}")
            raise
    
    def initialize(self) -> bool:
        """Initialize Earth Engine with service account credentials"""
        if GEEService._initialized:
            return True
        
        try:
            credentials = ee.ServiceAccountCredentials(
                self.config.service_account_email,
                key_data=self.config.private_key
            )
            ee.Initialize(credentials, project=self.config.project_id)
            GEEService._initialized = True
            logger.info("Earth Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            return False
    
    def get_aoi(self, lat: float, lng: float, buffer_m: int = 500) -> ee.Geometry:
        """Create area of interest from coordinates"""
        point = ee.Geometry.Point([lng, lat])
        return point.buffer(buffer_m)
    
    def fetch_ndvi(self, lat: float, lng: float, 
                   start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch NDVI time series from Sentinel-2
        
        Args:
            lat: Latitude
            lng: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of {date, ndvi} dictionaries
        """
        self.initialize()
        aoi = self.get_aoi(lat, lng)
        
        s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
              .filterBounds(aoi)
              .filterDate(start_date, end_date)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
        
        def compute_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return ndvi.set('system:time_start', image.get('system:time_start'))
        
        ndvi_collection = s2.map(compute_ndvi)
        
        return self._extract_time_series(ndvi_collection, aoi, 'NDVI')
    
    def fetch_rainfall(self, lat: float, lng: float,
                       start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch rainfall data from CHIRPS
        
        Args:
            lat: Latitude
            lng: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of {date, precipitation} dictionaries
        """
        self.initialize()
        aoi = self.get_aoi(lat, lng)
        
        chirps = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
                  .filterBounds(aoi)
                  .filterDate(start_date, end_date))
        
        return self._extract_time_series(chirps, aoi, 'precipitation')
    
    def fetch_et(self, lat: float, lng: float,
                 start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch evapotranspiration from MODIS MOD16A2GF
        
        Args:
            lat: Latitude
            lng: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of {date, et} dictionaries in mm/day
        """
        self.initialize()
        aoi = self.get_aoi(lat, lng)
        
        mod16 = (ee.ImageCollection('MODIS/061/MOD16A2GF')
                 .filterBounds(aoi)
                 .filterDate(start_date, end_date)
                 .select('ET'))
        
        # MOD16 ET is in kg/m²/8day, convert to mm/day
        def convert_et(image):
            et_mm_day = image.multiply(0.1).divide(8).rename('ET')
            return et_mm_day.set('system:time_start', image.get('system:time_start'))
        
        et_collection = mod16.map(convert_et)
        
        return self._extract_time_series(et_collection, aoi, 'ET')
    
    def fetch_land_surface_temperature(self, lat: float, lng: float,
                                        start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch Land Surface Temperature from MODIS
        
        Returns temperature in Celsius
        """
        self.initialize()
        aoi = self.get_aoi(lat, lng)
        
        mod11 = (ee.ImageCollection('MODIS/061/MOD11A2')
                 .filterBounds(aoi)
                 .filterDate(start_date, end_date)
                 .select('LST_Day_1km'))
        
        # Convert from Kelvin * 0.02 to Celsius
        def convert_temp(image):
            temp_c = image.multiply(0.02).subtract(273.15).rename('LST')
            return temp_c.set('system:time_start', image.get('system:time_start'))
        
        lst_collection = mod11.map(convert_temp)
        
        return self._extract_time_series(lst_collection, aoi, 'LST')
    
    def fetch_soil_moisture_smap(self, lat: float, lng: float,
                                  start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch soil moisture from NASA SMAP L4
        
        Returns soil moisture in cm³/cm³
        """
        self.initialize()
        aoi = self.get_aoi(lat, lng)
        
        smap = (ee.ImageCollection('NASA/SMAP/SPL4SMGP/007')
                .filterBounds(aoi)
                .filterDate(start_date, end_date)
                .select('sm_surface'))
        
        return self._extract_time_series(smap, aoi, 'sm_surface')
    
    def fetch_comprehensive_data(self, lat: float, lng: float,
                                  start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetch all data needed for physics-informed ST-GNN
        
        This includes:
        - NDVI (vegetation health)
        - Precipitation (rainfall)
        - ET (evapotranspiration)
        - LST (land surface temperature)
        - Soil moisture (if available)
        - Calculated VPD
        - Crop coefficient (Kc)
        
        Returns:
            Dictionary with all time series data
        """
        self.initialize()
        
        logger.info(f"Fetching comprehensive GEE data for ({lat}, {lng}) "
                   f"from {start_date} to {end_date}")
        
        # Fetch all data in parallel would be ideal, but EE doesn't support that well
        # So we fetch sequentially
        try:
            ndvi_data = self.fetch_ndvi(lat, lng, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch NDVI: {e}")
            ndvi_data = []
        
        try:
            rainfall_data = self.fetch_rainfall(lat, lng, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch rainfall: {e}")
            rainfall_data = []
        
        try:
            et_data = self.fetch_et(lat, lng, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch ET: {e}")
            et_data = []
        
        try:
            lst_data = self.fetch_land_surface_temperature(lat, lng, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch LST: {e}")
            lst_data = []
        
        try:
            soil_moisture_data = self.fetch_soil_moisture_smap(lat, lng, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch SMAP soil moisture: {e}")
            soil_moisture_data = []
        
        # Calculate Kc from NDVI
        kc_data = self._calculate_kc_from_ndvi(ndvi_data)
        
        # Calculate VPD (requires temperature and humidity)
        # For satellite data, we estimate from LST
        vpd_data = self._estimate_vpd_from_lst(lst_data)
        
        return {
            'ndvi': ndvi_data,
            'rainfall': rainfall_data,
            'et': et_data,
            'lst': lst_data,
            'soil_moisture': soil_moisture_data,
            'kc': kc_data,
            'vpd': vpd_data,
            'metadata': {
                'location': {'lat': lat, 'lng': lng},
                'date_range': {'start': start_date, 'end': end_date},
                'data_sources': {
                    'ndvi': 'COPERNICUS/S2_SR_HARMONIZED',
                    'rainfall': 'UCSB-CHG/CHIRPS/DAILY',
                    'et': 'MODIS/061/MOD16A2GF',
                    'lst': 'MODIS/061/MOD11A2',
                    'soil_moisture': 'NASA/SMAP/SPL4SMGP/007'
                }
            }
        }
    
    def _extract_time_series(self, collection: ee.ImageCollection, 
                             aoi: ee.Geometry, band_name: str) -> List[Dict]:
        """
        Extract time series from image collection
        """
        def extract_values(image):
            value = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=30,
                maxPixels=1e9
            )
            return ee.Feature(None, {
                'date': ee.Date(image.get('system:time_start')).format('YYYY-MM-dd'),
                'value': value.get(band_name)
            })
        
        features = collection.map(extract_values)
        
        # Get as Python list
        result = features.getInfo()
        
        if result and 'features' in result:
            time_series = []
            for f in result['features']:
                props = f.get('properties', {})
                date = props.get('date')
                value = props.get('value')
                if date and value is not None:
                    time_series.append({
                        'date': date,
                        'value': float(value) if value else 0.0
                    })
            return sorted(time_series, key=lambda x: x['date'])
        
        return []
    
    def _calculate_kc_from_ndvi(self, ndvi_data: List[Dict]) -> List[Dict]:
        """
        Calculate crop coefficient (Kc) from NDVI
        
        Kc = 1.2 * (NDVI - NDVImin) / (NDVImax - NDVImin)
        """
        ndvi_min = 0.15
        ndvi_max = 0.85
        kc_max = 1.2
        
        kc_data = []
        for item in ndvi_data:
            ndvi = item['value']
            kc = kc_max * (ndvi - ndvi_min) / (ndvi_max - ndvi_min)
            kc = max(0.0, min(kc_max, kc))  # Clamp to valid range
            kc_data.append({
                'date': item['date'],
                'value': kc
            })
        
        return kc_data
    
    def _estimate_vpd_from_lst(self, lst_data: List[Dict], 
                               assumed_rh: float = 60.0) -> List[Dict]:
        """
        Estimate VPD from Land Surface Temperature
        
        VPD = es - ea where:
        es = 0.6108 * exp(17.27 * T / (T + 237.3))
        ea = es * RH / 100
        
        Args:
            lst_data: Land surface temperature data
            assumed_rh: Assumed relative humidity (%)
            
        Returns:
            List of VPD values in kPa
        """
        vpd_data = []
        for item in lst_data:
            temp = item['value']
            es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
            ea = es * assumed_rh / 100.0
            vpd = es - ea
            vpd_data.append({
                'date': item['date'],
                'value': float(vpd)
            })
        
        return vpd_data


# Singleton instance
gee_service = GEEService()


def get_gee_service() -> GEEService:
    """Get the GEE service singleton"""
    return gee_service


if __name__ == "__main__":
    # Test the service
    logging.basicConfig(level=logging.INFO)
    
    service = get_gee_service()
    
    # Test coordinates (Marondera, Zimbabwe)
    lat = -18.30252535
    lng = 31.56415345
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"\nFetching data for ({lat}, {lng})")
    print(f"Date range: {start_date} to {end_date}")
    
    data = service.fetch_comprehensive_data(lat, lng, start_date, end_date)
    
    print(f"\nNDVI data points: {len(data['ndvi'])}")
    print(f"Rainfall data points: {len(data['rainfall'])}")
    print(f"ET data points: {len(data['et'])}")
    print(f"LST data points: {len(data['lst'])}")
    print(f"Kc data points: {len(data['kc'])}")
    print(f"VPD data points: {len(data['vpd'])}")
