from datetime import date

import pytest

from filename_parser import InvalidFilename, corrected_filename, parse_due_date, parse_filename


def test_parse_due_date_extracts_date_ignoring_rest_of_filename():
    assert parse_due_date("2026-03-02_Jon Smyth.pdf") == date(2026, 3, 2)


def test_parse_due_date_accepts_date_only_filename():
    assert parse_due_date("2026-03-02.pdf") == date(2026, 3, 2)


def test_parse_due_date_accepts_any_separator_after_the_date():
    assert parse_due_date("2026-03-02 Jon Smyth.pdf") == date(2026, 3, 2)
    assert parse_due_date("2026-03-02-Jon Smyth.pdf") == date(2026, 3, 2)
    assert parse_due_date("2026-03-02JonSmyth.pdf") == date(2026, 3, 2)


def test_parse_due_date_accepts_underscore_or_dot_separators():
    assert parse_due_date("2026_03_02_Jon Smyth.pdf") == date(2026, 3, 2)
    assert parse_due_date("2026.03.02.Jon Smyth.pdf") == date(2026, 3, 2)


def test_parse_due_date_accepts_non_zero_padded_month_and_day():
    assert parse_due_date("2026-3-2_Jon Smyth.pdf") == date(2026, 3, 2)
    assert parse_due_date("2026_9_4 Jon Smyth.pdf") == date(2026, 9, 4)


def test_parse_due_date_rejects_missing_date_prefix():
    with pytest.raises(InvalidFilename):
        parse_due_date("homework.pdf")


def test_parse_filename_extracts_date_and_full_name():
    due_date, full_name = parse_filename("2026-03-02_John Smith.pdf")
    assert due_date == date(2026, 3, 2)
    assert full_name == "John Smith"


def test_parse_filename_rejects_missing_date_prefix():
    with pytest.raises(InvalidFilename):
        parse_filename("John Smith Homework.pdf")


def test_parse_filename_rejects_invalid_date():
    with pytest.raises(InvalidFilename):
        parse_filename("2026-13-40_John Smith.pdf")


def test_corrected_filename_inserts_suffix_before_extension():
    assert (
        corrected_filename("2026-03-02_John Smith.pdf")
        == "2026-03-02_John Smith - corrected.pdf"
    )
