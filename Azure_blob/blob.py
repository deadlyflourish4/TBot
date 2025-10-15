from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from typing import List, Optional
from os import getenv 
blob_service_client = BlobServiceClient.from_connection_string(getenv("BLOB_CONNECTION_STRING"))

class AzureBlobUploader:
    def __init__(self, connection_string: str, container_name: str):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.__ensure_container_exists()

    def __ensure_container_exists(self):
        try:
            self.container_client.create_container()
        except Exception:
            pass  # Container already exists

    def upload_file(self, data: bytes, blob_name: str, content_type: str= "application/octet-stream") -> str:
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
        return blob_client.url