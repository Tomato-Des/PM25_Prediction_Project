import numpy as np
import tensorflow as tf
from datetime import datetime, timedelta
from typing import List, Dict
from backend.config import Config
from backend.database import Database

class PredictionService:
    def __init__(self, db: Database = None):
        self.model_path = Config.MODEL_PATH
        self.sequence_length = Config.SEQUENCE_LENGTH
        self.prediction_hours = Config.PREDICTION_HOURS
        self.db = db or Database()
        self.model = None
        self.scaler_params = None
        self._load_model()
    
    def _load_model(self):
        """Load trained Transformer model"""
        try:
            print(f"📦 Loading model from {self.model_path}...")
            self.model = tf.keras.models.load_model(self.model_path)
            print("✅ Model loaded successfully")
            print(f"   Input shape: {self.model.input_shape}")
            print(f"   Output shape: {self.model.output_shape}")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            self.model = None
    
    def _normalize_data(self, data: np.ndarray) -> np.ndarray:
        """
        Normalize data using min-max scaling [0, 1].
        Same method as training.
        """
        min_val = np.min(data)
        max_val = np.max(data)
        
        if max_val == min_val:
            return np.zeros_like(data)
        
        normalized = (data - min_val) / (max_val - min_val)
        
        # Store scaler params for inverse transform
        self.scaler_params = {'min': min_val, 'max': max_val}
        
        return normalized
    
    def _denormalize_data(self, data: np.ndarray) -> np.ndarray:
        """Inverse transform normalized predictions"""
        if self.scaler_params is None:
            print("[WARN] No scaler params, returning raw predictions")
            return data
        
        min_val = self.scaler_params['min']
        max_val = self.scaler_params['max']
        
        return data * (max_val - min_val) + min_val
    
    def predict_24h(self) -> List[Dict]:
        """
        Generate 24-hour predictions based on last 720 hours of data.
        Returns list of {target_datetime, predicted_pm25} dicts.
        """
        if self.model is None:
            print("[ERROR] Model not loaded, cannot make predictions")
            return []
        
        print("\n" + "="*60)
        print(f"🔮 PREDICTION START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Get last 720 hours from database
        data = self.db.get_last_n_hours(self.sequence_length)
        
        if len(data) < self.sequence_length:
            print(f"[ERROR] Not enough data: {len(data)}/{self.sequence_length} hours")
            return []
        
        # Extract PM2.5 values
        pm25_values = np.array([record['pm25'] for record in data])
        
        # Normalize
        pm25_normalized = self._normalize_data(pm25_values)
        
        # Reshape for model input: (1, 720, 1)
        X = pm25_normalized.reshape(1, self.sequence_length, 1)
        
        # Predict
        print(f"🧠 Running model inference...")
        predictions_normalized = self.model.predict(X, verbose=0)  # Shape: (1, 24)
        
        # Denormalize
        predictions = self._denormalize_data(predictions_normalized[0])
        
        # Generate target datetimes (next 24 hours)
        last_datetime_str = data[-1]['datetime']
        last_datetime = datetime.strptime(last_datetime_str, '%Y-%m-%d %H:%M')
        
        results = []
        for i in range(self.prediction_hours):
            target_datetime = last_datetime + timedelta(hours=i+1)
            results.append({
                'target_datetime': target_datetime.strftime('%Y-%m-%d %H:%M'),
                'predicted_pm25': round(float(predictions[i]), 2)
            })
        
        print(f"✅ Generated {len(results)} predictions")
        print(f"   Next hour: {results[0]['target_datetime']} : {results[0]['predicted_pm25']} μg/m³")
        print(f"   Hour +24:  {results[-1]['target_datetime']} : {results[-1]['predicted_pm25']} μg/m³")
        
        # Store predictions in database
        prediction_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.db.insert_predictions(prediction_time, results)
        
        print("="*60)
        print(f"✅ PREDICTION END")
        print("="*60 + "\n")
        
        return results