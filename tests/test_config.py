from datetime import time

from config import CLASSES, LOCAL_BASE_PATH, LOG_DIR


def test_calc_deadline_is_thursday_1125_three_days_after_due_date():
    calc = CLASSES["calc"]
    assert calc.deadline_offset_days == 3
    assert calc.deadline_time == time(11, 25)


def test_precalc_deadline_is_tuesday_1320_one_day_after_due_date():
    precalc = CLASSES["precalc"]
    assert precalc.deadline_offset_days == 1
    assert precalc.deadline_time == time(13, 20)


def test_class_drive_names_and_folder_names():
    assert CLASSES["calc"].drive_name == "AP Calc"
    assert CLASSES["calc"].top_level_folder_name == "AP Calc - 2026/2027"
    assert CLASSES["precalc"].drive_name == "PreCalc"
    assert CLASSES["precalc"].top_level_folder_name == "PreCalc - 2026/2027"


def test_local_paths():
    assert LOCAL_BASE_PATH == "Hmwrks"
    assert LOG_DIR == "logs"
