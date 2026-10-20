import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from classifier import classify
from config import ClassConfig, LOCAL_BASE_PATH
from drive_client import DriveClient, parse_drive_timestamp
from filename_parser import InvalidFilename, parse_due_date

PDF_MIME = "application/pdf"


@dataclass
class SyncResult:
    student: str
    filename: str
    original_filename: str
    action: str
    bucket: str


def _student_name_from_folder(folder_name: str, class_prefix: str) -> str | None:
    prefix = f"{class_prefix} - "
    if not folder_name.startswith(prefix):
        return None
    return folder_name[len(prefix):]


def _ensure_corrected_copy(submitted_path: Path, bucket_dir: Path, local_filename: str) -> None:
    corrected_path = bucket_dir / "corrected" / local_filename
    if corrected_path.exists():
        return  # don't clobber annotations already made on a prior copy
    corrected_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(submitted_path, corrected_path)


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
                due_date = parse_due_date(file_info["name"])
            except InvalidFilename:
                continue

            if due_date.weekday() != 0:
                # Only a Monday is a real assignment due-date; a student who
                # put their actual (later) submission date in the filename
                # instead gets flagged here rather than silently downloaded
                # into the wrong week.
                results.append(
                    SyncResult(
                        student_name, file_info["name"], file_info["name"], "skipped_not_monday", "invalid"
                    )
                )
                continue

            if not (start <= due_date <= end):
                continue

            if file_info.get("mimeType") != PDF_MIME:
                # Checked by Drive's MIME type, not the filename: students often
                # upload photos or Google Docs with no extension at all.
                results.append(
                    SyncResult(
                        student_name,
                        file_info["name"],
                        file_info["name"],
                        "skipped_not_pdf",
                        classify(due_date, parse_drive_timestamp(file_info["createdTime"]), class_config),
                    )
                )
                continue

            local_filename = f"{due_date.isoformat()}_{student_name}.pdf"

            created_at = parse_drive_timestamp(file_info["createdTime"])
            bucket = classify(due_date, created_at, class_config)
            bucket_dir = base_path / class_config.key / bucket
            target = bucket_dir / "submitted" / local_filename

            if target.exists():
                results.append(
                    SyncResult(student_name, local_filename, file_info["name"], "skipped", bucket)
                )
                _ensure_corrected_copy(target, bucket_dir, local_filename)
                continue

            drive.download_file(file_info["id"], target)
            results.append(
                SyncResult(student_name, local_filename, file_info["name"], "downloaded", bucket)
            )
            _ensure_corrected_copy(target, bucket_dir, local_filename)

    return results
