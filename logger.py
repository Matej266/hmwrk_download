import csv
from datetime import datetime
from pathlib import Path
from typing import Sequence


def write_log(rows: Sequence[dict], log_dir: str = "logs") -> Path:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(log_dir) / f"run_{timestamp}.csv"

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(log_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _print_summary(rows)
    return log_path


def _print_summary(rows: Sequence[dict]) -> None:
    if not rows:
        print("No actions taken.")
        return
    for row in rows:
        print(" | ".join(f"{key}={value}" for key, value in row.items()))
