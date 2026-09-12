from datetime import date

import pytest

from main import build_parser


def test_sync_week_flag_parses_to_date():
    args = build_parser().parse_args(["sync", "--class", "calc", "--week", "2026-03-02"])
    assert args.command == "sync"
    assert args.class_key == "calc"
    assert args.week == date(2026, 3, 2)


def test_sync_from_to_flags_parse():
    args = build_parser().parse_args(
        ["sync", "--class", "precalc", "--from", "2026-03-02", "--to", "2026-03-30"]
    )
    assert args.from_date == date(2026, 3, 2)
    assert args.to_date == date(2026, 3, 30)


def test_sync_week_and_from_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["sync", "--class", "calc", "--week", "2026-03-02", "--from", "2026-03-02"]
        )


def test_upload_requires_class_flag():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["upload"])


def test_upload_parses_class_flag():
    args = build_parser().parse_args(["upload", "--class", "calc"])
    assert args.command == "upload"
    assert args.class_key == "calc"
