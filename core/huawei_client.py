import os
from typing import List


class HuaweiClient:
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self._obs = None

    def connect(self):
        try:
            from obs import ObsClient
        except ImportError:
            raise RuntimeError(
                "esdk-obs-python is not installed.\n"
                "Please run:  pip install esdk-obs-python"
            )

        self._obs = ObsClient(
            access_key_id=self.credentials["access_key"],
            secret_access_key=self.credentials["secret_key"],
            server=self.credentials["endpoint"],
        )

    def list_files(self, bucket: str, prefix: str) -> List[str]:
        resp = self._obs.listObjects(bucket, prefix=prefix or "", max_keys=1000)
        if resp.status >= 300:
            raise RuntimeError(f"listObjects failed: {resp.errorMessage}")
        contents = resp.body.contents or []
        return [obj.key for obj in contents]

    def file_exists(self, bucket: str, object_key: str) -> bool:
        resp = self._obs.getObjectMetadata(bucket, object_key)
        return resp.status < 300

    def download(self, bucket: str, object_key: str, local_path: str):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        resp = self._obs.getObject(bucket, object_key, downloadPath=local_path)
        if resp.status >= 300:
            raise RuntimeError(f"Download failed: {resp.errorMessage}")
