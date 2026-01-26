#!/usr/bin/env python3
"""
YOLOv8 Tobacco Disease Detection Inference Script
Run inference on tobacco leaf images to detect diseases
"""

import os
import sys
from pathlib import Path
from ultralytics import YOLO
import cv2
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TobaccoDiseaseDetector:
    """Detect tobacco diseases using trained YOLOv8 model"""
    
    TOBACCO_DISEASES = {
        0: 'healthy',
        1: 'brown_spot',
        2: 'frog_eye_leaf_spot',
        3: 'mosaic_virus',
        4: 'bacterial_wilt',
        5: 'black_shank',
        6: 'blue_mold',
        7: 'target_spot'
    }
    
    def __init__(self, model_path='./runs/train/tobacco_disease_detection/weights/best.pt', conf_threshold=0.25):
        """
        Initialize tobacco disease detector
        
        Args:
            model_path: Path to trained YOLOv8 model
            conf_threshold: Confidence threshold for detections
        """
        self.model_path = Path(model_path)
        self.conf_threshold = conf_threshold
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        logger.info(f"Loading tobacco disease model from {self.model_path}")
        self.model = YOLO(str(self.model_path))
        
        self.class_names = self.TOBACCO_DISEASES
        
        logger.info(f"Model loaded successfully with {len(self.class_names)} tobacco disease classes")
    
    def preprocess_image(self, image_path: str, target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
        """
        Preprocess image for inference
        
        Args:
            image_path: Path to input image
            target_size: Target size for resizing
            
        Returns:
            Preprocessed image array
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image from {image_path}")
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        return img
    
    def detect(self, image_path: str, save_annotated: bool = True) -> Dict:
        """
        Run tobacco disease detection on an image
        
        Args:
            image_path: Path to input image
            save_annotated: Whether to save annotated image
            
        Returns:
            Detection results dictionary
        """
        try:
            logger.info(f"Running tobacco disease inference on {image_path}")
            
            # Run inference
            results = self.model.predict(
                source=image_path,
                conf=self.conf_threshold,
                save=save_annotated,
                project='runs/detect',
                name='tobacco_disease_detection',
                exist_ok=True
            )
            
            # Process results
            detections = []
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Get confidence and class
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    
                    # Get class name
                    class_name = self.class_names.get(cls, f'class_{cls}')
                    
                    detection = {
                        'class': class_name,
                        'confidence': round(conf, 4),
                        'bbox': {
                            'x1': float(x1),
                            'y1': float(y1),
                            'x2': float(x2),
                            'y2': float(y2)
                        }
                    }
                    
                    detections.append(detection)
                    logger.info(f"Detected: {class_name} (confidence: {conf:.2%})")
            
            # Prepare result
            result_data = {
                'image_path': str(image_path),
                'timestamp': datetime.now().isoformat(),
                'num_detections': len(detections),
                'detections': detections,
                'annotated_image_path': str(results[0].save_dir / Path(image_path).name) if save_annotated else None
            }
            
            # Determine primary disease (highest confidence)
            if detections:
                primary_detection = max(detections, key=lambda x: x['confidence'])
                result_data['primary_disease'] = primary_detection['class']
                result_data['primary_confidence'] = primary_detection['confidence']
            else:
                result_data['primary_disease'] = 'none_detected'
                result_data['primary_confidence'] = 0.0
            
            logger.info(f"Detection complete: {len(detections)} disease(s) found")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise
    
    def batch_detect(self, image_dir: str, output_json: Optional[str] = None) -> List[Dict]:
        """
        Run detection on multiple images in a directory
        
        Args:
            image_dir: Directory containing images
            output_json: Optional path to save results as JSON
            
        Returns:
            List of detection results
        """
        image_dir = Path(image_dir)
        
        if not image_dir.exists():
            raise FileNotFoundError(f"Directory not found: {image_dir}")
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = [f for f in image_dir.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        logger.info(f"Found {len(image_files)} images in {image_dir}")
        
        # Run detection on each image
        all_results = []
        
        for image_file in image_files:
            try:
                result = self.detect(str(image_file))
                all_results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {image_file}: {e}")
                continue
        
        # Save results to JSON if requested
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(all_results, f, indent=2)
            logger.info(f"Results saved to {output_json}")
        
        return all_results
    
    def get_disease_summary(self, results: List[Dict]) -> Dict:
        """
        Generate summary statistics from detection results
        
        Args:
            results: List of detection results
            
        Returns:
            Summary statistics dictionary
        """
        total_images = len(results)
        total_detections = sum(r['num_detections'] for r in results)
        
        # Count diseases
        disease_counts = {}
        for result in results:
            for detection in result['detections']:
                disease = detection['class']
                disease_counts[disease] = disease_counts.get(disease, 0) + 1
        
        # Calculate percentages
        disease_percentages = {
            disease: (count / total_detections * 100) if total_detections > 0 else 0
            for disease, count in disease_counts.items()
        }
        
        summary = {
            'total_images': total_images,
            'total_detections': total_detections,
            'disease_counts': disease_counts,
            'disease_percentages': disease_percentages,
            'healthy_count': disease_counts.get('healthy', 0),
            'diseased_count': total_detections - disease_counts.get('healthy', 0)
        }
        
        return summary

def main():
    """Main inference function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Detect tobacco diseases using YOLOv8')
    parser.add_argument('--model', type=str, default='./runs/train/tobacco_disease_detection/weights/best.pt',
                       help='Path to trained model')
    parser.add_argument('--image', type=str, default=None,
                       help='Path to single image for detection')
    parser.add_argument('--dir', type=str, default=None,
                       help='Directory of images for batch detection')
    parser.add_argument('--conf', type=float, default=0.25,
                       help='Confidence threshold')
    parser.add_argument('--output', type=str, default=None,
                       help='Output JSON file for results')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save annotated images')
    
    args = parser.parse_args()
    
    # Create detector
    detector = TobaccoDiseaseDetector(
        model_path=args.model,
        conf_threshold=args.conf
    )
    
    # Run detection
    if args.image:
        # Single image detection
        result = detector.detect(args.image, save_annotated=not args.no_save)
        
        # Print results
        print("\n" + "="*60)
        print("TOBACCO DISEASE DETECTION RESULTS")
        print("="*60)
        print(f"Image: {result['image_path']}")
        print(f"Primary Disease: {result['primary_disease']}")
        print(f"Confidence: {result['primary_confidence']:.2%}")
        print(f"Total Detections: {result['num_detections']}")
        print("\nDetailed Detections:")
        for i, det in enumerate(result['detections'], 1):
            print(f"  {i}. {det['class']} - {det['confidence']:.2%}")
        print("="*60)
        
        # Save to JSON if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to {args.output}")
    
    elif args.dir:
        # Batch detection
        results = detector.batch_detect(args.dir, output_json=args.output)
        
        # Generate summary
        summary = detector.get_disease_summary(results)
        
        # Print summary
        print("\n" + "="*60)
        print("TOBACCO DISEASE BATCH DETECTION SUMMARY")
        print("="*60)
        print(f"Total Images: {summary['total_images']}")
        print(f"Total Detections: {summary['total_detections']}")
        print(f"Healthy: {summary['healthy_count']}")
        print(f"Diseased: {summary['diseased_count']}")
        print("\nDisease Distribution:")
        for disease, count in summary['disease_counts'].items():
            percentage = summary['disease_percentages'][disease]
            print(f"  {disease}: {count} ({percentage:.1f}%)")
        print("="*60)
    
    else:
        parser.print_help()
        print("\nError: Please provide either --image or --dir")

if __name__ == '__main__':
    main()
