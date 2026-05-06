import os
import time
import fnmatch
from typing import List


_MOCK_FILES = [
    "report_20240101.csv",
    "report_20240102.csv",
    "data_export_20240101.parquet",
    "data_export_20240102.parquet",
    "summary_20240101.xlsx",
    "log_20240101.txt",
    "archive_20240101.zip",
]


class SimulationClient:
    """Fake cloud client used when Simulation Mode is enabled."""

    def connect(self):
        time.sleep(0.2)

    def list_files(self, bucket: str, prefix: str) -> List[str]:
        time.sleep(0.15)
        return [f"{prefix.rstrip('/')}/{f}" if prefix else f for f in _MOCK_FILES]

    def file_exists(self, bucket: str, path: str) -> bool:
        filename = os.path.basename(path)
        return any(fnmatch.fnmatch(filename, m) for m in _MOCK_FILES) or filename in _MOCK_FILES

    def download(self, bucket: str, blob_name: str, local_path: str):
        time.sleep(0.25)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(f"[SIMULATION] bucket={bucket}  object={blob_name}\n")
