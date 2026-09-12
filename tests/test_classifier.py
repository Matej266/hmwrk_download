from datetime import date, time, timedelta

from classifier import classify, compute_deadline
from config import CLASSES


def test_compute_deadline_calc_is_three_days_after_due_date_at_1125():
    due_date = date(2026, 3, 2)  # Monday
    deadline = compute_deadline(due_date, CLASSES["calc"])
    assert deadline.date() == date(2026, 3, 5)  # Thursday
    assert deadline.time() == time(11, 25)


def test_compute_deadline_precalc_is_one_day_after_due_date_at_1320():
    due_date = date(2026, 3, 2)  # Monday
    deadline = compute_deadline(due_date, CLASSES["precalc"])
    assert deadline.date() == date(2026, 3, 3)  # Tuesday
    assert deadline.time() == time(13, 20)


def test_classify_on_time_when_before_deadline():
    due_date = date(2026, 3, 2)
    deadline = compute_deadline(due_date, CLASSES["calc"])
    created_at = deadline - timedelta(minutes=1)
    assert classify(due_date, created_at, CLASSES["calc"]) == "2026-03-02"


def test_classify_late_when_at_or_after_deadline():
    due_date = date(2026, 3, 2)
    deadline = compute_deadline(due_date, CLASSES["calc"])
    assert classify(due_date, deadline, CLASSES["calc"]) == "late"
