import re
from datetime import date
from pathlib import Path

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")
DATE_PREFIX_RE = re.compile(r"^(\d{4})[-_.](\d{1,2})[-_.](\d{1,2})")


class InvalidFilename(ValueError):
    pass


def parse_due_date(filename: str) -> date:
    """Extracts just the leading date prefix, ignoring whatever separator
    (or none) and text follows it (their own name, spelled however). The
    date's year-month-day parts may be separated by '-', '_', or '.', and
    month/day may be zero-padded or not (e.g. '2026-3-2', '2026_03_02',
    '2026.3.2')."""
    stem = Path(filename).stem
    match = DATE_PREFIX_RE.match(stem)
    if not match:
        raise InvalidFilename(
            f"filename does not start with a '<date>' prefix: {filename!r}"
        )
    year, month, day = (int(group) for group in match.groups())
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise InvalidFilename(f"invalid date in filename: {filename!r}") from exc


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
