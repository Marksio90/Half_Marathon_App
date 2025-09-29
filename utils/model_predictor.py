import os
import joblib
import boto3
import pandas as pd
from io import BytesIO
from pathlib import Path

class HalfMarathonPredictor:
    """
    Half Marathon time predictor using trained XGBoost model.
    Loads model from Digital Ocean Spaces or local cache.
    """
    
    def __init__(self):
        self.model = None
        self.model_metadata = None
        self.gender_encoder = None
        self.cache_dir = Path("model_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Digital Ocean Spaces configuration
        self.do_spaces_key = os.getenv('DO_SPACES_KEY')
        self.do_spaces_secret = os.getenv('DO_SPACES_SECRET')
        self.do_spaces_region = os.getenv('DO_SPACES_REGION', 'fra1')
        self.do_spaces_bucket = os.getenv('DO_SPACES_BUCKET', 'halfmarathon-ml')
        self.do_spaces_endpoint = f'https://{self.do_spaces_region}.digitaloceanspaces.com'
        
        self.load_model()
    
    def _get_s3_client(self):
        """Initialize S3 client for Digital Ocean Spaces"""
        return boto3.client(
            's3',
            region_name=self.do_spaces_region,
            endpoint_url=self.do_spaces_endpoint,
            aws_access_key_id=self.do_spaces_key,
            aws_secret_access_key=self.do_spaces_secret
        )
    
    def _download_from_spaces(self, spaces_key: str, local_path: Path) -> bool:
        """Download file from Digital Ocean Spaces"""
        try:
            s3_client = self._get_s3_client()
            with open(local_path, 'wb') as f:
                s3_client.download_fileobj(
                    self.do_spaces_bucket,
                    f'models/{spaces_key}',
                    f
                )
            print(f"✅ Downloaded {spaces_key} from Spaces")
            return True
        except Exception as e:
            print(f"⚠️ Could not download {spaces_key}: {e}")
            return False
    
    def load_model(self):
        """Load model and metadata from Spaces or local cache"""
        model_files = {
            'model': 'halfmarathon_model_latest.pkl',
            'metadata': 'model_metadata_latest.pkl',
            'encoder': 'gender_encoder.pkl'
        }
        
        # Try to load from cache first, then from Spaces
        for key, filename in model_files.items():
            local_path = self.cache_dir / filename
            
            # If not in cache, try to download from Spaces
            if not local_path.exists():
                print(f"📥 Downloading {filename} from Digital Ocean Spaces...")
                self._download_from_spaces(filename, local_path)
            
            # Load the file
            if local_path.exists():
                try:
                    data = joblib.load(local_path)
                    if key == 'model':
                        self.model = data
                        print(f"✅ Model loaded successfully")
                    elif key == 'metadata':
                        self.model_metadata = data
                        print(f"✅ Metadata loaded")
                    elif key == 'encoder':
                        self.gender_encoder = data
                        print(f"✅ Gender encoder loaded")
                except Exception as e:
                    print(f"❌ Error loading {filename}: {e}")
            else:
                print(f"⚠️ {filename} not found in cache or Spaces")
        
        if self.model is None:
            raise Exception("Could not load model. Please ensure model files are in Digital Ocean Spaces or local cache.")
    
    def predict(self, user_data: dict) -> dict:
        """
        Make prediction based on user data.
        
        Args:
            user_data: Dictionary with keys: gender, age, time_5km_seconds
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Validate input
            if not all(key in user_data for key in ['gender', 'age', 'time_5km_seconds']):
                return {
                    'success': False,
                    'error': 'Missing required fields'
                }
            
            # Encode gender
            gender_encoded = 1 if user_data['gender'].lower() == 'male' else 0
            
            # Calculate 5km pace (minutes per km)
            pace_5km = (user_data['time_5km_seconds'] / 5) / 60
            
            # Prepare feature vector
            features = pd.DataFrame({
                'Płeć_encoded': [gender_encoded],
                'Wiek': [user_data['age']],
                '5 km Czas_seconds': [user_data['time_5km_seconds']],
                '5 km Tempo': [pace_5km]
            })
            
            # Add optional features if model expects them
            if self.model_metadata:
                model_features = self.model_metadata.get('features', [])
                for feat in model_features:
                    if feat not in features.columns:
                        features[feat] = 0  # Default value for missing features
                
                # Ensure correct column order
                features = features[model_features]
            
            # Make prediction
            prediction_seconds = self.model.predict(features)[0]
            
            # Format time as HH:MM:SS
            hours = int(prediction_seconds // 3600)
            minutes = int((prediction_seconds % 3600) // 60)
            seconds = int(prediction_seconds % 60)
            formatted_time = f"{hours}:{minutes:02d}:{seconds:02d}"
            
            return {
                'success': True,
                'prediction_seconds': float(prediction_seconds),
                'formatted_time': formatted_time,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'average_pace_min_per_km': prediction_seconds / 21.0975 / 60,
                'model_version': self.model_metadata.get('version', 'unknown') if self.model_metadata else 'unknown'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if self.model_metadata:
            return {
                'version': self.model_metadata.get('version', 'unknown'),
                'model_type': self.model_metadata.get('model_type', 'unknown'),
                'features': self.model_metadata.get('features', []),
                'train_samples': self.model_metadata.get('train_samples', 0),
                'test_metrics': self.model_metadata.get('metrics', {}).get('test', {})
            }
        return {'error': 'No metadata available'}