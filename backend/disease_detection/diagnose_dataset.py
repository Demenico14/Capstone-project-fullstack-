#!/usr/bin/env python3
"""
Roboflow Dataset Diagnostics
Checks dataset status and provides alternative download methods
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def check_dataset_via_api():
    """Check dataset status using Roboflow API directly"""
    
    api_key = os.getenv('ROBOFLOW_API_KEY')
    workspace = os.getenv('ROBOFLOW_WORKSPACE', 'tobaccoleafdiseasedetection')
    project = os.getenv('ROBOFLOW_PROJECT', 'tobacco-leaf-disease-detection-j3awg-yavvr')
    version = os.getenv('ROBOFLOW_VERSION', '1')
    
    print("=" * 70)
    print("ROBOFLOW DATASET DIAGNOSTICS")
    print("=" * 70)
    print(f"Workspace: {workspace}")
    print(f"Project: {project}")
    print(f"Version: {version}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print("=" * 70)
    print()
    
    # Check project info
    print("Step 1: Checking project information...")
    project_url = f"https://api.roboflow.com/{workspace}/{project}/{version}"
    
    try:
        response = requests.get(
            project_url,
            params={'api_key': api_key}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Project found!")
            print(f"  Project Name: {data.get('project', {}).get('name', 'N/A')}")
            print(f"  Version: {data.get('version', {}).get('name', 'N/A')}")
            
            version_data = data.get('version', {})
            print(f"  Images: {version_data.get('images', 'N/A')}")
            print(f"  Classes: {version_data.get('classes', 'N/A')}")
            print(f"  Splits: {version_data.get('splits', 'N/A')}")
            
            # Check if dataset has images
            image_count = version_data.get('images', 0)
            if image_count == 0:
                print("\n✗ WARNING: Dataset appears to be empty (0 images)")
                print("  This might be why the download isn't working.")
                return False
            
            print(f"\n✓ Dataset has {image_count} images")
            
        elif response.status_code == 401:
            print("✗ Authentication failed!")
            print("  Your API key might be invalid or expired.")
            return False
        elif response.status_code == 404:
            print("✗ Dataset not found!")
            print("  Check your workspace/project/version names.")
            return False
        else:
            print(f"✗ Unexpected response: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error checking project: {e}")
        return False
    
    print()
    print("=" * 70)
    print("ALTERNATIVE DOWNLOAD METHODS")
    print("=" * 70)
    print()
    
    # Method 1: Direct download link
    print("Method 1: Download via Web Browser")
    print("-" * 70)
    download_url = f"https://app.roboflow.com/{workspace}/{project}/{version}/download/folder"
    print(f"1. Open this URL in your browser:")
    print(f"   {download_url}")
    print(f"2. Log in to Roboflow if prompted")
    print(f"3. Download the dataset as 'folder' format")
    print(f"4. Extract the zip file to:")
    print(f"   {Path(__file__).parent / 'dataset'}")
    print()
    
    # Method 2: Direct API download
    print("Method 2: Direct API Download (try this)")
    print("-" * 70)
    print("Run this command:")
    print(f"python download_direct.py")
    print()
    
    # Method 3: Check permissions
    print("Method 3: Check Dataset Permissions")
    print("-" * 70)
    print("1. Go to: https://app.roboflow.com/")
    print(f"2. Navigate to: {workspace}/{project}")
    print("3. Check if the dataset is:")
    print("   - Public (anyone can download)")
    print("   - Private (only you can download)")
    print("4. If private, make sure you're using the correct API key")
    print()
    
    return True

if __name__ == "__main__":
    check_dataset_via_api()
