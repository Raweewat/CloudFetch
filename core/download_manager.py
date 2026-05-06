import os
import fnmatch
import threading
from typing import Callable, Dict, List, Optional

from core.azure_client import AzureClient
from core.huawei_client import HuaweiClient
from core.simulation_client import SimulationClient
from core.file_organizer import FileOrganizer
from utils.logger import ReportLogger


class DownloadManager:
    def __init__(
        self,
        config: Dict,
        log_callback: Callable,
        progress_callback: Callable,
        done_callback: Callable,
    ):
        self.cloud_type: str = config["cloud_type"]
        self.credentials: Dict = config["credentials"]
        self.variables: Dict[str, str] = config["variables"]
        self.tasks: List[Dict] = config["tasks"]
        self.output_dir: str = config["output_dir"]
        self.simulation: bool = config.get("simulation", False)

        self._log = log_callback
        self._progress = progress_callback
        self._done = done_callback

        self._stop_event = threading.Event()
        self.is_running = False

    # ------------------------------------------------------------------
    def _resolve(self, text: str) -> str:
        for k, v in self.variables.items():
            text = text.replace(f"{{{k}}}", v)
        return text

    def _get_client(self):
        if self.simulation:
            return SimulationClient()
        if self.cloud_type == "azure":
            return AzureClient(self.credentials)
        return HuaweiClient(self.credentials)

    def _files_to_download(self, client, bucket: str, path: str, pattern: str):
        has_wildcard = "*" in pattern or "?" in pattern
        no_pattern = not pattern.strip()

        if has_wildcard or no_pattern:
            all_blobs = client.list_files(bucket, path)
            if no_pattern:
                return [(b, os.path.basename(b)) for b in all_blobs]
            return [
                (b, os.path.basename(b))
                for b in all_blobs
                if fnmatch.fnmatch(os.path.basename(b), pattern)
            ]
        else:
            sep = "/" if not path.endswith("/") else ""
            full_key = f"{path}{sep}{pattern}" if path else pattern
            exists = client.file_exists(bucket, full_key)
            return [(full_key, pattern)] if exists else []

    # ------------------------------------------------------------------
    def run(self):
        self.is_running = True
        self._stop_event.clear()
        organizer = FileOrganizer(self.output_dir)
        logger = ReportLogger(self.output_dir)
        total_tasks = len(self.tasks)
        total_dl = 0
        total_fail = 0
        failed_paths: List[str] = []

        try:
            client = self._get_client()
            self._log("Connecting to cloud storage…", "info")
            client.connect()
            self._log("Connected successfully.", "success")
        except Exception as exc:
            self._log(f"Connection failed: {exc}", "error")
            self._done({"total_dl": 0, "total_fail": 0, "failed_paths": [], "report_path": None})
            self.is_running = False
            return

        for idx, task in enumerate(self.tasks):
            if self._stop_event.is_set():
                self._log("Download stopped by user.", "warning")
                break

            bucket = self._resolve(task["bucket"].strip())
            path = self._resolve(task["path"].strip())
            pattern = self._resolve(task["filename"].strip())

            self._log(
                f"\n── Task {idx + 1}/{total_tasks} ──  Bucket: {bucket}  |  Path: {path}  |  Pattern: {pattern or '(all)'}",
                "info",
            )

            base_progress = (idx / total_tasks) * 100

            try:
                files = self._files_to_download(client, bucket, path, pattern)
            except Exception as exc:
                self._log(f"  Error listing files: {exc}", "error")
                logger.add_failed(bucket, path, pattern or "*", str(exc))
                failed_paths.append(path)
                total_fail += 1
                continue

            if not files:
                self._log("  No files matched. Skipping.", "warning")
                logger.add_failed(bucket, path, pattern or "*", "No files matched pattern")
                failed_paths.append(path)
                total_fail += 1
                continue

            self._log(f"  Found {len(files)} file(s).", "success")

            for f_idx, (blob_key, filename) in enumerate(files):
                if self._stop_event.is_set():
                    break

                local_path = organizer.get_local_path(path, filename)
                self._log(f"  ↓ {filename}", "info")

                try:
                    if self.simulation:
                        organizer.create_simulated_file(local_path, filename)
                    else:
                        client.download(bucket, blob_key, local_path)
                    self._log(f"    ✓ Saved → {local_path}", "success")
                    total_dl += 1
                except Exception as exc:
                    self._log(f"    ✗ Failed: {exc}", "error")
                    logger.add_failed(bucket, path, filename, str(exc))
                    total_fail += 1

                pct = base_progress + ((f_idx + 1) / len(files)) * (100 / total_tasks)
                self._progress(min(pct, 99), f"Downloading {filename}")

        report_path: Optional[str] = None
        if logger.has_failures:
            report_path = logger.generate_report()
            self._log(f"\nReport saved → {report_path}", "warning")

        self._progress(100, "Complete")
        self.is_running = False
        self._done(
            {
                "total_dl": total_dl,
                "total_fail": total_fail,
                "failed_paths": list(set(failed_paths)),
                "report_path": report_path,
                "result_dir": organizer.result_base,
            }
        )

    def stop(self):
        self._stop_event.set()

    def run_in_thread(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
