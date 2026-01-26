#!/usr/bin/env python3
"""
CropIoT Analytics Engine
Handles data analysis, trend calculations, and yield estimation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import csv
import os
from collections import defaultdict

class AnalyticsEngine:
    """Main analytics engine for processing sensor data"""
    
    def __init__(self, csv_file: str = "crop_data.csv"):
        self.csv_file = csv_file
        self.optimal_ranges = {
            'soil_moisture': {'min': 40, 'max': 70},  # Percentage
            'ph': {'min': 6.0, 'max': 7.5},           # pH scale
            'temperature': {'min': 18, 'max': 28},     # Celsius
            'humidity': {'min': 50, 'max': 80}         # Percentage
        }
        
    def load_data(self) -> pd.DataFrame:
        """Load and clean sensor data from CSV"""
        if not os.path.exists(self.csv_file):
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.csv_file)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Replace error values (-999) with NaN
            numeric_columns = ['soil_moisture', 'ph', 'temperature', 'humidity']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].replace(-999, np.nan)
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def calculate_daily_averages(self, days: int = 30) -> Dict:
        """Calculate daily averages for each sensor over the last N days"""
        df = self.load_data()
        if df.empty:
            return {}
        
        # Filter to last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff_date]
        
        # Group by date and sensor_id
        df['date'] = df['timestamp'].dt.date
        
        daily_averages = {}
        for sensor_id in df['sensor_id'].unique():
            sensor_data = df[df['sensor_id'] == sensor_id]
            
            daily_avg = sensor_data.groupby('date').agg({
                'soil_moisture': 'mean',
                'ph': 'mean',
                'temperature': 'mean',
                'humidity': 'mean'
            }).round(2)
            
            daily_averages[sensor_id] = [
                {
                    'date': str(date),
                    'soil_moisture': row['soil_moisture'] if not pd.isna(row['soil_moisture']) else None,
                    'ph': row['ph'] if not pd.isna(row['ph']) else None,
                    'temperature': row['temperature'] if not pd.isna(row['temperature']) else None,
                    'humidity': row['humidity'] if not pd.isna(row['humidity']) else None,
                    'readings_count': int(sensor_data[sensor_data['date'] == date].shape[0])
                }
                for date, row in daily_avg.iterrows()
            ]
        
        return daily_averages
    
    def calculate_trend_summary(self) -> Dict:
        """Calculate trend summaries comparing last 7 days vs previous 7 days"""
        df = self.load_data()
        if df.empty:
            return {}
        
        now = datetime.now()
        last_7_days = df[df['timestamp'] >= (now - timedelta(days=7))]
        previous_7_days = df[
            (df['timestamp'] >= (now - timedelta(days=14))) & 
            (df['timestamp'] < (now - timedelta(days=7)))
        ]
        
        trends = {}
        
        for sensor_id in df['sensor_id'].unique():
            last_week = last_7_days[last_7_days['sensor_id'] == sensor_id]
            prev_week = previous_7_days[previous_7_days['sensor_id'] == sensor_id]
            
            sensor_trends = {}
            
            for metric in ['soil_moisture', 'ph', 'temperature', 'humidity']:
                last_avg = last_week[metric].mean()
                prev_avg = prev_week[metric].mean()
                
                if pd.isna(last_avg) or pd.isna(prev_avg):
                    change = None
                    trend = "No data"
                else:
                    change = round(last_avg - prev_avg, 2)
                    if abs(change) < 0.1:
                        trend = "Stable"
                    elif change > 0:
                        trend = "Increasing"
                    else:
                        trend = "Decreasing"
                
                sensor_trends[metric] = {
                    'last_week_avg': round(last_avg, 2) if not pd.isna(last_avg) else None,
                    'prev_week_avg': round(prev_avg, 2) if not pd.isna(prev_avg) else None,
                    'change': change,
                    'trend': trend
                }
            
            trends[sensor_id] = sensor_trends
        
        return trends
    
    def get_sensor_statistics(self) -> Dict:
        """Get comprehensive statistics for each sensor"""
        df = self.load_data()
        if df.empty:
            return {}
        
        stats = {}
        
        for sensor_id in df['sensor_id'].unique():
            sensor_data = df[df['sensor_id'] == sensor_id]
            
            sensor_stats = {
                'total_readings': len(sensor_data),
                'date_range': {
                    'start': sensor_data['timestamp'].min().strftime('%Y-%m-%d'),
                    'end': sensor_data['timestamp'].max().strftime('%Y-%m-%d')
                },
                'metrics': {}
            }
            
            for metric in ['soil_moisture', 'ph', 'temperature', 'humidity']:
                metric_data = sensor_data[metric].dropna()
                
                if len(metric_data) > 0:
                    sensor_stats['metrics'][metric] = {
                        'current': round(metric_data.iloc[-1], 2),
                        'average': round(metric_data.mean(), 2),
                        'min': round(metric_data.min(), 2),
                        'max': round(metric_data.max(), 2),
                        'std': round(metric_data.std(), 2)
                    }
                else:
                    sensor_stats['metrics'][metric] = None
            
            stats[sensor_id] = sensor_stats
        
        return stats

class YieldEstimator:
    """Rule-based yield estimation system"""
    
    def __init__(self, analytics_engine: AnalyticsEngine):
        self.analytics = analytics_engine
        self.base_yield_score = 100  # Starting score out of 100
        
        # Thresholds for yield impact
        self.moisture_threshold = 30  # Below this for 3+ days reduces yield
        self.consecutive_days_threshold = 3
        
    def calculate_yield_score(self, sensor_id: str) -> Dict:
        """Calculate yield score for a specific sensor based on recent conditions"""
        df = self.analytics.load_data()
        if df.empty:
            return {'score': 0, 'factors': [], 'recommendations': []}
        
        # Filter to last 14 days for analysis
        cutoff_date = datetime.now() - timedelta(days=14)
        sensor_data = df[
            (df['sensor_id'] == sensor_id) & 
            (df['timestamp'] >= cutoff_date)
        ].copy()
        
        if sensor_data.empty:
            return {'score': 0, 'factors': ['No recent data'], 'recommendations': ['Check sensor connectivity']}
        
        yield_score = self.base_yield_score
        factors = []
        recommendations = []
        
        # Check soil moisture patterns
        moisture_impact, moisture_factors, moisture_recs = self._analyze_moisture_pattern(sensor_data)
        yield_score += moisture_impact
        factors.extend(moisture_factors)
        recommendations.extend(moisture_recs)
        
        # Check temperature patterns
        temp_impact, temp_factors, temp_recs = self._analyze_temperature_pattern(sensor_data)
        yield_score += temp_impact
        factors.extend(temp_factors)
        recommendations.extend(temp_recs)
        
        # Check pH patterns
        ph_impact, ph_factors, ph_recs = self._analyze_ph_pattern(sensor_data)
        yield_score += ph_impact
        factors.extend(ph_factors)
        recommendations.extend(ph_recs)
        
        # Check humidity patterns
        humidity_impact, humidity_factors, humidity_recs = self._analyze_humidity_pattern(sensor_data)
        yield_score += humidity_impact
        factors.extend(humidity_factors)
        recommendations.extend(humidity_recs)
        
        # Ensure score stays within bounds
        yield_score = max(0, min(100, yield_score))
        
        return {
            'score': round(yield_score, 1),
            'factors': factors,
            'recommendations': recommendations,
            'grade': self._get_yield_grade(yield_score)
        }
    
    def _analyze_moisture_pattern(self, sensor_data: pd.DataFrame) -> Tuple[float, List[str], List[str]]:
        """Analyze soil moisture patterns for yield impact"""
        impact = 0
        factors = []
        recommendations = []
        
        moisture_data = sensor_data['soil_moisture'].dropna()
        if len(moisture_data) == 0:
            return 0, ['No moisture data'], ['Install soil moisture sensor']
        
        # Check for consecutive low moisture days
        sensor_data['date'] = sensor_data['timestamp'].dt.date
        daily_avg = sensor_data.groupby('date')['soil_moisture'].mean()
        
        consecutive_low_days = 0
        max_consecutive_low = 0
        
        for moisture in daily_avg:
            if moisture < self.moisture_threshold:
                consecutive_low_days += 1
                max_consecutive_low = max(max_consecutive_low, consecutive_low_days)
            else:
                consecutive_low_days = 0
        
        if max_consecutive_low >= self.consecutive_days_threshold:
            impact -= 15 * (max_consecutive_low - self.consecutive_days_threshold + 1)
            factors.append(f"Low soil moisture for {max_consecutive_low} consecutive days")
            recommendations.append("Increase irrigation frequency")
        
        # Check current moisture level
        current_moisture = moisture_data.iloc[-1]
        optimal_range = self.analytics.optimal_ranges['soil_moisture']
        
        if current_moisture < optimal_range['min']:
            impact -= 5
            factors.append(f"Current moisture ({current_moisture}%) below optimal")
            recommendations.append("Water immediately")
        elif current_moisture > optimal_range['max']:
            impact -= 3
            factors.append(f"Current moisture ({current_moisture}%) above optimal")
            recommendations.append("Reduce watering, check drainage")
        else:
            factors.append(f"Soil moisture in optimal range ({current_moisture}%)")
        
        return impact, factors, recommendations
    
    def _analyze_temperature_pattern(self, sensor_data: pd.DataFrame) -> Tuple[float, List[str], List[str]]:
        """Analyze temperature patterns for yield impact"""
        impact = 0
        factors = []
        recommendations = []
        
        temp_data = sensor_data['temperature'].dropna()
        if len(temp_data) == 0:
            return 0, ['No temperature data'], ['Install temperature sensor']
        
        avg_temp = temp_data.mean()
        optimal_range = self.analytics.optimal_ranges['temperature']
        
        if avg_temp < optimal_range['min']:
            impact -= 8
            factors.append(f"Average temperature ({avg_temp:.1f}°C) below optimal")
            recommendations.append("Consider greenhouse or row covers")
        elif avg_temp > optimal_range['max']:
            impact -= 10
            factors.append(f"Average temperature ({avg_temp:.1f}°C) above optimal")
            recommendations.append("Provide shade or increase ventilation")
        else:
            factors.append(f"Temperature in optimal range ({avg_temp:.1f}°C)")
        
        # Check for extreme temperatures
        max_temp = temp_data.max()
        min_temp = temp_data.min()
        
        if max_temp > 35:
            impact -= 5
            factors.append(f"Extreme high temperature recorded ({max_temp:.1f}°C)")
            recommendations.append("Monitor for heat stress")
        
        if min_temp < 5:
            impact -= 7
            factors.append(f"Extreme low temperature recorded ({min_temp:.1f}°C)")
            recommendations.append("Protect from frost")
        
        return impact, factors, recommendations
    
    def _analyze_ph_pattern(self, sensor_data: pd.DataFrame) -> Tuple[float, List[str], List[str]]:
        """Analyze pH patterns for yield impact"""
        impact = 0
        factors = []
        recommendations = []
        
        ph_data = sensor_data['ph'].dropna()
        if len(ph_data) == 0:
            return 0, ['No pH data'], ['Install pH sensor']
        
        avg_ph = ph_data.mean()
        optimal_range = self.analytics.optimal_ranges['ph']
        
        if avg_ph < optimal_range['min']:
            impact -= 12
            factors.append(f"Soil pH ({avg_ph:.1f}) too acidic")
            recommendations.append("Add lime to raise pH")
        elif avg_ph > optimal_range['max']:
            impact -= 10
            factors.append(f"Soil pH ({avg_ph:.1f}) too alkaline")
            recommendations.append("Add sulfur or organic matter to lower pH")
        else:
            factors.append(f"Soil pH in optimal range ({avg_ph:.1f})")
        
        return impact, factors, recommendations
    
    def _analyze_humidity_pattern(self, sensor_data: pd.DataFrame) -> Tuple[float, List[str], List[str]]:
        """Analyze humidity patterns for yield impact"""
        impact = 0
        factors = []
        recommendations = []
        
        humidity_data = sensor_data['humidity'].dropna()
        if len(humidity_data) == 0:
            return 0, ['No humidity data'], ['Install humidity sensor']
        
        avg_humidity = humidity_data.mean()
        optimal_range = self.analytics.optimal_ranges['humidity']
        
        if avg_humidity < optimal_range['min']:
            impact -= 5
            factors.append(f"Low humidity ({avg_humidity:.1f}%)")
            recommendations.append("Increase air moisture or mulching")
        elif avg_humidity > optimal_range['max']:
            impact -= 7
            factors.append(f"High humidity ({avg_humidity:.1f}%)")
            recommendations.append("Improve air circulation to prevent disease")
        else:
            factors.append(f"Humidity in optimal range ({avg_humidity:.1f}%)")
        
        return impact, factors, recommendations
    
    def _get_yield_grade(self, score: float) -> str:
        """Convert yield score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def get_all_sensor_yields(self) -> Dict:
        """Get yield estimates for all sensors"""
        df = self.analytics.load_data()
        if df.empty:
            return {}
        
        yields = {}
        for sensor_id in df['sensor_id'].unique():
            yields[sensor_id] = self.calculate_yield_score(sensor_id)
        
        return yields

# Factory function for easy instantiation
def create_analytics_system(csv_file: str = "crop_data.csv"):
    """Create analytics engine and yield estimator"""
    analytics = AnalyticsEngine(csv_file)
    yield_estimator = YieldEstimator(analytics)
    
    return analytics, yield_estimator
