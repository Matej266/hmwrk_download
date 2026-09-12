import argparse
import dataclasses
from datetime import date

from config import CLASSES
from drive_client import DriveClient
from logger import write_log
from sync import sync
from upload import upload


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hmwrk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Download homework submissions")
    sync_parser.add_argument("--class", dest="class_key", choices=sorted(CLASSES), required=True)
    date_group = sync_parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--week", type=_parse_date, help="Monday date of a single week")
    date_group.add_argument("--from", dest="from_date", type=_parse_date)
    sync_parser.add_argument("--to", dest="to_date", type=_parse_date)

    upload_parser = subparsers.add_parser("upload", help="Upload corrected homework")
    upload_parser.add_argument("--class", dest="class_key", choices=sorted(CLASSES), required=True)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    class_config = CLASSES[args.class_key]
    drive = DriveClient.authenticated()

    if args.command == "sync":
        start = args.week if args.week else args.from_date
        end = args.week if args.week else args.to_date
        if end is None:
            raise SystemExit("--to is required when using --from")
        results = sync(drive, class_config, start, end)
    else:
        results = upload(drive, class_config)

    write_log([dataclasses.asdict(r) for r in results])


if __name__ == "__main__":
    main()
