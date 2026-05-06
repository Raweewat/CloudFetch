import os
from datetime import datetime


class FileOrganizer:
    def __init__(self, base_output_dir: str):
        self.base_output_dir = base_output_dir
        self.date_str = datetime.now().strftime("%d%m%Y")
        # Structure: <output_dir>/Result/<DDMMYYYY>/
        self.result_dir = os.path.join(base_output_dir, "Result", self.date_str)

    @staticmethod
    def _path_to_folder_name(cloud_path: str) -> str:
        """Convert 'Data/EDW/05062026/' → 'Data_EDW_05062026'."""
        return cloud_path.strip("/").replace("/", "_")

    def get_local_path(self, cloud_path: str, filename: str) -> str:
        """
        Structure: <output_dir>/<DDMMYYYY>/<Path_As_Folder>/<filename>
        All files from the same cloud path go flat into one folder (no sub-hierarchy).
        """
        clean_path = cloud_path.strip("/")
        if clean_path:
            folder_name = self._path_to_folder_name(clean_path)
            local_dir = os.path.join(self.result_dir, folder_name)
        else:
            local_dir = self.result_dir
        os.makedirs(local_dir, exist_ok=True)
        return os.path.join(local_dir, filename)

    def create_simulated_file(self, local_path: str, filename: str):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(f"[SIMULATION] Simulated download of: {filename}\n")
            f.write(f"Download time: {datetime.now().isoformat()}\n")

    @property
    def result_base(self) -> str:
        return self.result_dir
