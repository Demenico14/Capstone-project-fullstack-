"""
Flask API endpoints for ST-GNN yield predictions
Integrates with existing api_server.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import sys
from datetime import datetime, timedelta

# Load environment variables from .env file FIRST before any other imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Add ml_pipeline to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml_pipeline'))

from predict import create_predictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize predictor (lazy loading)
predictor = None


def get_predictor():
    """Get or create predictor instance"""
    global predictor
    
    if predictor is None:
        try:
            logger.info("Attempting to load yield prediction model...")
            predictor = create_predictor()
            logger.info("✓ Yield predictor initialized successfully")
        except FileNotFoundError as e:
            logger.error(f"✗ Model file not found: {e}")
            logger.error("Please train the model first using: python backend/ml_pipeline/train.py")
            raise
        except Exception as e:
            logger.error(f"✗ Failed to initialize predictor: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    return predictor


@app.route('/api/yield/predict/<sensor_id>', methods=['GET'])
def predict_sensor_yield(sensor_id):
    """
    Predict yield for a specific sensor
    
    Query params:
        - window_days: Number of days of history to use (default: 7)
    
    Returns:
        {
            "sensor_id": "sensor_1",
            "predicted_yield_kg": 85.5,
            "prediction_date": "2025-01-15T10:30:00",
            "window_start": "2025-01-08T10:30:00",
            "window_end": "2025-01-15T10:30:00",
            "window_days": 7
        }
    """
    try:
        window_days = request.args.get('window_days', 7, type=int)
        
        pred = get_predictor()
        result = pred.predict_sensor(sensor_id, window_days)
        
        return jsonify(result), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error predicting yield for {sensor_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/yield/predict-all', methods=['GET'])
def predict_all_yields():
    """
    Predict yield for all active sensors
    
    Query params:
        - window_days: Number of days of history to use (default: 7)
    
    Returns:
        {
            "predictions": [...],
            "model_info": {...},
            "timestamp": "2025-01-15T10:30:00"
        }
    """
    try:
        window_days = request.args.get('window_days', 7, type=int)
        
        pred = get_predictor()
        predictions = pred.predict_all_sensors(window_days)
        
        # Get model type from metadata or config
        model_type = 'unknown'
        if hasattr(pred, 'metadata') and pred.metadata:
            model_type = pred.metadata.get('model_type', 'unknown')
        elif hasattr(pred, 'config') and pred.config:
            model_type = pred.config.get('model', {}).get('model_type', 'unknown')
        
        # Get performance metrics from metadata (sklearn) or training history (pytorch)
        performance_metrics = {'mae': None, 'rmse': None, 'r2': None}
        trained_on = None
        
        if hasattr(pred, 'metadata') and pred.metadata:
            # Sklearn model from notebook
            metadata = pred.metadata
            if 'test_r2_score' in metadata:
                performance_metrics['r2'] = metadata['test_r2_score']
            if 'test_rmse' in metadata:
                performance_metrics['rmse'] = metadata['test_rmse']
            if 'test_mae' in metadata:
                performance_metrics['mae'] = metadata['test_mae']
            if 'training_date' in metadata:
                trained_on = metadata['training_date']
        else:
            # Try to load from training history for PyTorch models
            try:
                import json
                results_path = os.path.join(
                    os.path.dirname(__file__), 
                    'ml_pipeline', 
                    'results', 
                    'training_history.json'
                )
                if os.path.exists(results_path):
                    with open(results_path, 'r') as f:
                        history = json.load(f)
                        if 'val_loss' in history and len(history['val_loss']) > 0:
                            best_epoch = history['val_loss'].index(min(history['val_loss']))
                            performance_metrics = {
                                'mae': history.get('val_mae', [None])[best_epoch] if 'val_mae' in history else None,
                                'rmse': history.get('val_rmse', [None])[best_epoch] if 'val_rmse' in history else None,
                                'r2': history.get('val_r2', [None])[best_epoch] if 'val_r2' in history else None,
                            }
            except Exception as e:
                logger.warning(f"Could not load training history: {e}")
        
        response = {
            'predictions': predictions,
            'model_info': {
                'model_type': model_type,
                'trained_on': trained_on,
                'performance_metrics': performance_metrics
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error predicting yields: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/yield/model-info', methods=['GET'])
def model_info():
    """
    Get information about the loaded model
    
    Returns:
        {
            "model_loaded": true,
            "model_type": "Random Forest" or "stgnn",
            "num_parameters": "200 trees, 13 features",
            "device": "cpu",
            "performance_metrics": {...},
            "config": {...}
        }
    """
    try:
        pred = get_predictor()
        
        performance_metrics = {}
        
        # Get metadata if available (sklearn models from notebook have this)
        metadata = {}
        if hasattr(pred, 'metadata') and pred.metadata:
            metadata = pred.metadata
            # Extract metrics from notebook-trained models
            if 'test_r2_score' in metadata:
                performance_metrics['r2'] = metadata['test_r2_score']
            if 'test_rmse' in metadata:
                performance_metrics['rmse'] = metadata['test_rmse']
            if 'test_mae' in metadata:
                performance_metrics['mae'] = metadata['test_mae']
            if 'training_date' in metadata:
                performance_metrics['trained_on'] = metadata['training_date']
        
        # Try to load from training_history.json for PyTorch models
        if not performance_metrics:
            try:
                import json
                results_path = os.path.join(
                    os.path.dirname(__file__), 
                    'ml_pipeline', 
                    'results', 
                    'training_history.json'
                )
                if os.path.exists(results_path):
                    with open(results_path, 'r') as f:
                        history = json.load(f)
                        if 'val_loss' in history and len(history['val_loss']) > 0:
                            best_epoch = history['val_loss'].index(min(history['val_loss']))
                            performance_metrics = {
                                'mae': history.get('val_mae', [None])[best_epoch] if 'val_mae' in history else None,
                                'rmse': history.get('val_rmse', [None])[best_epoch] if 'val_rmse' in history else None,
                                'r2': history.get('val_r2', [None])[best_epoch] if 'val_r2' in history else None,
                                'loss': history['val_loss'][best_epoch]
                            }
            except Exception as e:
                logger.warning(f"Could not load training history: {e}")
        
        # Get model info - handle both sklearn and PyTorch models
        num_parameters = None
        device = 'cpu'
        model_type = metadata.get('model_type', 'unknown')
        
        # Check if predictor has config
        if hasattr(pred, 'config') and pred.config and model_type == 'unknown':
            model_type = pred.config.get('model', {}).get('model_type', 'unknown')
        
        # Try to get parameters count based on model type
        if hasattr(pred, 'model'):
            model = pred.model
            # Check if it's a PyTorch model
            if hasattr(model, 'parameters'):
                try:
                    num_parameters = sum(p.numel() for p in model.parameters())
                except:
                    pass
            # Check if it's a sklearn model (Random Forest, etc.)
            elif hasattr(model, 'n_estimators'):
                # For Random Forest/Gradient Boosting, count estimators and features
                if hasattr(model, 'n_features_in_'):
                    num_parameters = f"{model.n_estimators} trees, {model.n_features_in_} features"
                else:
                    num_parameters = f"{model.n_estimators} trees"
            elif hasattr(model, 'coef_'):
                # For linear models
                num_parameters = len(model.coef_) if hasattr(model.coef_, '__len__') else 1
        
        # Get device if available
        if hasattr(pred, 'device'):
            device = str(pred.device)
        
        # Get feature columns if available
        feature_info = {}
        if hasattr(pred, 'feature_columns'):
            feature_info = {
                'n_features': len(pred.feature_columns),
                'feature_names': pred.feature_columns
            }
        
        info = {
            'model_loaded': True,
            'model_type': model_type,
            'num_parameters': num_parameters,
            'device': device,
            'performance_metrics': performance_metrics,
            'config': pred.config if hasattr(pred, 'config') else {},
            'metadata': metadata,
            'feature_info': feature_info
        }
        
        return jsonify(info), 200
    
    except FileNotFoundError as e:
        return jsonify({
            'model_loaded': False,
            'error': 'Model not found. Please train the model first.',
            'details': str(e)
        }), 503
    except Exception as e:
        logger.error(f"Error in model_info endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'model_loaded': False,
            'error': str(e)
        }), 503


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        pred = get_predictor()
        model_loaded = True
    except:
        model_loaded = False
    
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_loaded
    })


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ST-GNN Yield Prediction API")
    logger.info("=" * 60)
    logger.info("Starting server on http://0.0.0.0:9000")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=9000, debug=False)
