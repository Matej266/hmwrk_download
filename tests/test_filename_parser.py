from datetime import date

import pytest

from filename_parser import InvalidFilename, corrected_filename, parse_filename


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
