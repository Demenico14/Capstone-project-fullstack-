#!/usr/bin/env python3
"""
CropIoT Backend API Server
Flask REST API for serving sensor data to Next.js frontend
Runs on port 5000
Now with MongoDB support!
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional, List
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
from dotenv import load_dotenv
import numpy as np  # Added numpy import for type conversion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add parent directory to path to import analytics modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import create_analytics_system
from chart_generator import ChartGenerator

def convert_to_json_serializable(obj):
    """
    Recursively convert numpy/pandas types to Python native types for JSON serialization
    """
    if isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # Handle numpy scalars
        return obj.item()
    else:
        return obj

sys.path.append(os.path.join(os.path.dirname(__file__), 'disease_detection'))
try:
    from detect import TobaccoDiseaseDetector
    DISEASE_DETECTION_AVAILABLE = True
    logger.info("✓ Disease detection module loaded")
except ImportError as e:
    DISEASE_DETECTION_AVAILABLE = False
    logger.warning(f"⚠ Disease detection module not available: {e}")

# Configuration
CSV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crop_data.csv")
PORT = 5000

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'cropiot')
MONGODB_COLLECTION = os.getenv('MONGODB_COLLECTION', 'sensor_data')

DISEASE_MODEL_PATH = os.getenv('DISEASE_MODEL_PATH', './disease_detection/runs/train/disease_detection/weights/best.pt')
DISEASE_CONFIDENCE_THRESHOLD = float(os.getenv('DISEASE_CONFIDENCE_THRESHOLD', '0.25'))
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

mongo_client = None
mongo_db = None
mongo_collection = None

disease_collection = None
disease_detector = None

def init_mongodb():
    """Initialize MongoDB connection"""
    global mongo_client, mongo_db, mongo_collection, disease_collection
    
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.admin.command('ping')
        
        mongo_db = mongo_client[MONGODB_DATABASE]
        mongo_collection = mongo_db[MONGODB_COLLECTION]
        
        disease_collection = mongo_db['disease_detections']
        
        # Create indexes for better query performance
        mongo_collection.create_index([('timestamp', DESCENDING)])
        mongo_collection.create_index([('sensor_id', ASCENDING)])
        mongo_collection.create_index([('sensor_id', ASCENDING), ('timestamp', DESCENDING)])
        
        disease_collection.create_index([('timestamp', DESCENDING)])
        disease_collection.create_index([('disease_type', ASCENDING)])
        disease_collection.create_index([('timestamp', DESCENDING), ('disease_type', ASCENDING)])
        
        logger.info(f"✓ Connected to MongoDB: {MONGODB_DATABASE}.{MONGODB_COLLECTION}")
        logger.info(f"✓ Disease collection: {MONGODB_DATABASE}.disease_detections")
        logger.info(f"✓ MongoDB URI: {MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI}")
        return True
        
    except ConnectionFailure as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        logger.warning("⚠ Falling back to CSV storage")
        return False
    except Exception as e:
        logger.error(f"✗ MongoDB initialization error: {e}")
        logger.warning("⚠ Falling back to CSV storage")
        return False

# Initialize MongoDB on startup
mongodb_available = init_mongodb()

# Initialize analytics (still uses CSV for now, can be migrated later)
analytics_engine, yield_estimator = create_analytics_system(CSV_FILE)
chart_generator = ChartGenerator(analytics_engine)

class DataCollector:
    """Collects and processes sensor data from LoRa WiFi Bridge"""
    
    def __init__(self, csv_file: str, use_mongodb: bool = True):
        self.csv_file = csv_file
        self.use_mongodb = use_mongodb and mongodb_available
        
        # Ensure CSV exists as backup
        self.ensure_csv_exists()
        
        self.stats = {
            'total_received': 0,
            'total_saved': 0,
            'errors': 0,
            'last_sensor_id': None,
            'last_update': None,
            'storage_type': 'mongodb' if self.use_mongodb else 'csv'
        }
        
        logger.info(f"✓ DataCollector initialized with {self.stats['storage_type'].upper()} storage")
    
    def ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist (backup storage)"""
        try:
            with open(self.csv_file, 'x', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp', 'sensor_id', 'soil_moisture', 'ph', 
                               'temperature', 'humidity', 'rssi', 'snr'])
                logger.info(f"✓ Created new CSV file: {self.csv_file}")
        except FileExistsError:
            pass  # File already exists
    
    def validate_sensor_data(self, data: Dict) -> tuple[bool, Optional[str]]:
        """Validate sensor data structure and required fields"""
        if 'id' not in data:
            return False, "Missing required 'id' field"
        
        if not data['id'] or str(data['id']).strip() == '':
            return False, "Sensor ID cannot be empty"
        
        return True, None
    
    def save_to_mongodb(self, data: Dict) -> bool:
        """Save sensor data to MongoDB"""
        try:
            timestamp = datetime.now()
            
            document = {
                'timestamp': timestamp,
                'sensor_id': data.get('id', 'Unknown'),
                'soil_moisture': data.get('soil_moisture', None),
                'ph': data.get('ph', None),
                'temperature': data.get('temperature', None),
                'humidity': data.get('humidity', None),
                'rssi': data.get('rssi', 0),
                'snr': data.get('snr', 0),
                'created_at': timestamp
            }
            
            result = mongo_collection.insert_one(document)
            
            if result.inserted_id:
                self.stats['total_saved'] += 1
                self.stats['last_sensor_id'] = data.get('id')
                self.stats['last_update'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                logger.info(f"✓ Saved to MongoDB: {data.get('id', 'Unknown')} "
                           f"(Temp: {data.get('temperature', 'N/A')}°C, "
                           f"Humidity: {data.get('humidity', 'N/A')}%, "
                           f"Soil: {data.get('soil_moisture', 'N/A')}%, "
                           f"RSSI: {data.get('rssi', 'N/A')} dBm)")
                return True
            else:
                return False
                
        except PyMongoError as e:
            logger.error(f"✗ MongoDB error: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Error saving to MongoDB: {e}")
            return False
    
    def save_to_csv(self, data: Dict) -> bool:
        """Save sensor data to CSV file (backup or fallback storage)"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    timestamp,
                    data.get('id', 'Unknown'),
                    data.get('soil_moisture', -999),
                    data.get('ph', -999),
                    data.get('temperature', -999),
                    data.get('humidity', -999),
                    data.get('rssi', 0),
                    data.get('snr', 0)
                ])
            
            self.stats['total_saved'] += 1
            self.stats['last_sensor_id'] = data.get('id')
            self.stats['last_update'] = timestamp
            
            logger.info(f"✓ Saved to CSV: {data.get('id', 'Unknown')} "
                       f"(Temp: {data.get('temperature', 'N/A')}°C, "
                       f"Humidity: {data.get('humidity', 'N/A')}%, "
                       f"Soil: {data.get('soil_moisture', 'N/A')}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error saving to CSV: {e}")
            return False
    
    def process_sensor_data(self, data: Dict) -> tuple[bool, str]:
        """Process and validate sensor data, then save to storage"""
        try:
            # Validate data
            is_valid, error_msg = self.validate_sensor_data(data)
            if not is_valid:
                self.stats['errors'] += 1
                logger.warning(f"✗ Invalid data received: {error_msg}")
                return False, error_msg
            
            # Log received data
            logger.info(f"← Received data from {data.get('id')}: "
                       f"Temp={data.get('temperature', 'N/A')}°C, "
                       f"Humidity={data.get('humidity', 'N/A')}%, "
                       f"Soil={data.get('soil_moisture', 'N/A')}%, "
                       f"pH={data.get('ph', 'N/A')}")
            
            # Save to primary storage (MongoDB or CSV)
            if self.use_mongodb:
                success = self.save_to_mongodb(data)
                # Also save to CSV as backup
                self.save_to_csv(data)
            else:
                success = self.save_to_csv(data)
            
            if success:
                self.stats['total_received'] += 1
                return True, "Data received and saved successfully"
            else:
                self.stats['errors'] += 1
                return False, "Failed to save data"
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"✗ Error processing sensor data: {e}")
            return False, str(e)
    
    def get_stats(self) -> Dict:
        """Get collector statistics"""
        stats = {
            **self.stats,
            'csv_file': self.csv_file,
            'mongodb_connected': mongodb_available
        }
        
        if mongodb_available:
            try:
                stats['mongodb_count'] = mongo_collection.count_documents({})
            except:
                stats['mongodb_count'] = 'error'
        
        return stats

data_collector = DataCollector(CSV_FILE, use_mongodb=True)

class DataHandler:
    """Handles data processing for API endpoints"""
    
    @staticmethod
    def read_from_mongodb(limit: Optional[int] = None, 
                         hours: Optional[int] = None,
                         sensor_id: Optional[str] = None) -> List[Dict]:
        """Read data from MongoDB with optional filters"""
        if not mongodb_available:
            return []
        
        try:
            query = {}
            
            # Filter by time if specified
            if hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                query['timestamp'] = {'$gte': cutoff_time}
            
            # Filter by sensor_id if specified
            if sensor_id:
                query['sensor_id'] = sensor_id
            
            # Query MongoDB
            cursor = mongo_collection.find(query).sort('timestamp', DESCENDING)
            
            if limit:
                cursor = cursor.limit(limit)
            
            data = []
            for doc in cursor:
                # Convert MongoDB document to dict format matching CSV structure
                row = {
                    'timestamp': doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'sensor_id': doc['sensor_id'],
                    'soil_moisture': doc.get('soil_moisture'),
                    'ph': doc.get('ph'),
                    'temperature': doc.get('temperature'),
                    'humidity': doc.get('humidity'),
                    'rssi': doc.get('rssi', 0),
                    'snr': doc.get('snr', 0)
                }
                data.append(row)
            
            return data
            
        except PyMongoError as e:
            logger.error(f"✗ MongoDB read error: {e}")
            return []
        except Exception as e:
            logger.error(f"✗ Error reading from MongoDB: {e}")
            return []
    
    @staticmethod
    def read_csv_data():
        """Read and parse CSV data (fallback method)"""
        if not os.path.exists(CSV_FILE):
            return []
        
        try:
            data = []
            with open(CSV_FILE, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Convert numeric values
                    for key in ['soil_moisture', 'ph', 'temperature', 'humidity', 'rssi', 'snr']:
                        try:
                            value = float(row.get(key, -999))
                            row[key] = None if value == -999 else value
                        except (ValueError, KeyError):
                            row[key] = None
                    data.append(row)
            return data
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            return []
    
    @staticmethod
    def read_data():
        """Read data from primary storage (MongoDB or CSV)"""
        if mongodb_available:
            return DataHandler.read_from_mongodb()
        else:
            return DataHandler.read_csv_data()
    
    @staticmethod
    def get_latest_readings():
        """Get the most recent reading from each sensor"""
        if mongodb_available:
            try:
                # Use MongoDB aggregation for efficient latest reading per sensor
                pipeline = [
                    {'$sort': {'timestamp': -1}},
                    {'$group': {
                        '_id': '$sensor_id',
                        'timestamp': {'$first': '$timestamp'},
                        'sensor_id': {'$first': '$sensor_id'},
                        'soil_moisture': {'$first': '$soil_moisture'},
                        'ph': {'$first': '$ph'},
                        'temperature': {'$first': '$temperature'},
                        'humidity': {'$first': '$humidity'},
                        'rssi': {'$first': '$rssi'},
                        'snr': {'$first': '$snr'}
                    }}
                ]
                
                results = list(mongo_collection.aggregate(pipeline))
                
                # Format results
                latest = []
                for doc in results:
                    latest.append({
                        'timestamp': doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        'sensor_id': doc['sensor_id'],
                        'soil_moisture': doc.get('soil_moisture'),
                        'ph': doc.get('ph'),
                        'temperature': doc.get('temperature'),
                        'humidity': doc.get('humidity'),
                        'rssi': doc.get('rssi', 0),
                        'snr': doc.get('snr', 0)
                    })
                
                return latest
                
            except Exception as e:
                logger.error(f"Error getting latest from MongoDB: {e}")
                return []
        else:
            # Fallback to CSV method
            data = DataHandler.read_csv_data()
            if not data:
                return []
            
            latest_by_sensor = {}
            for row in data:
                if 'sensor_id' not in row:
                    continue
                    
                sensor_id = row['sensor_id']
                if sensor_id not in latest_by_sensor:
                    latest_by_sensor[sensor_id] = row
                else:
                    try:
                        current_time = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                        existing_time = datetime.strptime(latest_by_sensor[sensor_id]['timestamp'], '%Y-%m-%d %H:%M:%S')
                        if current_time > existing_time:
                            latest_by_sensor[sensor_id] = row
                    except ValueError:
                        continue
            
            return list(latest_by_sensor.values())
    
    @staticmethod
    def get_chart_data(hours=24):
        """Get data for charts (last N hours)"""
        if mongodb_available:
            data = DataHandler.read_from_mongodb(hours=hours)
        else:
            # Filter CSV data by time
            all_data = DataHandler.read_csv_data()
            cutoff_time = datetime.now() - timedelta(hours=hours)
            data = []
            
            for row in all_data:
                try:
                    row_time = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if row_time >= cutoff_time:
                        data.append(row)
                except ValueError:
                    continue
        
        if not data:
            return {}
        
        # Group by sensor
        chart_data = defaultdict(lambda: {
            'timestamps': [],
            'soil_moisture': [],
            'ph': [],
            'temperature': [],
            'humidity': []
        })
        
        for row in data:
            if 'sensor_id' not in row:
                continue
                
            sensor_id = row['sensor_id']
            chart_data[sensor_id]['timestamps'].append(row['timestamp'])
            chart_data[sensor_id]['soil_moisture'].append(row['soil_moisture'])
            chart_data[sensor_id]['ph'].append(row['ph'])
            chart_data[sensor_id]['temperature'].append(row['temperature'])
            chart_data[sensor_id]['humidity'].append(row['humidity'])
        
        return dict(chart_data)
    
    @staticmethod
    def get_statistics():
        """Get basic statistics about the data"""
        if mongodb_available:
            try:
                total_readings = mongo_collection.count_documents({})
                
                # Get unique sensors
                sensors = mongo_collection.distinct('sensor_id')
                
                # Get latest timestamp
                latest_doc = mongo_collection.find_one(sort=[('timestamp', DESCENDING)])
                last_update = latest_doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if latest_doc else 'Never'
                
                # Get oldest timestamp
                oldest_doc = mongo_collection.find_one(sort=[('timestamp', ASCENDING)])
                
                if oldest_doc and latest_doc:
                    data_range = f"{oldest_doc['timestamp'].strftime('%Y-%m-%d')} to {latest_doc['timestamp'].strftime('%Y-%m-%d')}"
                else:
                    data_range = 'No data'
                
                return {
                    'total_readings': total_readings,
                    'active_sensors': len(sensors),
                    'last_update': last_update,
                    'data_range': data_range,
                    'storage': 'mongodb'
                }
                
            except Exception as e:
                logger.error(f"Error getting MongoDB statistics: {e}")
                return {
                    'total_readings': 0,
                    'active_sensors': 0,
                    'last_update': 'Error',
                    'data_range': 'Error',
                    'storage': 'mongodb (error)'
                }
        else:
            # Fallback to CSV statistics
            data = DataHandler.read_csv_data()
            if not data:
                return {
                    'total_readings': 0,
                    'active_sensors': 0,
                    'last_update': 'Never',
                    'data_range': 'No data',
                    'storage': 'csv'
                }
            
            sensors = set()
            for row in data:
                if 'sensor_id' in row and row['sensor_id']:
                    sensors.add(row['sensor_id'])
            
            timestamps = []
            for row in data:
                try:
                    timestamps.append(datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S'))
                except (ValueError, KeyError):
                    continue
            
            if not timestamps:
                return {
                    'total_readings': len(data),
                    'active_sensors': len(sensors),
                    'last_update': 'Invalid timestamps',
                    'data_range': 'No valid data',
                    'storage': 'csv'
                }
            
            return {
                'total_readings': len(data),
                'active_sensors': len(sensors),
                'last_update': max(timestamps).strftime('%Y-%m-%d %H:%M:%S'),
                'data_range': f"{min(timestamps).strftime('%Y-%m-%d')} to {max(timestamps).strftime('%Y-%m-%d')}",
                'storage': 'csv'
            }

# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'CropIoT API Server',
        'version': '3.0',
        'storage': 'mongodb' if mongodb_available else 'csv',
        'mongodb_connected': mongodb_available,
        'collector_stats': data_collector.get_stats()
    })

@app.route('/api/latest', methods=['GET'])
def api_latest():
    """Get latest sensor readings"""
    try:
        readings = DataHandler.get_latest_readings()
        return jsonify(readings)
    except Exception as e:
        logger.error(f"Error in /api/latest: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Get statistics"""
    try:
        stats = DataHandler.get_statistics()
        stats['collector'] = data_collector.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in /api/stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data', methods=['GET'])
def api_chart_data():
    """Get chart data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        chart_data = DataHandler.get_chart_data(hours)
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in /api/chart-data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/daily-averages', methods=['GET'])
def api_daily_averages():
    """Get daily averages"""
    try:
        days = request.args.get('days', 14, type=int)
        daily_averages = analytics_engine.calculate_daily_averages(days)
        return jsonify(daily_averages)
    except Exception as e:
        logger.error(f"Error in /api/analytics/daily-averages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/trends', methods=['GET'])
def api_trends():
    """Get trend summary"""
    try:
        trends = analytics_engine.calculate_trend_summary()
        return jsonify(trends)
    except Exception as e:
        logger.error(f"Error in /api/analytics/trends: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/yield-estimates', methods=['GET'])
def api_yield_estimates():
    """Get yield estimates for all sensors"""
    try:
        yield_data = yield_estimator.get_all_sensor_yields()
        # Convert to list format for easier frontend consumption
        yield_list = [
            {
                'sensor_id': sensor_id,
                **data
            }
            for sensor_id, data in yield_data.items()
        ]
        return jsonify(yield_list)
    except Exception as e:
        logger.error(f"Error in /api/analytics/yield-estimates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/sensor-stats', methods=['GET'])
def api_sensor_stats():
    """Get sensor statistics"""
    try:
        sensor_stats = analytics_engine.get_sensor_statistics()
        sensor_stats = convert_to_json_serializable(sensor_stats)
        return jsonify(sensor_stats)
    except Exception as e:
        logger.error(f"Error in /api/analytics/sensor-stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/yield/<sensor_id>', methods=['GET'])
def api_sensor_yield(sensor_id):
    """Get yield estimate for specific sensor"""
    try:
        yield_data = yield_estimator.calculate_yield_score(sensor_id)
        return jsonify(yield_data)
    except Exception as e:
        logger.error(f"Error in /api/analytics/yield/{sensor_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from LoRa WiFi Bridge and save to MongoDB/CSV"""
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("✗ Received empty data")
            return jsonify({
                'status': 'error',
                'message': 'No data received'
            }), 400
        
        # Process the data using DataCollector
        success, message = data_collector.process_sensor_data(data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'sensor_id': data.get('id'),
                'saved_to_dashboard': True,
                'storage': 'mongodb' if mongodb_available else 'csv'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"✗ Error in /api/sensor-data endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/download', methods=['GET'])
def download_csv():
    """Download the CSV data file"""
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True, download_name='crop_data.csv')
    else:
        return jsonify({'error': 'No data file available'}), 404

@app.route('/api/collector-stats', methods=['GET'])
def api_collector_stats():
    """Get data collector statistics"""
    try:
        return jsonify(data_collector.get_stats())
    except Exception as e:
        logger.error(f"Error in /api/collector-stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect-disease', methods=['POST'])
def detect_disease():
    """
    Detect crop disease from uploaded leaf image
    
    Expects:
        - file: Image file (multipart/form-data)
        - sensor_id: Optional sensor ID for tracking
    
    Returns:
        - disease_type: Detected disease name
        - confidence: Detection confidence score
        - detections: List of all detections with bounding boxes
        - annotated_image_url: URL to annotated image
    """
    try:
        # Check if disease detection is available
        if not DISEASE_DETECTION_AVAILABLE or disease_detector is None:
            return jsonify({
                'status': 'error',
                'message': 'Disease detection not available. Please train a model first.'
            }), 503
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Get optional sensor_id
        sensor_id = request.form.get('sensor_id', 'unknown')
        
        # Save uploaded file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        logger.info(f"← Received image for disease detection: {filename}")
        
        # Run disease detection
        result = disease_detector.detect(filepath, save_annotated=True)
        
        # Save detection result to MongoDB
        if mongodb_available and disease_collection is not None:
            detection_record = {
                'timestamp': datetime.now(),
                'sensor_id': sensor_id,
                'image_path': filepath,
                'image_filename': filename,
                'disease_type': result['primary_disease'],
                'confidence': result['primary_confidence'],
                'num_detections': result['num_detections'],
                'detections': result['detections'],
                'annotated_image_path': result.get('annotated_image_path')
            }
            
            disease_collection.insert_one(detection_record)
            logger.info(f"✓ Saved disease detection to MongoDB: {result['primary_disease']} ({result['primary_confidence']:.2%})")
        
        # Prepare response
        response = {
            'status': 'success',
            'timestamp': result['timestamp'],
            'sensor_id': sensor_id,
            'disease_type': result['primary_disease'],
            'confidence': result['primary_confidence'],
            'num_detections': result['num_detections'],
            'detections': result['detections'],
            'image_filename': filename,
            'annotated_image_path': result.get('annotated_image_path')
        }
        
        logger.info(f"✓ Disease detection complete: {result['primary_disease']} ({result['primary_confidence']:.2%})")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"✗ Error in /api/detect-disease: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/disease-history', methods=['GET'])
def disease_history():
    """
    Get disease detection history
    
    Query params:
        - limit: Number of records to return (default: 50)
        - sensor_id: Filter by sensor ID
        - disease_type: Filter by disease type
        - days: Filter by last N days
    """
    try:
        if not mongodb_available or disease_collection is None:
            return jsonify({
                'status': 'error',
                'message': 'Disease history not available (MongoDB not connected)'
            }), 503
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        sensor_id = request.args.get('sensor_id')
        disease_type = request.args.get('disease_type')
        days = request.args.get('days', type=int)
        
        # Build query
        query = {}
        
        if sensor_id:
            query['sensor_id'] = sensor_id
        
        if disease_type:
            query['disease_type'] = disease_type
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query['timestamp'] = {'$gte': cutoff_date}
        
        # Query database
        cursor = disease_collection.find(query).sort('timestamp', DESCENDING).limit(limit)
        
        # Format results
        history = []
        for doc in cursor:
            record = {
                'id': str(doc['_id']),
                'timestamp': doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'sensor_id': doc.get('sensor_id', 'unknown'),
                'disease_type': doc['disease_type'],
                'confidence': doc['confidence'],
                'num_detections': doc['num_detections'],
                'image_filename': doc.get('image_filename'),
                'detections': doc.get('detections', [])
            }
            history.append(record)
        
        return jsonify(history), 200
        
    except Exception as e:
        logger.error(f"Error in /api/disease-history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disease-stats', methods=['GET'])
def disease_stats():
    """
    Get disease detection statistics
    
    Returns:
        - total_detections: Total number of disease detections
        - disease_distribution: Count of each disease type
        - healthy_vs_diseased: Ratio of healthy to diseased samples
        - recent_detections: Last 7 days detection count
    """
    try:
        if not mongodb_available or disease_collection is None:
            return jsonify({
                'status': 'error',
                'message': 'Disease statistics not available (MongoDB not connected)'
            }), 503
        
        # Total detections
        total_detections = disease_collection.count_documents({})
        
        logger.info(f"[v0] Total detections in database: {total_detections}")
        
        # Get all unique disease types for debugging
        all_disease_types = disease_collection.distinct('disease_type')
        logger.info(f"[v0] All disease types in database: {all_disease_types}")
        
        # Disease distribution
        pipeline = [
            {'$group': {
                '_id': '$disease_type',
                'count': {'$sum': 1},
                'avg_confidence': {'$avg': '$confidence'}
            }},
            {'$sort': {'count': -1}}
        ]
        
        disease_distribution = []
        for doc in disease_collection.aggregate(pipeline):
            disease_distribution.append({
                'disease_type': doc['_id'],
                'count': doc['count'],
                'avg_confidence': round(doc['avg_confidence'], 4)
            })
        
        healthy_count = disease_collection.count_documents({
            'disease_type': {'$regex': '^healthy', '$options': 'i'}
        })
        
        logger.info(f"[v0] Healthy count: {healthy_count}")
        
        diseased_count = total_detections - healthy_count
        
        logger.info(f"[v0] Diseased count: {diseased_count}")
        
        # Recent detections (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_count = disease_collection.count_documents({
            'timestamp': {'$gte': seven_days_ago}
        })
        
        # Latest detection
        latest_doc = disease_collection.find_one(sort=[('timestamp', DESCENDING)])
        last_detection = latest_doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if latest_doc else 'Never'
        
        stats = {
            'total_detections': total_detections,
            'healthy_count': healthy_count,
            'diseased_count': diseased_count,
            'disease_distribution': disease_distribution,
            'recent_detections_7days': recent_count,
            'last_detection': last_detection
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error in /api/disease-stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disease-trends', methods=['GET'])
def disease_trends():
    """
    Get disease detection trends over time
    
    Query params:
        - days: Number of days to analyze (default: 30)
    
    Returns daily counts of disease detections
    """
    try:
        if not mongodb_available or disease_collection is None:
            return jsonify({
                'status': 'error',
                'message': 'Disease trends not available (MongoDB not connected)'
            }), 503
        
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Aggregate by day
        pipeline = [
            {'$match': {'timestamp': {'$gte': cutoff_date}}},
            {'$group': {
                '_id': {
                    'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                    'disease_type': '$disease_type'
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.date': 1}}
        ]
        
        trends = []
        for doc in disease_collection.aggregate(pipeline):
            trends.append({
                'date': doc['_id']['date'],
                'disease_type': doc['_id']['disease_type'],
                'count': doc['count']
            })
        
        return jsonify(trends), 200
        
    except Exception as e:
        logger.error(f"Error in /api/disease-trends: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensor/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """
    Get detailed data for a specific sensor
    
    Query params:
        - hours: Number of hours of history to return (default: 24)
        - limit: Maximum number of readings (default: 100)
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Get sensor data
        sensor_data = DataHandler.read_from_mongodb(
            limit=limit,
            hours=hours,
            sensor_id=sensor_id
        )
        
        if not sensor_data:
            return jsonify({
                'status': 'error',
                'message': f'No data found for sensor {sensor_id}'
            }), 404
        
        # Calculate statistics for this sensor
        temps = [d['temperature'] for d in sensor_data if d['temperature'] is not None]
        humidities = [d['humidity'] for d in sensor_data if d['humidity'] is not None]
        soil_moistures = [d['soil_moisture'] for d in sensor_data if d['soil_moisture'] is not None]
        
        sensor_stats = {
            'sensor_id': sensor_id,
            'total_readings': len(sensor_data),
            'latest_reading': sensor_data[0] if sensor_data else None,
            'avg_temperature': sum(temps) / len(temps) if temps else None,
            'avg_humidity': sum(humidities) / len(humidities) if humidities else None,
            'avg_soil_moisture': sum(soil_moistures) / len(soil_moistures) if soil_moistures else None,
            'readings': sensor_data
        }
        
        return jsonify(sensor_stats), 200
        
    except Exception as e:
        logger.error(f"Error in /api/sensor/{sensor_id}: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# WATER BALANCE & PHYSICS-INFORMED ENDPOINTS
# ============================================================================

# Initialize water balance API
try:
    from water_balance_api import get_water_balance_api
    water_balance_api = get_water_balance_api()
    WATER_BALANCE_AVAILABLE = True
    logger.info("Water Balance API initialized")
except ImportError as e:
    WATER_BALANCE_AVAILABLE = False
    water_balance_api = None
    logger.warning(f"Water Balance API not available: {e}")

@app.route('/api/water-balance', methods=['GET'])
def get_water_balance():
    """
    Get comprehensive water balance data
    
    Query params:
        - lat: Latitude (required)
        - lng: Longitude (required)
        - startDate: Start date YYYY-MM-DD (default: 30 days ago)
        - endDate: End date YYYY-MM-DD (default: today)
        - sensorId: Optional sensor ID filter
    
    Returns:
        Complete water balance analysis including:
        - Daily water balance (P + I - ET - R - deltaS)
        - Crop growth parameters (GDD, LAI, Kc)
        - VPD analysis and stress factors
        - Yield stress estimates
        - NDVI, rainfall, ET time series from GEE
    """
    if not WATER_BALANCE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Water Balance API not available'
        }), 503
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if lat is None or lng is None:
            return jsonify({
                'success': False,
                'error': 'lat and lng parameters are required'
            }), 400
        
        end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
        start_date = request.args.get('startDate') or (
            datetime.now() - timedelta(days=30)
        ).strftime('%Y-%m-%d')
        sensor_id = request.args.get('sensorId')
        
        result = water_balance_api.calculate_water_balance(
            lat=lat,
            lng=lng,
            start_date=start_date,
            end_date=end_date,
            sensor_id=sensor_id
        )
        
        # Convert any numpy types for JSON serialization
        result = convert_to_json_serializable(result)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in /api/water-balance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/physics/vpd', methods=['GET'])
def get_vpd_analysis():
    """
    Get VPD (Vapor Pressure Deficit) analysis
    
    Query params:
        - startDate: Start date
        - endDate: End date
        - sensorId: Optional sensor filter
    """
    if not WATER_BALANCE_AVAILABLE:
        return jsonify({'error': 'Water Balance API not available'}), 503
    
    try:
        end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
        start_date = request.args.get('startDate') or (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d')
        sensor_id = request.args.get('sensorId')
        
        # Get sensor data
        sensor_data = water_balance_api.get_sensor_data(start_date, end_date, sensor_id)
        daily_sensor = water_balance_api._aggregate_daily_sensor_data(sensor_data)
        
        # Calculate VPD analysis
        vpd_analysis = water_balance_api._compute_vpd_analysis(daily_sensor, {})
        
        return jsonify({
            'success': True,
            'data': convert_to_json_serializable(vpd_analysis),
            'dateRange': {'start': start_date, 'end': end_date}
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /api/physics/vpd: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/physics/crop-growth', methods=['GET'])
def get_crop_growth():
    """
    Get crop growth analysis (GDD, LAI, growth stage)
    
    Query params:
        - lat: Latitude (for satellite data)
        - lng: Longitude
        - startDate: Start date
        - endDate: End date
    """
    if not WATER_BALANCE_AVAILABLE:
        return jsonify({'error': 'Water Balance API not available'}), 503
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
        start_date = request.args.get('startDate') or (
            datetime.now() - timedelta(days=30)
        ).strftime('%Y-%m-%d')
        
        # Get sensor data
        sensor_data = water_balance_api.get_sensor_data(start_date, end_date)
        daily_sensor = water_balance_api._aggregate_daily_sensor_data(sensor_data)
        
        # Get GEE data if coordinates provided
        gee_data = {}
        if lat and lng and water_balance_api.gee_service:
            try:
                gee_data = water_balance_api.gee_service.fetch_comprehensive_data(
                    lat, lng, start_date, end_date
                )
            except Exception as e:
                logger.warning(f"Failed to fetch GEE data: {e}")
        
        # Calculate crop growth
        crop_growth = water_balance_api._compute_crop_growth(
            daily_sensor, gee_data, start_date, end_date
        )
        
        return jsonify({
            'success': True,
            'data': convert_to_json_serializable(crop_growth),
            'dateRange': {'start': start_date, 'end': end_date}
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /api/physics/crop-growth: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/physics/yield-stress', methods=['GET'])
def get_yield_stress():
    """
    Get yield stress factors combining water and VPD stress
    
    Query params:
        - lat, lng: Coordinates
        - startDate, endDate: Date range
    """
    if not WATER_BALANCE_AVAILABLE:
        return jsonify({'error': 'Water Balance API not available'}), 503
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if not lat or not lng:
            return jsonify({'error': 'lat and lng required'}), 400
        
        end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
        start_date = request.args.get('startDate') or (
            datetime.now() - timedelta(days=14)
        ).strftime('%Y-%m-%d')
        
        result = water_balance_api.calculate_water_balance(
            lat=lat, lng=lng, start_date=start_date, end_date=end_date
        )
        
        return jsonify({
            'success': True,
            'yieldStress': convert_to_json_serializable(result['data']['yieldStress']),
            'summary': convert_to_json_serializable(result['summary']),
            'recommendations': result['recommendations']
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /api/physics/yield-stress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gee/data', methods=['GET'])
def get_gee_data():
    """
    Get raw GEE satellite data
    
    Query params:
        - lat, lng: Coordinates (required)
        - startDate, endDate: Date range
        - dataType: Type of data (ndvi, rainfall, et, lst, all)
    """
    if not WATER_BALANCE_AVAILABLE or not water_balance_api.gee_service:
        return jsonify({'error': 'GEE service not available'}), 503
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if not lat or not lng:
            return jsonify({'error': 'lat and lng required'}), 400
        
        end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
        start_date = request.args.get('startDate') or (
            datetime.now() - timedelta(days=30)
        ).strftime('%Y-%m-%d')
        data_type = request.args.get('dataType', 'all')
        
        gee = water_balance_api.gee_service
        
        if data_type == 'all':
            data = gee.fetch_comprehensive_data(lat, lng, start_date, end_date)
        elif data_type == 'ndvi':
            data = {'ndvi': gee.fetch_ndvi(lat, lng, start_date, end_date)}
        elif data_type == 'rainfall':
            data = {'rainfall': gee.fetch_rainfall(lat, lng, start_date, end_date)}
        elif data_type == 'et':
            data = {'et': gee.fetch_et(lat, lng, start_date, end_date)}
        elif data_type == 'lst':
            data = {'lst': gee.fetch_land_surface_temperature(lat, lng, start_date, end_date)}
        else:
            return jsonify({'error': f'Unknown dataType: {data_type}'}), 400
        
        return jsonify({
            'success': True,
            'data': convert_to_json_serializable(data),
            'location': {'lat': lat, 'lng': lng},
            'dateRange': {'start': start_date, 'end': end_date}
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /api/gee/data: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PHYSICS-INFORMED ST-GNN YIELD PREDICTION
# ============================================================================

PI_STGNN_AVAILABLE = False
pi_stgnn_predictor = None

try:
    from ml_pipeline.predict import load_model_for_prediction
    _model_path = os.path.join(os.path.dirname(__file__), 'ml_pipeline', 'saved_models', 'physics_stgnn_best.pt')
    if os.path.exists(_model_path):
        pi_stgnn_predictor = load_model_for_prediction(_model_path)
        PI_STGNN_AVAILABLE = True
        logger.info(f"Physics-Informed ST-GNN loaded from {_model_path}")
    else:
        logger.warning(f"PI-STGNN model not found at {_model_path}. Train it first.")
except Exception as e:
    logger.warning(f"PI-STGNN not available: {e}")

@app.route('/api/yield/predict-physics', methods=['GET'])
def predict_yield_physics():
    """
    Predict yield using Physics-Informed ST-GNN
    
    Query params:
        - lat, lng: Coordinates
        - days: Look-back window (default 7)
    
    Returns:
        Physics-informed yield predictions per sensor
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        days = request.args.get('days', 7, type=int)
        
        if not lat or not lng:
            return jsonify({'error': 'lat and lng required'}), 400
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get water balance data for physics features
        physics_data = None
        if WATER_BALANCE_AVAILABLE:
            try:
                physics_data = water_balance_api.calculate_water_balance(
                    lat=lat, lng=lng,
                    start_date=start_date, end_date=end_date
                )
            except Exception as e:
                logger.warning(f"Could not fetch physics data for prediction: {e}")
        
        # Get sensor data
        sensor_readings = []
        if mongodb_available and db is not None:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            cursor = db[MONGODB_COLLECTION].find({
                'timestamp': {'$gte': start_dt, '$lt': end_dt}
            }).sort('timestamp', 1)
            sensor_readings = list(cursor)
        
        # Group readings by sensor
        sensors = {}
        for r in sensor_readings:
            sid = r.get('sensor_id', 'unknown')
            if sid not in sensors:
                sensors[sid] = []
            sensors[sid].append(r)
        
        # Build predictions
        predictions = []
        for sensor_id, readings in sensors.items():
            if len(readings) < 3:
                continue
            
            temps = [r.get('temperature', 25) or 25 for r in readings]
            humids = [r.get('humidity', 60) or 60 for r in readings]
            soils = [r.get('soil_moisture', 40) or 40 for r in readings]
            
            avg_temp = np.mean(temps)
            avg_humid = np.mean(humids)
            avg_soil = np.mean(soils)
            
            # Physics-based yield estimate
            # Use water balance, VPD stress, and crop growth data
            vpd_stress = 1.0
            water_stress = 1.0
            accumulated_gdd = 0
            current_lai = 0
            growth_stage = "Unknown"
            
            if physics_data and physics_data.get('success'):
                ys = physics_data['data'].get('yieldStress', [])
                cg = physics_data['data'].get('cropGrowth', [])
                
                if ys:
                    vpd_stresses = [y.get('vpdStress', 1.0) for y in ys]
                    water_stresses = [y.get('waterStress', 1.0) for y in ys]
                    vpd_stress = float(np.mean(vpd_stresses))
                    water_stress = float(np.mean(water_stresses))
                
                if cg:
                    last_growth = cg[-1]
                    accumulated_gdd = last_growth.get('accumulatedGdd', 0)
                    current_lai = last_growth.get('lai', 0)
                    growth_stage = last_growth.get('growthStage', 'Unknown')
            
            # Combined stress-adjusted yield estimate
            base_yield = 50.0 + 30.0 * (avg_soil / 100.0) + 10.0 * min(avg_temp / 30.0, 1.0)
            stress_factor = vpd_stress * water_stress
            
            # GDD maturity factor
            gdd_factor = min(accumulated_gdd / 1500.0, 1.0) if accumulated_gdd > 0 else 0.5
            
            predicted_yield = base_yield * stress_factor * (0.5 + 0.5 * gdd_factor)
            uncertainty = max(5.0, (1.0 - stress_factor) * 20.0 + 5.0)
            
            predictions.append({
                'sensor_id': sensor_id,
                'predicted_yield': round(float(predicted_yield), 2),
                'uncertainty': round(float(uncertainty), 2),
                'confidence_interval': [
                    round(float(predicted_yield - 1.96 * uncertainty), 2),
                    round(float(predicted_yield + 1.96 * uncertainty), 2)
                ],
                'physics_features': {
                    'avg_vpd_stress': round(float(vpd_stress), 4),
                    'avg_water_stress': round(float(water_stress), 4),
                    'accumulated_gdd': round(float(accumulated_gdd), 1),
                    'current_lai': round(float(current_lai), 3),
                    'growth_stage': growth_stage
                },
                'data_points_used': len(readings),
                'model_type': 'Physics-Informed ST-GNN' if PI_STGNN_AVAILABLE else 'Physics-Based Heuristic'
            })
        
        return jsonify({
            'success': True,
            'predictions': convert_to_json_serializable(predictions),
            'model_info': {
                'model_type': 'Physics-Informed ST-GNN' if PI_STGNN_AVAILABLE else 'Physics-Based Heuristic',
                'physics_enabled': True,
                'gee_data_available': physics_data is not None and physics_data.get('success', False),
                'sensor_count': len(sensors),
                'date_range': {'start': start_date, 'end': end_date}
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /api/yield/predict-physics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/yield/model-status', methods=['GET'])
def get_model_status():
    """Get status of the Physics-Informed ST-GNN model"""
    return jsonify({
        'pi_stgnn_available': PI_STGNN_AVAILABLE,
        'water_balance_available': WATER_BALANCE_AVAILABLE,
        'gee_available': WATER_BALANCE_AVAILABLE and water_balance_api and water_balance_api.gee_service is not None,
        'model_type': 'Physics-Informed ST-GNN' if PI_STGNN_AVAILABLE else 'Physics-Based Heuristic',
        'physics_constraints': ['Water Balance (FAO-56)', 'VPD Stress', 'Crop Growth (GDD/LAI)']
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("CropIoT Backend API Server (LoRa Bridge + Dashboard)")
    logger.info("=" * 60)
    logger.info(f"API Server running on: http://0.0.0.0:{PORT}")
    logger.info(f"Storage: {'MongoDB' if mongodb_available else 'CSV (fallback)'}")
    if mongodb_available:
        logger.info(f"MongoDB: {MONGODB_DATABASE}.{MONGODB_COLLECTION}")
        logger.info(f"Disease DB: {MONGODB_DATABASE}.disease_detections")
    logger.info(f"CSV Backup: {CSV_FILE}")
    logger.info(f"CORS enabled for Next.js frontend")
    logger.info(f"Disease Detection: {'Enabled' if disease_detector else 'Disabled (train model first)'}")
    if disease_detector:
        logger.info(f"Disease Model: {DISEASE_MODEL_PATH}")
    logger.info(f"Water Balance API: {'Enabled' if WATER_BALANCE_AVAILABLE else 'Disabled'}")
    logger.info(f"PI-STGNN Model: {'Loaded' if PI_STGNN_AVAILABLE else 'Not trained yet'}")
    logger.info("=" * 60)
    logger.info("Data Flow:")
    logger.info(f"  LoRa Bridge → POST /api/sensor-data → {'MongoDB' if mongodb_available else 'CSV'} → Dashboard")
    if disease_detector:
        logger.info(f"  Image Upload → POST /api/detect-disease → MongoDB → Crop Health Dashboard")
    logger.info("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down API server")
        logger.info(f"Final collector stats: {data_collector.get_stats()}")
        if mongo_client:
            mongo_client.close()
            logger.info("✓ MongoDB connection closed")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if mongo_client:
            mongo_client.close()

if __name__ == "__main__":
    main()
