# common/utils/storage_service.py
"""

import boto3
import os
import uuid
import mimetypes
import subprocess
import base64
import hashlib
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("OBJECT_STORAGE_BUCKET")

print("🧪 STORAGE INIT")
print("🧪 BUCKET:", BUCKET)
print("🧪 ENDPOINT:", os.getenv("OBJECT_STORAGE_ENDPOINT"))

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("OBJECT_STORAGE_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("OBJECT_STORAGE_SECRET_KEY"),
    endpoint_url=os.getenv("OBJECT_STORAGE_ENDPOINT"),
    region_name="us-east-1",  # ignored by PureStore
    config=Config(
        signature_version="s3v4",
        retries={"max_attempts": 1},
        s3={
            "addressing_style": "path",
            "payload_signing_enabled": False,  # 🔥 critical
        },
    ),
)

print("🧪 S3 ENDPOINT IN USE:", s3.meta.endpoint_url)

def upload_file(file_path: str, folder: str) -> str:
    if not BUCKET:
        raise RuntimeError("OBJECT_STORAGE_BUCKET is not set")

    ext = file_path.rsplit(".", 1)[-1]
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    s3_uri = f"s3://{BUCKET}/{key}"

    # Use s3cmd (PureStore-compatible)
    result = subprocess.run(
        ["s3cmd", "put", "--no-progress", file_path, s3_uri],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"s3cmd upload failed:\n{result.stderr}"
        )

    return key


def generate_presigned_url(key, expiry=300):
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expiry,
    )


def delete_file(key):
    s3.delete_object(Bucket=BUCKET, Key=key)
"""

# common/utils/storage_service.py

import boto3
import os
import uuid
import urllib3
from botocore.client import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable SSL warnings (PureStore requirement)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Environment variables
BUCKET = os.getenv("OBJECT_STORAGE_BUCKET")
ENDPOINT = os.getenv("OBJECT_STORAGE_ENDPOINT")
ACCESS_KEY = os.getenv("OBJECT_STORAGE_ACCESS_KEY")
SECRET_KEY = os.getenv("OBJECT_STORAGE_SECRET_KEY")

print("🧪 STORAGE INIT")
print("🧪 BUCKET:", BUCKET)
print("🧪 ENDPOINT:", ENDPOINT)


def get_s3_client():
    """
    Create S3 client configured specifically for PureStore.
    These settings are mandatory for PureStore compatibility.
    """
    if not ENDPOINT or not ACCESS_KEY or not SECRET_KEY:
        raise RuntimeError("S3 environment variables are not properly configured")

    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="in-west2",  # MUST match PureStore region
        verify=False,  # Required because PureStore SSL cert is not trusted by default
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path"  # Required for PureStore
            },
            request_checksum_calculation="when_required"  # Prevent checksum header errors
        ),
    )


# Create reusable client
s3 = get_s3_client()


def upload_file(file_path: str, folder: str) -> str:
    """
    Upload file to PureStore S3.
    Returns the generated object key.
    """
    if not BUCKET:
        raise RuntimeError("OBJECT_STORAGE_BUCKET is not set")

    if not os.path.exists(file_path):
        raise RuntimeError(f"File does not exist: {file_path}")

    # Generate unique file key
    ext = file_path.rsplit(".", 1)[-1]
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    # Upload file
    s3.upload_file(file_path, BUCKET, key)

    return key


def generate_presigned_url(key: str, expiry: int = 300) -> str:
    """
    Generate presigned URL for secure file access.
    """
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": key
        },
        ExpiresIn=expiry,
    )


def delete_file(key: str):
    """
    Delete file from PureStore S3.
    """
    s3.delete_object(Bucket=BUCKET, Key=key)
    
    
    
    
#New
def upload_file_object(file_obj, filename: str, folder: str) -> str:
    """
    Direct upload file object to PureStore S3.
    No temp file required.
    """

    if not BUCKET:
        raise RuntimeError(
            "OBJECT_STORAGE_BUCKET is not set"
        )

    # -------------------------------------------------
    # FILE EXTENSION
    # -------------------------------------------------

    ext = filename.rsplit(".", 1)[-1]

    # -------------------------------------------------
    # GENERATE UNIQUE KEY
    # -------------------------------------------------

    key = f"{folder}/{uuid.uuid4()}.{ext}"

    # -------------------------------------------------
    # RESET POINTER
    # -------------------------------------------------

    file_obj.seek(0)

    # -------------------------------------------------
    # DIRECT STREAM UPLOAD
    # -------------------------------------------------

    s3.upload_fileobj(
        file_obj,
        BUCKET,
        key
    )

    return key
