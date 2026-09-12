from config import CLASSES
from tests.fakes import FakeDriveClient
from upload import upload


def build_fake_drive_with_corrected_folder(existing_files=None):
    return FakeDriveClient(
        folders_by_parent={
            None: [{"id": "class1", "name": "AP Calc - 2026/2027"}],
            "class1": [{"id": "student1", "name": "AP Calc - John Smith"}],
            "student1": [
                {"id": "corrected1", "name": "AP Calc Homeworks - John Smith - corrected"}
            ],
        },
        files_by_folder={"corrected1": existing_files or []},
    )


def test_upload_uploads_new_corrected_file(tmp_path):
    drive = build_fake_drive_with_corrected_folder()
    corrected_dir = tmp_path / "calc" / "2026-03-02" / "corrected"
    corrected_dir.mkdir(parents=True)
    (corrected_dir / "2026-03-02_John Smith.pdf").write_text("marked up")

    results = upload(drive, CLASSES["calc"], base_path=tmp_path)

    assert results[0].action == "uploaded"
    local_path, folder_id, upload_name = drive.uploaded[0]
    assert folder_id == "corrected1"
    assert upload_name == "2026-03-02_John Smith - corrected.pdf"
    assert local_path.name == "2026-03-02_John Smith.pdf"


def test_upload_skips_already_uploaded_file(tmp_path):
    drive = build_fake_drive_with_corrected_folder(
        existing_files=[
            {
                "id": "x",
                "name": "2026-03-02_John Smith - corrected.pdf",
                "createdTime": "2026-03-02T00:00:00.000Z",
            }
        ]
    )
    corrected_dir = tmp_path / "calc" / "2026-03-02" / "corrected"
    corrected_dir.mkdir(parents=True)
    (corrected_dir / "2026-03-02_John Smith.pdf").write_text("marked up")

    results = upload(drive, CLASSES["calc"], base_path=tmp_path)

    assert results[0].action == "skipped"
    assert drive.uploaded == []


def test_upload_reports_no_matching_folder(tmp_path):
    drive = FakeDriveClient(folders_by_parent={None: []}, files_by_folder={})
    corrected_dir = tmp_path / "calc" / "2026-03-02" / "corrected"
    corrected_dir.mkdir(parents=True)
    (corrected_dir / "2026-03-02_Jane Doe.pdf").write_text("marked up")

    results = upload(drive, CLASSES["calc"], base_path=tmp_path)

    assert results[0].action == "no_matching_folder"
