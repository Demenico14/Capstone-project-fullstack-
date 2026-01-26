#!/usr/bin/env python3
"""
Dataset Verification Script
Verify the downloaded Roboflow dataset structure and contents
"""

import os
from pathlib import Path
from collections import defaultdict

def verify_dataset(dataset_path='./dataset'):
    """Verify dataset structure and provide statistics"""
    
    dataset_path = Path(dataset_path)
    
    print("=" * 60)
    print("DATASET VERIFICATION")
    print("=" * 60)
    print(f"\nDataset location: {dataset_path.absolute()}")
    
    if not dataset_path.exists():
        print(f"\nERROR: Dataset directory not found!")
        print(f"Expected location: {dataset_path.absolute()}")
        print("\nPlease run: python roboflow_download.py")
        return False
    
    # Check for train/valid/test directories
    splits = ['train', 'valid', 'test']
    found_splits = []
    
    print("\n" + "-" * 60)
    print("DATASET STRUCTURE")
    print("-" * 60)
    
    for split in splits:
        split_dir = dataset_path / split
        if split_dir.exists():
            found_splits.append(split)
            print(f"✓ {split}/ directory found")
        else:
            print(f"✗ {split}/ directory not found")
    
    if not found_splits:
        print("\nERROR: No train/valid/test directories found!")
        print("Please check your dataset download.")
        return False
    
    # Analyze each split
    print("\n" + "-" * 60)
    print("CLASS DISTRIBUTION")
    print("-" * 60)
    
    all_classes = set()
    split_stats = {}
    
    for split in found_splits:
        split_dir = dataset_path / split
        classes = [d.name for d in split_dir.iterdir() if d.is_dir()]
        all_classes.update(classes)
        
        class_counts = {}
        total_images = 0
        
        for class_name in classes:
            class_dir = split_dir / class_name
            # Count image files
            image_files = list(class_dir.glob('*.jpg')) + \
                         list(class_dir.glob('*.jpeg')) + \
                         list(class_dir.glob('*.png'))
            count = len(image_files)
            class_counts[class_name] = count
            total_images += count
        
        split_stats[split] = {
            'classes': class_counts,
            'total': total_images
        }
        
        print(f"\n{split.upper()} SET:")
        print(f"  Total images: {total_images}")
        print(f"  Classes: {len(classes)}")
        for class_name in sorted(classes):
            count = class_counts.get(class_name, 0)
            percentage = (count / total_images * 100) if total_images > 0 else 0
            print(f"    - {class_name}: {count} images ({percentage:.1f}%)")
    
    # Summary
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Total classes: {len(all_classes)}")
    print(f"Class names: {', '.join(sorted(all_classes))}")
    print(f"\nTotal images across all splits:")
    for split in found_splits:
        print(f"  {split}: {split_stats[split]['total']} images")
    
    total_all = sum(stats['total'] for stats in split_stats.values())
    print(f"  TOTAL: {total_all} images")
    
    # Check for issues
    print("\n" + "-" * 60)
    print("VALIDATION CHECKS")
    print("-" * 60)
    
    issues = []
    
    # Check if train set exists
    if 'train' not in found_splits:
        issues.append("Missing train set")
    
    # Check if valid set exists
    if 'valid' not in found_splits:
        issues.append("Missing validation set")
    
    # Check for empty classes
    for split, stats in split_stats.items():
        for class_name, count in stats['classes'].items():
            if count == 0:
                issues.append(f"Empty class '{class_name}' in {split} set")
    
    # Check for class imbalance
    if 'train' in split_stats:
        train_classes = split_stats['train']['classes']
        if train_classes:
            max_count = max(train_classes.values())
            min_count = min(train_classes.values())
            if max_count > 0 and min_count > 0:
                imbalance_ratio = max_count / min_count
                if imbalance_ratio > 5:
                    issues.append(f"Severe class imbalance (ratio: {imbalance_ratio:.1f}:1)")
    
    if issues:
        print("\nWARNINGS:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("\n✓ All validation checks passed!")
    
    print("\n" + "=" * 60)
    print("Dataset is ready for training!")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    import sys
    
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else './dataset'
    verify_dataset(dataset_path)
