from datetime import date

from config import CLASSES
from sync import sync
from tests.fakes import FakeDriveClient


def build_fake_drive():
    return FakeDriveClient(
        folders_by_parent={
            None: [{"id": "class1", "name": "AP Calc - 2026/2027"}],
            "class1": [{"id": "student1", "name": "AP Calc - John Smith"}],
            "student1": [{"id": "hw1", "name": "AP Calc Homeworks - John Smith"}],
        },
        files_by_folder={
            "hw1": [
                {
                    "id": "f1",
                    "name": "2026-03-02_John Smith.pdf",
                    "createdTime": "2026-03-02T15:00:00.000Z",
                },
                {
                    "id": "f2",
                    "name": "2026-03-02_John Smith.pdf",
                    "createdTime": "2026-03-06T15:00:00.000Z",
                },
            ]
        },
    )


def test_sync_downloads_on_time_and_late_copies_into_correct_buckets(tmp_path):
    drive = build_fake_drive()

    results = sync(drive, CLASSES["calc"], date(2026, 3, 2), date(2026, 3, 2), base_path=tmp_path)

    buckets = {r.bucket for r in results}
    assert buckets == {"2026-03-02", "late"}
    assert all(r.action == "downloaded" for r in results)
    assert (tmp_path / "calc" / "2026-03-02" / "submitted" / "2026-03-02_John Smith.pdf").exists()
    assert (tmp_path / "calc" / "late" / "submitted" / "2026-03-02_John Smith.pdf").exists()


def test_sync_skips_file_already_downloaded(tmp_path):
    drive = build_fake_drive()
    target = tmp_path / "calc" / "2026-03-02" / "submitted" / "2026-03-02_John Smith.pdf"
    target.parent.mkdir(parents=True)
    target.write_text("already here")

    results = sync(drive, CLASSES["calc"], date(2026, 3, 2), date(2026, 3, 2), base_path=tmp_path)

    on_time_result = next(r for r in results if r.bucket == "2026-03-02")
    assert on_time_result.action == "skipped"
    assert target.read_text() == "already here"


def test_sync_ignores_files_outside_date_range(tmp_path):
    drive = build_fake_drive()

    results = sync(drive, CLASSES["calc"], date(2026, 4, 1), date(2026, 4, 30), base_path=tmp_path)

    assert results == []


def test_sync_renames_local_file_using_drive_folder_name_not_uploaded_filename(tmp_path):
    drive = FakeDriveClient(
        folders_by_parent={
            None: [{"id": "class1", "name": "AP Calc - 2026/2027"}],
            "class1": [{"id": "student1", "name": "AP Calc - John Smith"}],
            "student1": [{"id": "hw1", "name": "AP Calc Homeworks - John Smith"}],
        },
        files_by_folder={
            "hw1": [
                {
                    "id": "f1",
                    "name": "2026-03-02_Jon Smyth (phonetic spelling).pdf",
                    "createdTime": "2026-03-02T15:00:00.000Z",
                }
            ]
        },
    )

    results = sync(drive, CLASSES["calc"], date(2026, 3, 2), date(2026, 3, 2), base_path=tmp_path)

    assert results[0].filename == "2026-03-02_John Smith.pdf"
    assert (tmp_path / "calc" / "2026-03-02" / "submitted" / "2026-03-02_John Smith.pdf").exists()
