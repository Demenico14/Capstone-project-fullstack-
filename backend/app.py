from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import os
from pathlib import Path
import logging
from PIL import Image
import io
import base64
import numpy as np
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Add disease_detection directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'disease_detection'))
try:
    from disease_yield_integration import DiseaseYieldIntegrator
    DISEASE_INTEGRATION_AVAILABLE = True
except ImportError as e:
    DISEASE_INTEGRATION_AVAILABLE = False
    print(f"Warning: Disease integration not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

# Model configuration
MODEL_PATH = os.getenv(
    'MODEL_PATH',
    'disease_detection/runs/classify/tobacco_disease_classification/weights/best.pt'
)

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'cropiot')

# Load model
model = None
mongo_client = None
mongo_db = None
disease_collection = None
disease_integrator = None

def init_mongodb():
    """Initialize MongoDB connection"""
    global mongo_client, mongo_db, disease_collection
    
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.admin.command('ping')
        
        mongo_db = mongo_client[MONGODB_DATABASE]
        disease_collection = mongo_db['disease_detections']
        
        # Create indexes for better query performance
        disease_collection.create_index([('timestamp', DESCENDING)])
        disease_collection.create_index([('disease_type', 1)])
        
        logger.info(f"✓ Connected to MongoDB: {MONGODB_DATABASE}.disease_detections")
        return True
        
    except ConnectionFailure as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        logger.warning("⚠ Disease detections will not be saved to database")
        return False
    except Exception as e:
        logger.error(f"✗ MongoDB initialization error: {e}")
        return False

def load_model():
    """Load the YOLO classification model"""
    global model, disease_integrator
    try:
        model_file = Path(MODEL_PATH)
        if not model_file.exists():
            logger.error(f"Model file not found at {MODEL_PATH}")
            return False
        
        logger.info(f"Loading model from {MODEL_PATH}")
        model = YOLO(MODEL_PATH)
        logger.info("Model loaded successfully")
        logger.info(f"Model classes: {model.names}")
        
        if DISEASE_INTEGRATION_AVAILABLE:
            disease_integrator = DiseaseYieldIntegrator()
            logger.info("✓ Disease integrator initialized")
        
        return True
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False

def get_disease_recommendations(disease_type):
    """
    Get comprehensive recommendations based on detected disease type
    """
    disease_lower = disease_type.lower()
    
    if 'no cercospora nicotianae or alternaria alternata present' in disease_lower or 'no disease' in disease_lower:
        return {
            'disease_name': 'Healthy',  # Changed from 'Healthy Plant' to 'Healthy' for consistency
            'description': 'No cercospora nicotianae or alternaria alternata present. Healthy plant condition.',
            'symptoms': [
                'No visible disease symptoms',
                'Plant appears healthy'
            ],
            'actions': [
                'Continue regular monitoring for early detection of disease',
                'Maintain plant health with balanced fertilization',
                'Keep optimal watering schedule — not too much or too little',
                'Clean tools and equipment to prevent contamination',
                'Rotate crops annually to prevent soil-borne diseases',
                'Inspect nearby plants for disease signs to act early if necessary'
            ],
            'severity': 'none',
            'is_healthy': True
        }
    elif 'alternaria alternata' in disease_lower:
        return {
            'disease_name': 'Alternaria alternata',
            'description': 'A fungal disease that causes leaf spots and can reduce plant yield.',
            'symptoms': [
                'Brown or black spots on leaves',
                'Yellowing of surrounding tissue',
                'Leaf drop in severe cases'
            ],
            'actions': [
                'Remove infected leaves to stop spread',
                'Apply appropriate fungicide (e.g., mancozeb, chlorothalonil, or azoxystrobin)',
                'Improve airflow between plants by pruning or increasing spacing',
                'Avoid overhead watering to reduce leaf wetness',
                'Rotate crops — avoid planting the same crop in the same spot repeatedly',
                'Monitor regularly — early detection reduces damage'
            ],
            'severity': 'moderate',
            'is_healthy': False
        }
    elif 'cercospora nicotianae' in disease_lower:
        return {
            'disease_name': 'Cercospora nicotianae',
            'description': 'A fungal disease common in tobacco and other plants.',
            'symptoms': [
                'Circular to irregular greyish spots on leaves',
                'Yellow halos around spots',
                'Leaf blight in severe cases'
            ],
            'actions': [
                'Remove infected leaves to limit spread',
                'Apply fungicides such as copper-based products or chlorothalonil',
                'Improve plant spacing for airflow',
                'Avoid excessive irrigation — keep leaves dry',
                'Practice crop rotation to reduce spores in soil',
                'Weed control to reduce alternate hosts'
            ],
            'severity': 'moderate',
            'is_healthy': False
        }
    else:
        return {
            'disease_name': 'Unknown',
            'description': 'Disease type not recognized.',
            'symptoms': ['Unknown symptoms'],
            'actions': ['Consult with agricultural expert'],
            'severity': 'unknown',
            'is_healthy': False
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'model_path': MODEL_PATH,
        'mongodb_connected': disease_collection is not None,
        'disease_integration': DISEASE_INTEGRATION_AVAILABLE
    })

