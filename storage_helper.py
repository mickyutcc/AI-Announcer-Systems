import os
import logging

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None

from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self, bucket: str, region: str = "us-east-1", aws_access_key_id=None, aws_secret_access_key=None):
        if boto3 is None:
            raise RuntimeError("boto3 required for S3Storage")
        self.bucket = bucket
        self.s3_client = boto3.client(
            "s3",
            region_name=region or "us-east-1",
            aws_access_key_id=aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
        )

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        # Note: parameter name is 'data' to match your code
        try:
            self.s3_client.put_object(
                Bucket=self.bucket, 
                Key=key, 
                Body=data, 
                ContentType=content_type
            )
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def get_signed_url(self, path_or_key: str, expires: int = 3600) -> str:
        try:
            if path_or_key.startswith("s3://"):
                # Parse s3://bucket/key
                parsed = urlparse(path_or_key)
                bucket = parsed.netloc
                key = parsed.path.lstrip('/')
            else:
                bucket = self.bucket
                key = path_or_key
            
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return ""

class LocalStorage:
    def __init__(self, base_path: str):
        self.base_path = base_path
        
    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        try:
            # Ensure key doesn't start with / to avoid absolute path confusion
            clean_key = key.lstrip('/')
            dest = os.path.join(self.base_path, clean_key)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            return dest
        except Exception as e:
            logger.error(f"Failed to save local file: {e}")
            raise

    def get_signed_url(self, path: str, expires: int = 3600) -> str:
        # In dev return file:// path for admin preview
        # If path is already absolute, use it directly
        if os.path.isabs(path):
            return f"file://{path}"
        
        # Otherwise join with base_path if not already part of it
        # This logic depends on what 'path' contains. 
        # If 'path' is the full path returned by upload_bytes, it's already absolute/full.
        # If 'path' is just the key, we need to join.
        
        full_path = path
        if not os.path.exists(full_path):
             full_path = os.path.join(self.base_path, path.lstrip('/'))
             
        return f"file://{os.path.abspath(full_path)}"
