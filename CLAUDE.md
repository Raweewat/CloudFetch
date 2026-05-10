# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

No test suite or linter is configured.

## Architecture

CloudFetch is a Tkinter desktop app that downloads files from Azure Blob Storage or Huawei OBS, with a Simulation Mode for testing without real cloud credentials.

### Data flow

```
MainWindow (_get_config) → dict config → DownloadManager.run_in_thread()
                                                ↓ (background thread)
                                         _get_client() → AzureClient | HuaweiClient | SimulationClient
                                                ↓
                                         FileOrganizer → local paths
                                         ReportLogger  → failure log
                                                ↓ (Queue)
                                         MainWindow._process_queues() → UI update (every 80 ms via root.after)
```

### Cloud client interface

All three clients (`AzureClient`, `HuaweiClient`, `SimulationClient`) share the same duck-typed interface:
- `connect()` — establish connection
- `list_files(bucket, prefix) → List[str]` — list blob keys
- `file_exists(bucket, key) → bool` — check single file
- `download(bucket, key, local_path)` — download to disk

To add a new cloud provider, implement these four methods and register it in `DownloadManager._get_client()`.

### GUI ↔ background thread communication

`DownloadManager` never touches Tkinter directly. It writes to two `queue.Queue` objects passed as callbacks:
- `log_callback(msg, level)` → `_log_q`
- `progress_callback(pct, status)` → `_prog_q`
- `done_callback(result_dict)` → sends sentinel `("__DONE__", result)` to `_log_q`

`MainWindow._process_queues()` drains both queues every 80 ms.

### Variable resolution

User-defined variables (name → value pairs from the Variables section) are resolved in `DownloadManager._resolve()` by simple `str.replace("{key}", value)` substitution. Resolution is applied to `bucket`, `path`, and `filename` fields of every task before any cloud API call.

### Output directory structure

```
<output_dir>/Result/<DDMMYYYY>/<Cloud_Path_As_Folder>/<filename>
```

`FileOrganizer._path_to_folder_name()` converts `data/reports/2024/` → `data_reports_2024` (slashes → underscores). `ReportLogger` writes `Report_log_<timestamp>.txt` into the same `Result/<DDMMYYYY>/` directory only when at least one file fails.

### Simulation Mode

When the "Simulation Mode" checkbox is on, `_get_client()` returns `SimulationClient` instead of a real cloud client. `SimulationClient` returns a fixed list of mock filenames (`_MOCK_FILES`) and writes `[SIMULATION]` placeholder files to disk. The rest of the download pipeline runs identically.
