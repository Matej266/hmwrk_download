from datetime import date, datetime, timedelta

from config import ClassConfig


def compute_deadline(due_date: date, class_config: ClassConfig) -> datetime:
    deadline_date = due_date + timedelta(days=class_config.deadline_offset_days)
    naive = datetime.combine(deadline_date, class_config.deadline_time)
    return naive.astimezone()


def classify(due_date: date, created_at: datetime, class_config: ClassConfig) -> str:
    deadline = compute_deadline(due_date, class_config)
    if created_at >= deadline:
        return "late"
    return due_date.isoformat()
