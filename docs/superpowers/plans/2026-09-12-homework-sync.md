# Homework Sync Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that downloads student homework submissions from Google Drive (sorted by assignment week and on-time/late status) and uploads corrected versions back to Drive.

**Architecture:** A small set of focused modules — config, filename parsing, on-time/late classification, a thin Drive API client, and two orchestration functions (`sync`, `upload`) — wired together by a CLI entrypoint. Drive API interactions are isolated behind `DriveClient` so `sync`/`upload` can be unit-tested against a fake, with no live network calls in the test suite.

**Tech Stack:** Python 3, `google-api-python-client`, `google-auth-oauthlib` (already installed), `pytest` (installed in Task 1).

**Spec:** `docs/superpowers/specs/2026-09-12-homework-sync-design.md`

## Global Constraints

- Filename convention: submissions are named `<YYYY-MM-DD>_<Student Full Name>.<ext>`, where the date is the assignment's Monday due date.
- Deadlines: PreCalc = due date + 1 day (Tuesday), 13:20 local time. Calc = due date + 3 days (Thursday), 11:25 local time. A file is late if its Drive `createdTime` is at or after the deadline.
- Local mirror root: `Hmwrks/<class_key>/<due-date-or-"late">/<"submitted"|"corrected">/<filename>` — flat, no per-student subfolders.
- Corrected files are uploaded under the original filename with `" - corrected"` inserted before the extension; locally they keep the original filename.
- Every Drive `files.list` call must pass `supportsAllDrives=True`, `includeItemsFromAllDrives=True`, `corpora="allDrives"` (folders may be regular "shared with me" folders or Shared Drive folders — this combination works for both).
- `credentials.json` and `token.json` are never committed (already in `.gitignore`).
- No in-app scheduler — the CLI is designed to be invoked by Windows Task Scheduler or manually.

---

### Task 1: Config module

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `ClassConfig` (dataclass: `key: str`, `drive_name: str`, `top_level_folder_name: str`, `deadline_offset_days: int`, `deadline_time: datetime.time`), `CLASSES: dict[str, ClassConfig]`, `LOCAL_BASE_PATH: str`, `LOG_DIR: str`.

- [ ] **Step 1: Install pytest**

Run: `pip install pytest`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_config.py
from datetime import time

from config import CLASSES, LOCAL_BASE_PATH, LOG_DIR


def test_calc_deadline_is_thursday_1125_three_days_after_due_date():
    calc = CLASSES["calc"]
    assert calc.deadline_offset_days == 3
    assert calc.deadline_time == time(11, 25)


def test_precalc_deadline_is_tuesday_1320_one_day_after_due_date():
    precalc = CLASSES["precalc"]
    assert precalc.deadline_offset_days == 1
    assert precalc.deadline_time == time(13, 20)


def test_class_drive_names_and_folder_names():
    assert CLASSES["calc"].drive_name == "AP Calc"
    assert CLASSES["calc"].top_level_folder_name == "AP Calc - 2026/2027"
    assert CLASSES["precalc"].drive_name == "PreCalc"
    assert CLASSES["precalc"].top_level_folder_name == "PreCalc - 2026/2027"


def test_local_paths():
    assert LOCAL_BASE_PATH == "Hmwrks"
    assert LOG_DIR == "logs"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Write minimal implementation**

```python
# config.py
from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ClassConfig:
    key: str
    drive_name: str
    top_level_folder_name: str
    deadline_offset_days: int
    deadline_time: time


CLASSES: dict[str, ClassConfig] = {
    "calc": ClassConfig(
        key="calc",
        drive_name="AP Calc",
        top_level_folder_name="AP Calc - 2026/2027",
        deadline_offset_days=3,
        deadline_time=time(11, 25),
    ),
    "precalc": ClassConfig(
        key="precalc",
        drive_name="PreCalc",
        top_level_folder_name="PreCalc - 2026/2027",
        deadline_offset_days=1,
        deadline_time=time(13, 20),
    ),
}

LOCAL_BASE_PATH = "Hmwrks"
LOG_DIR = "logs"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add class configuration module"
```

---

