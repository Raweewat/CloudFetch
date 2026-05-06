import os
from typing import List


class AzureClient:
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self._service = None

    def connect(self):
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise RuntimeError(
                "azure-storage-blob is not installed.\n"
                "Please run:  pip install azure-storage-blob"
            )

        if self.credentials.get("connection_string"):
            self._service = BlobServiceClient.from_connection_string(
                self.credentials["connection_string"]
            )
        else:
            account_url = (
                f"https://{self.credentials['account_name']}.blob.core.windows.net"
            )
            self._service = BlobServiceClient(
                account_url=account_url,
                credential=self.credentials["account_key"],
            )

    def list_files(self, container: str, prefix: str) -> List[str]:
        cc = self._service.get_container_client(container)
        return [b.name for b in cc.list_blobs(name_starts_with=prefix or None)]

    def file_exists(self, container: str, blob_name: str) -> bool:
        bc = self._service.get_blob_client(container=container, blob=blob_name)
        return bc.exists()

    def download(self, container: str, blob_name: str, local_path: str):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        bc = self._service.get_blob_client(container=container, blob=blob_name)
        with open(local_path, "wb") as fh:
            fh.write(bc.download_blob().readall())
