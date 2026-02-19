import os
import logging
from config import (
    STORAGE_TYPE, ASSETS_DIR, S3_BUCKET, S3_REGION,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, LOCAL_STORAGE_PATH
)
from storage_helper import LocalStorage, S3Storage

logger = logging.getLogger(__name__)

def get_storage():
    if STORAGE_TYPE == "s3":
        if not S3_BUCKET:
            logger.warning("STORAGE_TYPE is s3 but S3_BUCKET is not set. Falling back to local.")
            return LocalStorage(base_path=LOCAL_STORAGE_PATH)
        try:
            return S3Storage(
                bucket=S3_BUCKET,
                region=S3_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3Storage: {e}. Falling back to local.")
            return LocalStorage(base_path=LOCAL_STORAGE_PATH)
    else:
        return LocalStorage(base_path=LOCAL_STORAGE_PATH)

# Singleton instance
storage = get_storage()
