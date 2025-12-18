from google.cloud import storage
from urllib.parse import urlparse
import os 
from google.cloud import exceptions
import io

class GCStorage:
    def __init__(self, credentials_path: str | None = None):
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self.client = storage.Client()

    def upload_blob_from_memory(self, bucket_name, buffer, destination_blob_name, content_type="audio/mpeg"):
        """
        Uploads binary data (e.g., an MP3 file) from a memory buffer to GCS.

        Args:
            bucket_name (str): The target GCS bucket.
            buffer (io.BytesIO): The in-memory file-like object containing data.
            destination_blob_name (str): The name to store the file as in GCS.
            content_type (str): MIME type (default: 'audio/mpeg').
        """
        storage_client = self.client
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        buffer.seek(0)
        blob.upload_from_file(buffer, content_type=content_type)
        blob.make_public()
        return blob.public_url
    
    def upload_from_bytes(self, bucket_name: str, data: bytes, destination_blob_name: str, content_type: str = "image/png") -> str:
        """Upload dữ liệu bytes (ví dụ ảnh từ memory)."""
        storage_client = self.client
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(data, content_type=content_type)
        blob.make_public()
        # print(f"Uploaded bytes data -> {blob.public_url}")
        return blob.public_url
    
    def delete_blob(self, url: str):
        """
        Delete a blob from its public URL or gs:// path.
        Args:
            url: The public URL (https://storage.googleapis.com/...) or gs:// path.
        """
        try:
            # Parse bucket name and blob name from URL
            if url.startswith("gs://"):
                # Example: gs://my-bucket/tts/audio.mp3
                parts = url.replace("gs://", "").split("/", 1)
                bucket_name, blob_name = parts[0], parts[1]
            else:
                # Example: https://storage.googleapis.com/my-bucket/tts/audio.mp3
                parsed = urlparse(url)
                parts = parsed.path.lstrip("/").split("/", 1)
                bucket_name, blob_name = parts[0], parts[1]

            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()

        except exceptions.NotFound:
            print(f"File not found: gs://{bucket_name}/{blob_name}")

        except Exception as e:
            print(f"Delete error: {e}")
