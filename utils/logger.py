import os
from datetime import datetime
from typing import List, Dict


class ReportLogger:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.failed_items: List[Dict] = []
        self.start_time = datetime.now()

    def add_failed(self, bucket: str, path: str, filename: str, reason: str):
        self.failed_items.append(
            {
                "bucket": bucket,
                "path": path,
                "filename": filename,
                "reason": reason,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    @property
    def has_failures(self) -> bool:
        return len(self.failed_items) > 0

    @property
    def failure_count(self) -> int:
        return len(self.failed_items)

    def generate_report(self) -> str:
        date_str = self.start_time.strftime("%Y%m%d_%H%M%S")
        # Same structure as FileOrganizer: <output_dir>/Result/<DDMMYYYY>/
        result_dir = os.path.join(
            self.output_dir, "Result", self.start_time.strftime("%d%m%Y")
        )
        os.makedirs(result_dir, exist_ok=True)

        report_path = os.path.join(result_dir, f"Report_log_{date_str}.txt")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("CloudFetch — Download Failure Report\n")
            f.write(f'Generated : {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write("=" * 60 + "\n\n")
            f.write(f"Total Failed : {len(self.failed_items)} file(s)\n\n")
            f.write("-" * 40 + "\n")

            for i, item in enumerate(self.failed_items, 1):
                f.write(f'\n[{i}] {item["filename"]}\n')
                f.write(f'    Bucket    : {item["bucket"]}\n')
                f.write(f'    Path      : {item["path"]}\n')
                f.write(f'    Reason    : {item["reason"]}\n')
                f.write(f'    Timestamp : {item["timestamp"]}\n')

        return report_path
