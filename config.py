from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ClassConfig:
    key: str
    drive_name: str
    top_level_folder_name: str
    deadline_offset_days: int
    deadline_time: time


CLASSES: dict[str, ClassConfig] = {
    "calc": ClassConfig(
        key="calc",
        drive_name="AP Calc",
        top_level_folder_name="AP Calc - 2026/2027",
        deadline_offset_days=3,
        deadline_time=time(11, 25),
    ),
    "precalc": ClassConfig(
        key="precalc",
        drive_name="PreCalc",
        top_level_folder_name="PreCalc - 2026/2027",
        deadline_offset_days=1,
        deadline_time=time(13, 20),
    ),
}

LOCAL_BASE_PATH = "Hmwrks"
LOG_DIR = "logs"
