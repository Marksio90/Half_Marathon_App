import os
import boto3
import pandas as pd
from io import StringIO

class DataLoader:
    """
    Utility class for loading data from Digital Ocean Spaces.
    """
    
    def __init__(self):
        self.do_spaces_key = os.getenv('DO_SPACES_KEY')
        self.do_spaces_secret = os.getenv('DO_SPACES_SECRET')
        self.do_spaces_region = os.getenv('DO_SPACES_REGION', 'fra1')
        self.do_spaces_bucket = os.getenv('DO_SPACES_BUCKET', 'halfmarathon-ml')
        self.do_spaces_endpoint = f'https://{self.do_spaces_region}.digitaloceanspaces.com'
        
        self.s3_client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client for Digital Ocean Spaces"""
        return boto3.client(
            's3',
            region_name=self.do_spaces_region,
            endpoint_url=self.do_spaces_endpoint,
            aws_access_key_id=self.do_spaces_key,
            aws_secret_access_key=self.do_spaces_secret
        )
    
    def load_csv(self, filename: str, folder: str = 'data') -> pd.DataFrame:
        """
        Load CSV file from Digital Ocean Spaces.
        
        Args:
            filename: Name of the CSV file
            folder: Folder in the bucket (default: 'data')
            
        Returns:
            pandas DataFrame
        """
        try:
            key = f'{folder}/{filename}'
            obj = self.s3_client.get_object(Bucket=self.do_spaces_bucket, Key=key)
            csv_content = obj['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), sep=';')
            print(f"✅ Loaded {filename}: {len(df)} rows")
            return df
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return None
    
    def upload_file(self, local_path: str, spaces_key: str, folder: str = 'models'):
        """
        Upload file to Digital Ocean Spaces.
        
        Args:
            local_path: Path to local file
            spaces_key: Key (filename) in Spaces
            folder: Folder in the bucket (default: 'models')
        """
        try:
            full_key = f'{folder}/{spaces_key}'
            self.s3_client.upload_file(
                local_path,
                self.do_spaces_bucket,
                full_key,
                ExtraArgs={'ACL': 'private'}
            )
            print(f"✅ Uploaded {spaces_key} to {folder}/")
        except Exception as e:
            print(f"❌ Upload error: {e}")
    
    def list_files(self, folder: str = 'data') -> list:
        """
        List all files in a specific folder.
        
        Args:
            folder: Folder to list
            
        Returns:
            List of file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.do_spaces_bucket,
                Prefix=f'{folder}/'
            )
            
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                return files
            return []
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return []