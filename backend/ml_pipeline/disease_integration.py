"""
Enhanced integration of YOLOv8 disease detection with yield prediction
Converts disease detections to risk scores and temporal features
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DiseaseFeatureExtractor:
    """
    Extracts disease-related features for yield prediction
    
    Features:
    - Disease severity score (0-1)
    - Disease progression rate
    - Days since last detection
    - Cumulative disease exposure
    """
    
    # Disease severity weights
    DISEASE_SEVERITY = {
        'healthy': 0.0,
        'alternaria alternata': 0.6,  # Moderate severity
        'cercospora nicotianae': 0.8,  # High severity
        'unknown': 0.5
    }
    
    # Yield impact factors (estimated reduction in yield)
    YIELD_IMPACT = {
        'healthy': 0.0,
        'alternaria alternata': 0.15,  # 15% yield reduction
        'cercospora nicotianae': 0.25,  # 25% yield reduction
        'unknown': 0.10
    }
    
    @staticmethod
    def compute_disease_score(disease_type: str, confidence: float) -> float:
        """
        Compute disease severity score
        
        Args:
            disease_type: Disease name
            confidence: Detection confidence (0-1)
        
        Returns:
            Disease score (0-1, higher = more severe)
        """
        disease_type = disease_type.lower()
        
        # Find matching disease
        severity = 0.0
        for disease, weight in DiseaseFeatureExtractor.DISEASE_SEVERITY.items():
            if disease in disease_type:
                severity = weight
                break
        
        # Weight by confidence
        return severity * confidence
    
    @staticmethod
    def compute_yield_impact(disease_type: str, confidence: float, duration_days: int) -> float:
        """
        Estimate yield impact from disease
        
        Args:
            disease_type: Disease name
            confidence: Detection confidence
            duration_days: Days since infection
        
        Returns:
            Estimated yield reduction (0-1)
        """
        disease_type = disease_type.lower()
        
        # Base impact
        base_impact = 0.0
        for disease, impact in DiseaseFeatureExtractor.YIELD_IMPACT.items():
            if disease in disease_type:
                base_impact = impact
                break
        
        # Scale by confidence
        impact = base_impact * confidence
        
        # Scale by duration (longer infection = more impact)
        # Assume impact increases logarithmically with time
        duration_factor = min(1.0, np.log1p(duration_days) / np.log1p(30))  # Saturates at 30 days
        
        return impact * duration_factor
    
    @staticmethod
    def extract_temporal_features(disease_df: pd.DataFrame, 
                                  window_start: datetime,
                                  window_end: datetime) -> Dict[str, float]:
        """
        Extract temporal disease features for a time window
        
        Args:
            disease_df: Disease detection DataFrame for a sensor
            window_start: Start of time window
            window_end: End of time window
        
        Returns:
            Dictionary of disease features
        """
        # Filter to window
        mask = (disease_df['timestamp'] >= window_start) & (disease_df['timestamp'] <= window_end)
        window_detections = disease_df[mask]
        
        if len(window_detections) == 0:
            return {
                'disease_score': 0.0,
                'disease_count': 0,
                'max_severity': 0.0,
                'avg_severity': 0.0,
                'days_since_detection': 999,
                'cumulative_exposure': 0.0,
                'disease_progression_rate': 0.0
            }
        
        # Compute scores
        scores = []
        for _, row in window_detections.iterrows():
            score = DiseaseFeatureExtractor.compute_disease_score(
                row['disease_type'],
                row['confidence']
            )
            scores.append(score)
        
        # Days since last detection
        last_detection = window_detections['timestamp'].max()
        days_since = (window_end - last_detection).days
        
        # Cumulative exposure (sum of daily scores)
        cumulative = sum(scores)
        
        # Disease progression rate (change in severity over window)
        if len(scores) > 1:
            # Sort by time
            sorted_detections = window_detections.sort_values('timestamp')
            early_scores = [DiseaseFeatureExtractor.compute_disease_score(
                row['disease_type'], row['confidence']
            ) for _, row in sorted_detections.head(len(sorted_detections)//2).iterrows()]
            
            late_scores = [DiseaseFeatureExtractor.compute_disease_score(
                row['disease_type'], row['confidence']
            ) for _, row in sorted_detections.tail(len(sorted_detections)//2).iterrows()]
            
            early_avg = np.mean(early_scores) if early_scores else 0.0
            late_avg = np.mean(late_scores) if late_scores else 0.0
            
            progression_rate = late_avg - early_avg
        else:
            progression_rate = 0.0
        
        return {
            'disease_score': scores[-1] if scores else 0.0,  # Most recent
            'disease_count': len(window_detections),
            'max_severity': max(scores) if scores else 0.0,
            'avg_severity': np.mean(scores) if scores else 0.0,
            'days_since_detection': days_since,
            'cumulative_exposure': cumulative,
            'disease_progression_rate': progression_rate
        }
    
    @staticmethod
    def create_disease_time_series(disease_df: pd.DataFrame,
                                   start_date: datetime,
                                   end_date: datetime,
                                   freq: str = 'D') -> pd.DataFrame:
        """
        Create daily disease score time series
        
        Args:
            disease_df: Disease detection DataFrame
            start_date: Start date
            end_date: End date
            freq: Frequency ('D' for daily)
        
        Returns:
            DataFrame with daily disease scores
        """
        # Create date range
        date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        # Initialize time series
        time_series = pd.DataFrame({
            'date': date_range,
            'disease_score': 0.0,
            'disease_count': 0
        })
        
        # Fill in disease scores
        for date in date_range:
            day_start = date
            day_end = date + timedelta(days=1)
            
            # Get detections for this day
            mask = (disease_df['timestamp'] >= day_start) & (disease_df['timestamp'] < day_end)
            day_detections = disease_df[mask]
            
            if len(day_detections) > 0:
                # Take maximum severity for the day
                scores = [DiseaseFeatureExtractor.compute_disease_score(
                    row['disease_type'], row['confidence']
                ) for _, row in day_detections.iterrows()]
                
                time_series.loc[time_series['date'] == date, 'disease_score'] = max(scores)
                time_series.loc[time_series['date'] == date, 'disease_count'] = len(day_detections)
        
        return time_series


class DiseaseYieldPredictor:
    """
    Predicts yield impact from disease history
    Uses simple empirical model before ST-GNN training
    """
    
    @staticmethod
    def predict_yield_reduction(disease_history: pd.DataFrame,
                                growth_stage: str = 'vegetative') -> float:
        """
        Predict yield reduction from disease history
        
        Args:
            disease_history: DataFrame with disease detections
            growth_stage: Crop growth stage ('vegetative', 'flowering', 'fruiting')
        
        Returns:
            Estimated yield reduction (0-1)
        """
        if len(disease_history) == 0:
            return 0.0
        
        # Compute cumulative disease exposure
        total_impact = 0.0
        
        for _, row in disease_history.iterrows():
            disease_type = row['disease_type']
            confidence = row['confidence']
            
            # Base impact
            impact = DiseaseFeatureExtractor.compute_yield_impact(
                disease_type,
                confidence,
                duration_days=1  # Simplified
            )
            
            # Growth stage multiplier
            stage_multipliers = {
                'vegetative': 0.5,   # Less impact early
                'flowering': 1.5,    # Critical stage
                'fruiting': 1.2      # Important stage
            }
            multiplier = stage_multipliers.get(growth_stage, 1.0)
            
            total_impact += impact * multiplier
        
        # Cap at 100% reduction
        return min(1.0, total_impact)


if __name__ == "__main__":
    # Test disease feature extraction
    logging.basicConfig(level=logging.INFO)
    
    # Create sample disease data
    disease_data = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=10, freq='D'),
        'disease_type': ['alternaria alternata'] * 5 + ['healthy'] * 5,
        'confidence': [0.8, 0.85, 0.9, 0.75, 0.7] + [0.95] * 5
    })
    
    # Extract features
    features = DiseaseFeatureExtractor.extract_temporal_features(
        disease_data,
        datetime(2025, 1, 1),
        datetime(2025, 1, 10)
    )
    
    print("\n✓ Disease feature extraction test:")
    for key, value in features.items():
        print(f"  - {key}: {value:.3f}")
    
    # Create time series
    time_series = DiseaseFeatureExtractor.create_disease_time_series(
        disease_data,
        datetime(2025, 1, 1),
        datetime(2025, 1, 10)
    )
    
    print(f"\n✓ Disease time series created:")
    print(f"  - Length: {len(time_series)}")
    print(f"  - Mean score: {time_series['disease_score'].mean():.3f}")