### Task 2: Filename parsing

**Files:**
- Create: `filename_parser.py`
- Test: `tests/test_filename_parser.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `parse_filename(filename: str) -> tuple[date, str]` (raises `InvalidFilename`), `corrected_filename(filename: str) -> str`, `InvalidFilename` (exception class).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_filename_parser.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_filename_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'filename_parser'`

- [ ] **Step 3: Write minimal implementation**

```python
# filename_parser.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_filename_parser.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add filename_parser.py tests/test_filename_parser.py
git commit -m "feat: add homework filename parsing"
```

---

### Task 3: Deadline classification

**Files:**
- Create: `classifier.py`
- Test: `tests/test_classifier.py`

**Interfaces:**
- Consumes: `config.ClassConfig`, `config.CLASSES` (Task 1).
- Produces: `compute_deadline(due_date: date, class_config: ClassConfig) -> datetime` (aware, local timezone), `classify(due_date: date, created_at: datetime, class_config: ClassConfig) -> str` (returns `due_date.isoformat()` or `"late"`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_classifier.py
from datetime import date, time, timedelta

from classifier import classify, compute_deadline
from config import CLASSES


def test_compute_deadline_calc_is_three_days_after_due_date_at_1125():
    due_date = date(2026, 3, 2)  # Monday
    deadline = compute_deadline(due_date, CLASSES["calc"])
    assert deadline.date() == date(2026, 3, 5)  # Thursday
    assert deadline.time() == time(11, 25)


def test_compute_deadline_precalc_is_one_day_after_due_date_at_1320():
    due_date = date(2026, 3, 2)  # Monday
    deadline = compute_deadline(due_date, CLASSES["precalc"])
    assert deadline.date() == date(2026, 3, 3)  # Tuesday
    assert deadline.time() == time(13, 20)


def test_classify_on_time_when_before_deadline():
    due_date = date(2026, 3, 2)
    deadline = compute_deadline(due_date, CLASSES["calc"])
    created_at = deadline - timedelta(minutes=1)
    assert classify(due_date, created_at, CLASSES["calc"]) == "2026-03-02"


def test_classify_late_when_at_or_after_deadline():
    due_date = date(2026, 3, 2)
    deadline = compute_deadline(due_date, CLASSES["calc"])
    assert classify(due_date, deadline, CLASSES["calc"]) == "late"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'classifier'`

- [ ] **Step 3: Write minimal implementation**

```python
# classifier.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add classifier.py tests/test_classifier.py
git commit -m "feat: add on-time/late deadline classification"
```

---

### Task 4: Drive client

**Files:**
- Create: `drive_client.py`
- Test: `tests/test_drive_client.py`
- Delete: `test_drive_oauth.py` (superseded — its logic moves into `drive_client.get_credentials`; keep `credentials.json`/`token.json` as-is)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `get_credentials() -> Credentials`, `parse_drive_timestamp(value: str) -> datetime` (aware, local timezone), `DriveClient` class with:
  - `DriveClient(service)` constructor (for tests, inject a fake/mock)
  - `DriveClient.authenticated() -> DriveClient` classmethod (real usage)
  - `find_folder_by_name(name: str, parent_id: str | None = None) -> str | None`
  - `list_subfolders(parent_id: str) -> list[dict]` (each `{"id", "name"}`)
  - `list_files_in_folder(folder_id: str) -> list[dict]` (each `{"id", "name", "createdTime"}`)
  - `download_file(file_id: str, destination: Path) -> None`
  - `upload_file(local_path: Path, folder_id: str, upload_name: str) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_drive_client.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_drive_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drive_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# drive_client.py
import os
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"
FOLDER_MIME = "application/vnd.google-apps.folder"


def get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    return creds


def parse_drive_timestamp(value: str) -> datetime:
    utc_dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return utc_dt.astimezone()


def _escape(value: str) -> str:
    return value.replace("'", "\\'")


class DriveClient:
    def __init__(self, service):
        self.service = service

    @classmethod
    def authenticated(cls) -> "DriveClient":
        return cls(build("drive", "v3", credentials=get_credentials()))

    def _list(self, query: str, fields: str) -> list[dict]:
        results = (
            self.service.files()
            .list(
                q=query,
                corpora="allDrives",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields=fields,
                pageSize=1000,
            )
            .execute()
        )
        return results.get("files", [])

    def find_folder_by_name(self, name: str, parent_id: str | None = None) -> str | None:
        query = f"mimeType='{FOLDER_MIME}' and name='{_escape(name)}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        matches = self._list(query, "files(id, name)")
        return matches[0]["id"] if matches else None

    def list_subfolders(self, parent_id: str) -> list[dict]:
        query = f"mimeType='{FOLDER_MIME}' and '{parent_id}' in parents and trashed=false"
        return self._list(query, "files(id, name)")

    def list_files_in_folder(self, folder_id: str) -> list[dict]:
        query = f"'{folder_id}' in parents and trashed=false and mimeType != '{FOLDER_MIME}'"
        return self._list(query, "files(id, name, createdTime)")

    def download_file(self, file_id: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with open(destination, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def upload_file(self, local_path: Path, folder_id: str, upload_name: str) -> None:
        media = MediaFileUpload(str(local_path))
        metadata = {"name": upload_name, "parents": [folder_id]}
        self.service.files().create(
            body=metadata, media_body=media, supportsAllDrives=True, fields="id"
        ).execute()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_drive_client.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Remove the superseded diagnostic script**

```bash
git rm test_drive_oauth.py
```

- [ ] **Step 6: Commit**

```bash
git add drive_client.py tests/test_drive_client.py
git commit -m "feat: add thin Google Drive API client"
```

---

### Task 5: Sync (download) orchestration

**Files:**
- Create: `sync.py`
- Create: `tests/fakes.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `config.ClassConfig`, `config.LOCAL_BASE_PATH` (Task 1); `filename_parser.parse_filename`, `filename_parser.InvalidFilename` (Task 2); `classifier.classify` (Task 3); `drive_client.DriveClient`, `drive_client.parse_drive_timestamp` (Task 4).
- Produces: `SyncResult` (dataclass: `student: str`, `filename: str`, `action: str`, `bucket: str`), `sync(drive: DriveClient, class_config: ClassConfig, start: date, end: date, base_path: Path = Path(LOCAL_BASE_PATH)) -> list[SyncResult]`. Also `tests/fakes.FakeDriveClient`, reused by Task 6.

- [ ] **Step 1: Write the shared fake Drive client**

```python
# tests/fakes.py
class FakeDriveClient:
    """Test double matching the DriveClient interface — no real Drive calls."""

    def __init__(self, folders_by_parent, files_by_folder):
        self.folders_by_parent = folders_by_parent  # {parent_id_or_None: [{"id","name"}]}
        self.files_by_folder = files_by_folder  # {folder_id: [{"id","name","createdTime"}]}
        self.downloaded = []
        self.uploaded = []

    def find_folder_by_name(self, name, parent_id=None):
        for folder in self.folders_by_parent.get(parent_id, []):
            if folder["name"] == name:
                return folder["id"]
        return None

    def list_subfolders(self, parent_id):
        return self.folders_by_parent.get(parent_id, [])

    def list_files_in_folder(self, folder_id):
        return self.files_by_folder.get(folder_id, [])

    def download_file(self, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"contents of {file_id}")
        self.downloaded.append((file_id, destination))

    def upload_file(self, local_path, folder_id, upload_name):
        self.uploaded.append((local_path, folder_id, upload_name))
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_sync.py
from datetime import date
from pathlib import Path

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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sync'`

- [ ] **Step 4: Write minimal implementation**

```python
# sync.py
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from classifier import classify
from config import ClassConfig, LOCAL_BASE_PATH
from drive_client import DriveClient, parse_drive_timestamp
from filename_parser import InvalidFilename, parse_filename


@dataclass
class SyncResult:
    student: str
    filename: str
    action: str
    bucket: str


def _student_name_from_folder(folder_name: str, class_prefix: str) -> str | None:
    prefix = f"{class_prefix} - "
    if not folder_name.startswith(prefix):
        return None
    return folder_name[len(prefix):]


def sync(
    drive: DriveClient,
    class_config: ClassConfig,
    start: date,
    end: date,
    base_path: Path = Path(LOCAL_BASE_PATH),
) -> list[SyncResult]:
    class_folder_id = drive.find_folder_by_name(class_config.top_level_folder_name)
    if class_folder_id is None:
        raise LookupError(f"Drive folder {class_config.top_level_folder_name!r} not found")

    results: list[SyncResult] = []
    for student_folder in drive.list_subfolders(class_folder_id):
        student_name = _student_name_from_folder(student_folder["name"], class_config.drive_name)
        if student_name is None:
            continue

        homework_folder_id = drive.find_folder_by_name(
            f"{class_config.drive_name} Homeworks - {student_name}",
            parent_id=student_folder["id"],
        )
        if homework_folder_id is None:
            continue

        for file_info in drive.list_files_in_folder(homework_folder_id):
            try:
                due_date, full_name = parse_filename(file_info["name"])
            except InvalidFilename:
                continue
            if not (start <= due_date <= end):
                continue
            if full_name != student_name:
                continue

            created_at = parse_drive_timestamp(file_info["createdTime"])
            bucket = classify(due_date, created_at, class_config)
            target = base_path / class_config.key / bucket / "submitted" / file_info["name"]

            if target.exists():
                results.append(SyncResult(student_name, file_info["name"], "skipped", bucket))
                continue

            drive.download_file(file_info["id"], target)
            results.append(SyncResult(student_name, file_info["name"], "downloaded", bucket))

    return results
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_sync.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/fakes.py tests/test_sync.py
git commit -m "feat: add homework download sync orchestration"
```

---

### Task 6: Upload orchestration

**Files:**
- Create: `upload.py`
- Test: `tests/test_upload.py`

**Interfaces:**
- Consumes: `config.ClassConfig`, `config.LOCAL_BASE_PATH` (Task 1); `filename_parser.parse_filename`, `filename_parser.corrected_filename`, `filename_parser.InvalidFilename` (Task 2); `drive_client.DriveClient` (Task 4); `tests.fakes.FakeDriveClient` (Task 5).
- Produces: `UploadResult` (dataclass: `student: str`, `filename: str`, `action: str` — one of `"uploaded"`, `"skipped"`, `"no_matching_folder"`), `upload(drive: DriveClient, class_config: ClassConfig, base_path: Path = Path(LOCAL_BASE_PATH)) -> list[UploadResult]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_upload.py
from pathlib import Path

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_upload.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'upload'`

- [ ] **Step 3: Write minimal implementation**

```python
# upload.py
from dataclasses import dataclass
from pathlib import Path

from config import ClassConfig, LOCAL_BASE_PATH
from drive_client import DriveClient
from filename_parser import InvalidFilename, corrected_filename, parse_filename


@dataclass
class UploadResult:
    student: str
    filename: str
    action: str


def _find_corrected_folder(drive: DriveClient, class_config: ClassConfig, full_name: str) -> str | None:
    class_folder_id = drive.find_folder_by_name(class_config.top_level_folder_name)
    if class_folder_id is None:
        return None
    student_folder_id = drive.find_folder_by_name(
        f"{class_config.drive_name} - {full_name}", parent_id=class_folder_id
    )
    if student_folder_id is None:
        return None
    return drive.find_folder_by_name(
        f"{class_config.drive_name} Homeworks - {full_name} - corrected",
        parent_id=student_folder_id,
    )


def upload(
    drive: DriveClient,
    class_config: ClassConfig,
    base_path: Path = Path(LOCAL_BASE_PATH),
) -> list[UploadResult]:
    class_dir = base_path / class_config.key
    results: list[UploadResult] = []

    if not class_dir.exists():
        return results

    for bucket_dir in sorted(class_dir.iterdir()):
        corrected_dir = bucket_dir / "corrected"
        if not corrected_dir.is_dir():
            continue

        for local_file in sorted(corrected_dir.iterdir()):
            if not local_file.is_file():
                continue
            try:
                _, full_name = parse_filename(local_file.name)
            except InvalidFilename:
                continue

            upload_name = corrected_filename(local_file.name)
            corrected_folder_id = _find_corrected_folder(drive, class_config, full_name)
            if corrected_folder_id is None:
                results.append(UploadResult(full_name, local_file.name, "no_matching_folder"))
                continue

            existing_names = {f["name"] for f in drive.list_files_in_folder(corrected_folder_id)}
            if upload_name in existing_names:
                results.append(UploadResult(full_name, local_file.name, "skipped"))
                continue

            drive.upload_file(local_file, corrected_folder_id, upload_name)
            results.append(UploadResult(full_name, local_file.name, "uploaded"))

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_upload.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add upload.py tests/test_upload.py
git commit -m "feat: add corrected homework upload orchestration"
```

---

### Task 7: Run logging

**Files:**
- Create: `logger.py`
- Test: `tests/test_logger.py`

**Interfaces:**
- Consumes: nothing from other tasks (accepts plain `list[dict]`).
- Produces: `write_log(rows: list[dict], log_dir: str = "logs") -> Path`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_logger.py
from logger import write_log


def test_write_log_creates_csv_with_rows(tmp_path):
    rows = [
        {
            "student": "John Smith",
            "filename": "2026-03-02_John Smith.pdf",
            "action": "downloaded",
            "bucket": "2026-03-02",
        }
    ]

    log_path = write_log(rows, log_dir=str(tmp_path))

    assert log_path.exists()
    content = log_path.read_text()
    assert "John Smith" in content
    assert "downloaded" in content


def test_write_log_prints_summary_to_console(tmp_path, capsys):
    rows = [{"student": "John Smith", "filename": "a.pdf", "action": "downloaded", "bucket": "2026-03-02"}]

    write_log(rows, log_dir=str(tmp_path))

    captured = capsys.readouterr()
    assert "downloaded" in captured.out


def test_write_log_handles_empty_rows(tmp_path, capsys):
    log_path = write_log([], log_dir=str(tmp_path))

    assert log_path.exists()
    captured = capsys.readouterr()
    assert "No actions taken." in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_logger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logger'`

- [ ] **Step 3: Write minimal implementation**

```python
# logger.py
import csv
from datetime import datetime
from pathlib import Path
from typing import Sequence


def write_log(rows: Sequence[dict], log_dir: str = "logs") -> Path:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(log_dir) / f"run_{timestamp}.csv"

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(log_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _print_summary(rows)
    return log_path


def _print_summary(rows: Sequence[dict]) -> None:
    if not rows:
        print("No actions taken.")
        return
    for row in rows:
        print(" | ".join(f"{key}={value}" for key, value in row.items()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_logger.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add CSV/console run logging"
```

---

### Task 8: CLI entrypoint

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `config.CLASSES` (Task 1); `drive_client.DriveClient` (Task 4); `sync.sync` (Task 5); `upload.upload` (Task 6); `logger.write_log` (Task 7).
- Produces: `build_parser() -> argparse.ArgumentParser`, `main(argv: list[str] | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write minimal implementation**

```python
# main.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests across every task PASS

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add CLI entrypoint wiring sync and upload"
```

- [ ] **Step 7: Manual end-to-end smoke test (real Drive, real credentials)**

Since Drive access now needs the broader `https://www.googleapis.com/auth/drive` scope (not just `drive.readonly`, which `token.json` was issued for), delete the existing token so the CLI re-authenticates with the new scope:

Run: `del token.json`

Then, against your real class folders:

```bash
python main.py sync --class calc --week 2026-03-02
```

Confirm it prints a run summary, writes a CSV under `logs/`, and that files land under `Hmwrks/calc/2026-03-02/submitted/` (or `Hmwrks/calc/late/submitted/` for anything past the Thursday 11:25 deadline). Then place a test file in a `Hmwrks/calc/2026-03-02/corrected/` folder and run:

```bash
python main.py upload --class calc
```

Confirm it appears in the matching student's `"AP Calc Homeworks - <Name> - corrected"` Drive folder as `<original name> - corrected.<ext>`. This step is exploratory verification against live data — not part of the automated test suite.
