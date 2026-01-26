#!/usr/bin/env python3
"""
Tobacco Disease Classification Training Script
Train image classification model for tobacco disease detection
"""

import os
import sys
from pathlib import Path
from ultralytics import YOLO
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TobaccoClassificationTrainer:
    """Train classification model for tobacco disease detection"""
    
    def __init__(self, model_size='n', dataset_path='./dataset'):
        """
        Initialize classification trainer
        
        Args:
            model_size: YOLOv8 model size ('n', 's', 'm', 'l', 'x')
            dataset_path: Path to dataset directory (folder format from Roboflow)
        """
        self.model_size = model_size
        self.dataset_path = Path(dataset_path)
        self.model_path = f'yolov8{model_size}-cls.pt'  # Classification model
        self.output_dir = Path('./runs/classify')
        
        logger.info(f"Initializing Tobacco Classification Trainer with YOLOv8{model_size}-cls")
        logger.info(f"Dataset path: {self.dataset_path}")
    
    def verify_dataset_structure(self):
        """
        Verify folder-based dataset structure
        
        Expected structure (folder format from Roboflow):
        dataset/
          ├── train/
          │   ├── class1/
          │   │   ├── image1.jpg
          │   │   └── image2.jpg
          │   ├── class2/
          │   │   ├── image1.jpg
          │   │   └── image2.jpg
          │   └── ...
          ├── valid/
          │   ├── class1/
          │   ├── class2/
          │   └── ...
          └── test/ (optional)
              ├── class1/
              ├── class2/
              └── ...
        """
        train_dir = self.dataset_path / 'train'
        valid_dir = self.dataset_path / 'valid'
        test_dir = self.dataset_path / 'test'
        
        if not train_dir.exists():
            raise ValueError(f"Training directory not found: {train_dir}")
        if not valid_dir.exists():
            raise ValueError(f"Validation directory not found: {valid_dir}")
        
        train_classes = set([d.name for d in train_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
        valid_classes = set([d.name for d in valid_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
        test_classes = set([d.name for d in test_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]) if test_dir.exists() else set()
        
        if not train_classes:
            raise ValueError(f"No class directories found in {train_dir}")
        
        logger.info(f"Found {len(train_classes)} classes in train: {sorted(train_classes)}")
        logger.info(f"Found {len(valid_classes)} classes in valid: {sorted(valid_classes)}")
        if test_classes:
            logger.info(f"Found {len(test_classes)} classes in test: {sorted(test_classes)}")
        
        if train_classes != valid_classes:
            missing_in_valid = train_classes - valid_classes
            extra_in_valid = valid_classes - train_classes
            
            error_msg = "\n❌ CLASS MISMATCH ERROR:\n"
            error_msg += f"  Train has {len(train_classes)} classes: {sorted(train_classes)}\n"
            error_msg += f"  Valid has {len(valid_classes)} classes: {sorted(valid_classes)}\n"
            
            if missing_in_valid:
                error_msg += f"\n  Missing in valid: {sorted(missing_in_valid)}\n"
                error_msg += f"  → Add these folders to: {valid_dir}\n"
            
            if extra_in_valid:
                error_msg += f"\n  Extra in valid: {sorted(extra_in_valid)}\n"
                error_msg += f"  → Remove these folders from: {valid_dir}\n"
            
            error_msg += "\n💡 FIX: Ensure train/, valid/, and test/ have the exact same class folders."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if test_classes and train_classes != test_classes:
            missing_in_test = train_classes - test_classes
            extra_in_test = test_classes - train_classes
            
            error_msg = "\n❌ CLASS MISMATCH ERROR:\n"
            error_msg += f"  Train has {len(train_classes)} classes: {sorted(train_classes)}\n"
            error_msg += f"  Test has {len(test_classes)} classes: {sorted(test_classes)}\n"
            
            if missing_in_test:
                error_msg += f"\n  Missing in test: {sorted(missing_in_test)}\n"
                error_msg += f"  → Add these folders to: {test_dir}\n"
            
            if extra_in_test:
                error_msg += f"\n  Extra in test: {sorted(extra_in_test)}\n"
                error_msg += f"  → Remove these folders from: {test_dir}\n"
            
            error_msg += "\n💡 FIX: Ensure train/, valid/, and test/ have the exact same class folders."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        classes = sorted(train_classes)
        logger.info(f"✓ All splits have {len(classes)} matching classes")
        
        # Count images per class
        total_train = 0
        total_valid = 0
        total_test = 0
        
        for class_name in classes:
            train_class_dir = train_dir / class_name
            valid_class_dir = valid_dir / class_name
            test_class_dir = test_dir / class_name if test_dir.exists() else None
            
            train_count = len(list(train_class_dir.glob('*.*'))) if train_class_dir.exists() else 0
            valid_count = len(list(valid_class_dir.glob('*.*'))) if valid_class_dir.exists() else 0
            test_count = len(list(test_class_dir.glob('*.*'))) if test_class_dir and test_class_dir.exists() else 0
            
            total_train += train_count
            total_valid += valid_count
            total_test += test_count
            
            if test_count > 0:
                logger.info(f"  {class_name}: {train_count} train, {valid_count} valid, {test_count} test")
            else:
                logger.info(f"  {class_name}: {train_count} train, {valid_count} valid")
        
        if total_test > 0:
            logger.info(f"Total images: {total_train} train, {total_valid} valid, {total_test} test")
        else:
            logger.info(f"Total images: {total_train} train, {total_valid} valid")
        
        return classes
    
    def train(self, epochs=100, imgsz=224, batch=32, patience=50):
        """
        Train classification model
        
        Args:
            epochs: Number of training epochs
            imgsz: Image size for training (224 is standard for classification)
            batch: Batch size
            patience: Early stopping patience
        """
        try:
            # Verify dataset
            classes = self.verify_dataset_structure()
            
            # Load pretrained classification model
            logger.info(f"Loading YOLOv8{self.model_size}-cls pretrained model...")
            model = YOLO(self.model_path)
            
            # Train the model
            logger.info("Starting tobacco disease classification training...")
            logger.info(f"Epochs: {epochs}, Image size: {imgsz}, Batch: {batch}")
            
            results = model.train(
                data=str(self.dataset_path),
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                patience=patience,
                save=True,
                project='runs/classify',
                name='tobacco_disease_classification',
                exist_ok=True,
                pretrained=True,
                optimizer='AdamW',
                verbose=True,
                seed=42,
                deterministic=True,
                cos_lr=True,
                resume=False,
                amp=True,
                lr0=0.01,
                lrf=0.01,
                momentum=0.937,
                weight_decay=0.0005,
                warmup_epochs=3.0,
                warmup_momentum=0.8,
                warmup_bias_lr=0.1,
                # Classification-specific augmentation
                hsv_h=0.015,
                hsv_s=0.7,
                hsv_v=0.4,
                degrees=10.0,
                translate=0.1,
                scale=0.5,
                shear=0.0,
                perspective=0.0,
                flipud=0.0,
                fliplr=0.5,
                mosaic=0.0,  # Not used in classification
                mixup=0.0,   # Not used in classification
            )
            
            logger.info("Training completed successfully!")
            logger.info(f"Best model saved to: {results.save_dir}")
            
            # Validate the model
            logger.info("Running validation...")
            metrics = model.val()
            
            logger.info(f"Validation Top-1 Accuracy: {metrics.top1:.4f}")
            logger.info(f"Validation Top-5 Accuracy: {metrics.top5:.4f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def export_model(self, format='onnx'):
        """Export trained model"""
        try:
            best_model_path = self.output_dir / 'tobacco_disease_classification' / 'weights' / 'best.pt'
            
            if not best_model_path.exists():
                logger.error(f"Best model not found at {best_model_path}")
                return
            
            logger.info(f"Exporting model to {format}...")
            model = YOLO(str(best_model_path))
            model.export(format=format)
            
            logger.info(f"Model exported successfully!")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

def main():
    """Main training function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train classification model for tobacco disease detection')
    parser.add_argument('--model', type=str, default='n', choices=['n', 's', 'm', 'l', 'x'],
                       help='YOLOv8 model size')
    parser.add_argument('--data', type=str, default='./dataset',
                       help='Path to dataset directory')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of training epochs')
    parser.add_argument('--imgsz', type=int, default=224,
                       help='Image size for training')
    parser.add_argument('--batch', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--patience', type=int, default=50,
                       help='Early stopping patience')
    parser.add_argument('--export', type=str, default=None,
                       help='Export format after training')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = TobaccoClassificationTrainer(
        model_size=args.model,
        dataset_path=args.data
    )
    
    # Train model
    trainer.train(
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience
    )
    
    # Export if requested
    if args.export:
        trainer.export_model(format=args.export)

if __name__ == '__main__':
    main()
