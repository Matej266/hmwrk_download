import re
from datetime import date
from pathlib import Path

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")


class InvalidFilename(ValueError):
    pass


def parse_filename(filename: str) -> tuple[date, str]:
    stem = Path(filename).stem
    match = FILENAME_RE.match(stem)
    if not match:
        raise InvalidFilename(
            f"filename does not match '<date>_<full name>' pattern: {filename!r}"
        )
    date_str, full_name = match.groups()
    try:
        due_date = date.fromisoformat(date_str)
    except ValueError as exc:
        raise InvalidFilename(f"invalid date in filename: {filename!r}") from exc
    return due_date, full_name


def corrected_filename(filename: str) -> str:
    path = Path(filename)
    return f"{path.stem} - corrected{path.suffix}"
