#!/usr/bin/env python3
"""
Data Augmentation Pipeline for Tobacco Disease Detection
Implements augmentation strategies for Zimbabwean field conditions
"""

import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TobaccoAugmentation:
    """Augmentation pipeline for tobacco disease images"""
    
    def __init__(self, image_size=640):
        """
        Initialize augmentation pipeline
        
        Args:
            image_size: Target image size for training
        """
        self.image_size = image_size
        
        # Training augmentation pipeline
        self.train_transform = A.Compose([
            # Geometric transformations
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.3),
            A.RandomRotate90(p=0.5),
            A.Rotate(limit=30, p=0.5),
            A.ShiftScaleRotate(
                shift_limit=0.1,
                scale_limit=0.2,
                rotate_limit=15,
                p=0.5
            ),
            
            # Lighting and color adjustments (for field conditions)
            A.RandomBrightnessContrast(
                brightness_limit=0.3,
                contrast_limit=0.3,
                p=0.7
            ),
            A.HueSaturationValue(
                hue_shift_limit=20,
                sat_shift_limit=30,
                val_shift_limit=20,
                p=0.5
            ),
            A.RandomGamma(gamma_limit=(80, 120), p=0.5),
            
            # Weather and environmental conditions
            A.OneOf([
                A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
            ], p=0.3),
            
            A.OneOf([
                A.MotionBlur(blur_limit=5, p=1.0),
                A.MedianBlur(blur_limit=5, p=1.0),
                A.GaussianBlur(blur_limit=5, p=1.0),
            ], p=0.2),
            
            # Shadow and lighting variations (field conditions)
            A.RandomShadow(
                shadow_roi=(0, 0.5, 1, 1),
                num_shadows_lower=1,
                num_shadows_upper=2,
                shadow_dimension=5,
                p=0.3
            ),
            
            # Color channel adjustments
            A.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=0.3),
            A.ChannelShuffle(p=0.1),
            
            # Quality degradation (simulating mobile camera quality)
            A.OneOf([
                A.ImageCompression(quality_lower=75, quality_upper=100, p=1.0),
                A.Downscale(scale_min=0.75, scale_max=0.95, p=1.0),
            ], p=0.2),
            
            # Resize to target size
            A.Resize(height=self.image_size, width=self.image_size),
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_visibility=0.3
        ))
        
        # Validation transform (no augmentation)
        self.val_transform = A.Compose([
            A.Resize(height=self.image_size, width=self.image_size),
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels']
        ))
    
    def augment_image(self, image, bboxes, class_labels, is_training=True):
        """
        Apply augmentation to image and bounding boxes
        
        Args:
            image: Input image (numpy array)
            bboxes: List of bounding boxes in YOLO format [x_center, y_center, width, height]
            class_labels: List of class labels for each bbox
            is_training: Whether to apply training augmentations
            
        Returns:
            Augmented image and bboxes
        """
        transform = self.train_transform if is_training else self.val_transform
        
        try:
            transformed = transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_labels
            )
            
            return transformed['image'], transformed['bboxes'], transformed['class_labels']
        except Exception as e:
            logger.warning(f"Augmentation failed: {e}")
            # Return original if augmentation fails
            return image, bboxes, class_labels
    
    def augment_dataset(self, input_dir, output_dir, multiplier=3):
        """
        Augment entire dataset by creating multiple versions of each image
        
        Args:
            input_dir: Input dataset directory
            output_dir: Output directory for augmented dataset
            multiplier: Number of augmented versions per image
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Process train and valid splits
        for split in ['train', 'valid']:
            images_dir = input_path / split / 'images'
            labels_dir = input_path / split / 'labels'
            
            if not images_dir.exists():
                continue
            
            output_images = output_path / split / 'images'
            output_labels = output_path / split / 'labels'
            output_images.mkdir(parents=True, exist_ok=True)
            output_labels.mkdir(parents=True, exist_ok=True)
            
            image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
            
            logger.info(f"Augmenting {split} set: {len(image_files)} images")
            
            for img_path in image_files:
                # Read image
                image = cv2.imread(str(img_path))
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Read labels
                label_path = labels_dir / f"{img_path.stem}.txt"
                bboxes = []
                class_labels = []
                
                if label_path.exists():
                    with open(label_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                class_labels.append(int(parts[0]))
                                bboxes.append([float(x) for x in parts[1:5]])
                
                # Create augmented versions
                for i in range(multiplier):
                    aug_image, aug_bboxes, aug_labels = self.augment_image(
                        image, bboxes, class_labels, is_training=(split == 'train')
                    )
                    
                    # Save augmented image
                    output_img_path = output_images / f"{img_path.stem}_aug{i}.jpg"
                    aug_image_bgr = cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(output_img_path), aug_image_bgr)
                    
                    # Save augmented labels
                    output_label_path = output_labels / f"{img_path.stem}_aug{i}.txt"
                    with open(output_label_path, 'w') as f:
                        for label, bbox in zip(aug_labels, aug_bboxes):
                            f.write(f"{label} {' '.join(map(str, bbox))}\n")
            
            logger.info(f"✓ Augmented {split} set saved to {output_path / split}")

def main():
    """Main augmentation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Augment tobacco disease dataset')
    parser.add_argument('--input', type=str, required=True,
                       help='Input dataset directory')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory for augmented dataset')
    parser.add_argument('--multiplier', type=int, default=3,
                       help='Number of augmented versions per image')
    parser.add_argument('--image-size', type=int, default=640,
                       help='Target image size')
    
    args = parser.parse_args()
    
    augmenter = TobaccoAugmentation(image_size=args.image_size)
    augmenter.augment_dataset(args.input, args.output, args.multiplier)
    
    logger.info("✓ Dataset augmentation complete!")

if __name__ == '__main__':
    main()
