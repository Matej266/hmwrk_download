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
