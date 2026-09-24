from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from drive_client import DriveClient, parse_drive_timestamp


def test_parse_drive_timestamp_matches_known_utc_instant():
    result = parse_drive_timestamp("2026-03-02T17:45:00.000Z")
    assert result.astimezone(timezone.utc) == datetime(2026, 3, 2, 17, 45, tzinfo=timezone.utc)


def test_parse_drive_timestamp_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_drive_timestamp("not-a-timestamp")


def test_find_folder_by_name_returns_first_match_id():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "abc123", "name": "AP Calc - 2026/2027"}]
    }
    client = DriveClient(service)
    assert client.find_folder_by_name("AP Calc - 2026/2027") == "abc123"


def test_find_folder_by_name_returns_none_when_not_found():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    client = DriveClient(service)
    assert client.find_folder_by_name("Nonexistent") is None


def test_list_files_in_folder_returns_metadata():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "f1",
                "name": "2026-03-02_John Smith.pdf",
                "createdTime": "2026-03-02T17:00:00.000Z",
            }
        ]
    }
    client = DriveClient(service)
    files = client.list_files_in_folder("folder123")

    _, kwargs = service.files.return_value.list.call_args
    assert "mimeType" in kwargs["fields"]

    assert files == [
        {
            "id": "f1",
            "name": "2026-03-02_John Smith.pdf",
            "createdTime": "2026-03-02T17:00:00.000Z",
        }
    ]


def test_download_file_writes_to_destination(tmp_path):
    service = MagicMock()
    client = DriveClient(service)
    destination = tmp_path / "sub" / "file.pdf"

    with patch("drive_client.MediaIoBaseDownload") as mock_downloader_cls:
        mock_downloader_cls.return_value.next_chunk.return_value = (None, True)
        client.download_file("file123", destination)

    assert destination.parent.exists()
    service.files.return_value.get_media.assert_called_once_with(
        fileId="file123", supportsAllDrives=True
    )


def test_upload_file_sets_name_and_parent(tmp_path):
    service = MagicMock()
    client = DriveClient(service)
    local_file = tmp_path / "2026-03-02_John Smith - corrected.pdf"
    local_file.write_text("fake pdf content")

    client.upload_file(local_file, "folder456", "2026-03-02_John Smith - corrected.pdf")

    _, kwargs = service.files.return_value.create.call_args
    assert kwargs["body"] == {
        "name": "2026-03-02_John Smith - corrected.pdf",
        "parents": ["folder456"],
    }
