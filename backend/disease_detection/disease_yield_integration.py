#!/usr/bin/env python3
"""
Disease-Yield Integration Module
Integrate disease detection scores into yield prediction pipeline
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiseaseYieldIntegrator:
    """Integrate disease scores with yield predictions"""
    
    # Disease severity impact on yield (percentage reduction)
    DISEASE_IMPACT = {
        'healthy': 0.0,
        'brown_spot': 0.15,          # 15% yield reduction
        'frog_eye_leaf_spot': 0.20,  # 20% yield reduction
        'mosaic_virus': 0.35,        # 35% yield reduction
        'bacterial_wilt': 0.50,      # 50% yield reduction
        'black_shank': 0.60,         # 60% yield reduction
        'blue_mold': 0.45,           # 45% yield reduction
        'target_spot': 0.25          # 25% yield reduction
    }
    
    def __init__(self):
        """Initialize disease-yield integrator"""
        self.disease_history = []
    
    def calculate_disease_severity(self, detections: List[Dict]) -> Dict:
        """
        Calculate overall disease severity from detections
        
        Args:
            detections: List of disease detections with class and confidence
            
        Returns:
            Dictionary with severity metrics
        """
        if not detections:
            return {
                'severity_score': 0.0,
                'primary_disease': 'healthy',
                'disease_count': 0,
                'yield_impact': 0.0
            }
        
        # Count diseases by type
        disease_counts = {}
        total_confidence = 0.0
        
        for detection in detections:
            disease = detection.get('class', 'unknown')
            confidence = detection.get('confidence', 0.0)
            
            if disease not in disease_counts:
                disease_counts[disease] = {'count': 0, 'total_conf': 0.0}
            
            disease_counts[disease]['count'] += 1
            disease_counts[disease]['total_conf'] += confidence
            total_confidence += confidence
        
        # Find primary disease (most prevalent)
        primary_disease = max(
            disease_counts.items(),
            key=lambda x: (x[1]['count'], x[1]['total_conf'])
        )[0] if disease_counts else 'healthy'
        
        # Calculate severity score (0-1)
        severity_score = min(1.0, total_confidence / max(1, len(detections)))
        
        # Calculate yield impact
        base_impact = self.DISEASE_IMPACT.get(primary_disease, 0.0)
        yield_impact = base_impact * severity_score
        
        # Adjust for multiple diseases
        if len(disease_counts) > 1:
            yield_impact *= 1.2  # 20% additional impact for multiple diseases
        
        return {
            'severity_score': float(severity_score),
            'primary_disease': primary_disease,
            'disease_count': len(detections),
            'disease_types': len(disease_counts),
            'yield_impact': float(min(1.0, yield_impact)),
            'disease_distribution': disease_counts
        }
    
    def adjust_yield_prediction(
        self,
        base_yield: float,
        disease_severity: Dict,
        field_area: float = 1.0
    ) -> Dict:
        """
        Adjust yield prediction based on disease severity
        
        Args:
            base_yield: Base yield prediction (kg/ha)
            disease_severity: Disease severity metrics
            field_area: Field area in hectares
            
        Returns:
            Adjusted yield prediction with disease impact
        """
        yield_impact = disease_severity.get('yield_impact', 0.0)
        
        # Calculate adjusted yield
        adjusted_yield = base_yield * (1.0 - yield_impact)
        
        # Calculate losses
        yield_loss = base_yield - adjusted_yield
        total_loss = yield_loss * field_area
        
        return {
            'base_yield_per_ha': float(base_yield),
            'adjusted_yield_per_ha': float(adjusted_yield),
            'yield_reduction_percent': float(yield_impact * 100),
            'yield_loss_per_ha': float(yield_loss),
            'total_yield_loss': float(total_loss),
            'field_area_ha': float(field_area),
            'disease_severity': disease_severity
        }
    
    def generate_recommendations(self, disease_severity: Dict) -> List[str]:
        """
        Generate management recommendations based on disease severity
        
        Args:
            disease_severity: Disease severity metrics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        primary_disease = disease_severity.get('primary_disease', 'healthy')
        severity = disease_severity.get('severity_score', 0.0)
        
        if primary_disease == 'healthy':
            recommendations.append("✓ Crop appears healthy. Continue regular monitoring.")
            return recommendations
        
        # Severity-based recommendations
        if severity > 0.7:
            recommendations.append("⚠️ HIGH SEVERITY: Immediate intervention required")
        elif severity > 0.4:
            recommendations.append("⚠️ MODERATE SEVERITY: Treatment recommended")
        else:
            recommendations.append("ℹ️ LOW SEVERITY: Monitor closely")
        
        # Disease-specific recommendations
        disease_recommendations = {
            'brown_spot': [
                "Apply copper-based fungicides",
                "Improve field drainage",
                "Remove infected leaves"
            ],
            'frog_eye_leaf_spot': [
                "Apply fungicides (chlorothalonil or mancozeb)",
                "Rotate crops to reduce pathogen buildup",
                "Ensure proper plant spacing"
            ],
            'mosaic_virus': [
                "Remove and destroy infected plants",
                "Control aphid vectors with insecticides",
                "Use virus-resistant varieties in future plantings"
            ],
            'bacterial_wilt': [
                "Remove infected plants immediately",
                "Improve soil drainage",
                "Avoid overhead irrigation",
                "Consider soil fumigation for severe cases"
            ],
            'black_shank': [
                "Apply metalaxyl-based fungicides",
                "Improve field drainage",
                "Use resistant varieties",
                "Rotate with non-host crops"
            ],
            'blue_mold': [
                "Apply systemic fungicides immediately",
                "Increase air circulation",
                "Reduce humidity in field",
                "Scout regularly for early detection"
            ],
            'target_spot': [
                "Apply azoxystrobin or pyraclostrobin",
                "Remove crop debris",
                "Ensure adequate plant nutrition"
            ]
        }
        
        if primary_disease in disease_recommendations:
            recommendations.extend(disease_recommendations[primary_disease])
        
        # Multiple disease warning
        if disease_severity.get('disease_types', 0) > 1:
            recommendations.append("⚠️ Multiple diseases detected - consult agricultural extension officer")
        
        return recommendations
    
    def create_disease_report(
        self,
        detections: List[Dict],
        base_yield: float,
        field_area: float,
        field_id: str = None
    ) -> Dict:
        """
        Create comprehensive disease impact report
        
        Args:
            detections: Disease detections
            base_yield: Base yield prediction
            field_area: Field area in hectares
            field_id: Optional field identifier
            
        Returns:
            Complete disease impact report
        """
        # Calculate disease severity
        severity = self.calculate_disease_severity(detections)
        
        # Adjust yield prediction
        yield_adjustment = self.adjust_yield_prediction(base_yield, severity, field_area)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(severity)
        
        # Compile report
        report = {
            'field_id': field_id,
            'detection_summary': {
                'total_detections': len(detections),
                'primary_disease': severity['primary_disease'],
                'severity_score': severity['severity_score'],
                'disease_types_detected': severity['disease_types']
            },
            'yield_impact': yield_adjustment,
            'recommendations': recommendations,
            'raw_detections': detections
        }
        
        return report
    
    def save_report(self, report: Dict, output_path: str):
        """Save disease report to JSON file"""
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"✓ Report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

def main():
    """Example usage"""
    # Example detections
    detections = [
        {'class': 'brown_spot', 'confidence': 0.85},
        {'class': 'brown_spot', 'confidence': 0.78},
        {'class': 'mosaic_virus', 'confidence': 0.65}
    ]
    
    # Create integrator
    integrator = DiseaseYieldIntegrator()
    
    # Generate report
    report = integrator.create_disease_report(
        detections=detections,
        base_yield=2500,  # kg/ha
        field_area=5.0,   # hectares
        field_id='FIELD_001'
    )
    
    # Print report
    print(json.dumps(report, indent=2))
    
    # Save report
    integrator.save_report(report, 'disease_report.json')

if __name__ == '__main__':
    main()
