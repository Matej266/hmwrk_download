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