@app.route('/api/detect', methods=['POST'])
def detect_disease():
    """
    Detect disease from uploaded image
    Expects: multipart/form-data with 'image' file
    Returns: JSON with prediction results
    """
    try:
        if model is None:
            return jsonify({'error': 'Model not loaded'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        logger.info(f"Running inference on image: {file.filename}")
        results = model(image)
        
        result = results[0]
        probs = result.probs
        
        logger.info(f"[v0] Model names: {model.names}")
        logger.info(f"[v0] Probs data: {probs.data.tolist()}")
        logger.info(f"[v0] Top1 index: {probs.top1}")
        logger.info(f"[v0] Top1 confidence: {probs.top1conf}")
        
        top_class_idx = probs.top1
        top_class_name = model.names[top_class_idx]
        top_confidence = float(probs.top1conf)
        
        logger.info(f"[v0] Detected class: {top_class_name} at index {top_class_idx} with confidence {top_confidence}")
        
        all_predictions = []
        for idx, conf in enumerate(probs.data.tolist()):
            class_name = model.names[idx]
            all_predictions.append({
                'class': class_name,
                'confidence': float(conf)
            })
            logger.info(f"[v0] Class {idx}: {class_name} = {conf:.4f}")
        
        all_predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        recommendations = get_disease_recommendations(top_class_name)
        
        display_disease_type = recommendations['disease_name']
        
        timestamp = datetime.now()
        
        response = {
            'success': True,
            'disease_type': display_disease_type,
            'original_class': top_class_name,
            'confidence': top_confidence,
            'num_detections': 1,
            'timestamp': timestamp.isoformat(),
            'detections': all_predictions[:5],
            'recommendations': recommendations,
            'filename': file.filename,
            'prediction': {
                'class': top_class_name,
                'confidence': top_confidence
            },
            'all_predictions': all_predictions[:5]
        }
        
        if disease_collection is not None:
            try:
                detection_record = {
                    'timestamp': timestamp,
                    'sensor_id': request.form.get('sensor_id', 'web_upload'),
                    'image_filename': file.filename,
                    'disease_type': display_disease_type,
                    'original_class': top_class_name,
                    'confidence': top_confidence,
                    'num_detections': 1,
                    'detections': all_predictions[:5],
                    'recommendations': recommendations
                }
                
                disease_collection.insert_one(detection_record)
                logger.info(f"✓ Saved detection to MongoDB: {display_disease_type} ({top_confidence:.2%})")
            except PyMongoError as e:
                logger.error(f"✗ Failed to save to MongoDB: {e}")
        
        logger.info(f"Prediction: {display_disease_type} ({top_confidence:.2%})")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error during detection: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect/base64', methods=['POST'])
def detect_disease_base64():
    """
    Detect disease from base64 encoded image
    Expects: JSON with 'image' field containing base64 string
    Returns: JSON with prediction results
    """
    try:
        if model is None:
            return jsonify({'error': 'Model not loaded'}), 500
        
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400
        
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        logger.info("Running inference on base64 image")
        results = model(image)
        
        result = results[0]
        probs = result.probs
        
        top_class_idx = probs.top1
        top_class_name = model.names[top_class_idx]
        top_confidence = float(probs.top1conf)
        
        all_predictions = []
        for idx, conf in enumerate(probs.data.tolist()):
            class_name = model.names[idx]
            all_predictions.append({
                'class': class_name,
                'confidence': float(conf)
            })
        
        all_predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        recommendations = get_disease_recommendations(top_class_name)
        
        display_disease_type = recommendations['disease_name']
        
        timestamp = datetime.now()
        
        response = {
            'success': True,
            'disease_type': display_disease_type,
            'original_class': top_class_name,
            'confidence': top_confidence,
            'num_detections': 1,
            'timestamp': timestamp.isoformat(),
            'detections': all_predictions[:5],
            'recommendations': recommendations,
            'filename': 'base64_image',
            'prediction': {
                'class': top_class_name,
                'confidence': top_confidence
            },
            'all_predictions': all_predictions[:5]
        }
        
        if disease_collection is not None:
            try:
                detection_record = {
                    'timestamp': timestamp,
                    'sensor_id': 'base64_upload',
                    'image_filename': 'base64_image',
                    'disease_type': display_disease_type,
                    'original_class': top_class_name,
                    'confidence': top_confidence,
                    'num_detections': 1,
                    'detections': all_predictions[:5],
                    'recommendations': recommendations
                }
                
                disease_collection.insert_one(detection_record)
                logger.info(f"✓ Saved detection to MongoDB: {display_disease_type} ({top_confidence:.2%})")
            except PyMongoError as e:
                logger.error(f"✗ Failed to save to MongoDB: {e}")
        
        logger.info(f"Prediction: {display_disease_type} ({top_confidence:.2%})")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error during detection: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/model/info', methods=['GET'])
def model_info():
    """Get information about the loaded model"""
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    return jsonify({
        'model_path': MODEL_PATH,
        'classes': model.names,
        'num_classes': len(model.names)
    })

if __name__ == '__main__':
    mongodb_available = init_mongodb()
    
    if load_model():
        logger.info("=" * 60)
        logger.info("Disease Detection API Server")
        logger.info("=" * 60)
        logger.info(f"Server: http://localhost:8000")
        logger.info(f"Model: {MODEL_PATH}")
        logger.info(f"MongoDB: {'Connected' if mongodb_available else 'Not connected'}")
        logger.info(f"Disease Integration: {'Enabled' if DISEASE_INTEGRATION_AVAILABLE else 'Disabled'}")
        logger.info("=" * 60)
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        logger.error("Failed to load model. Server not started.")
