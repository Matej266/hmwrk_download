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
