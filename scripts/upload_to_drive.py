"""Upload rendered video/thumbnail files to a Google Drive folder via a service account.

Used by .github/workflows/render-shorts.yml as an optional convenience step —
GitHub Actions Artifacts remain the source of truth; this just mirrors the
output to Drive so nobody has to dig through the Actions UI to download it.

Env vars:
    GDRIVE_SA_KEY_JSON  Service account credentials (the full JSON key file content)
    GDRIVE_FOLDER_ID    Destination Drive folder ID (the owner must have shared
                         this folder with the service account's client_email)
"""
import json
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def upload(paths: list[str]) -> None:
    key_json = os.environ["GDRIVE_SA_KEY_JSON"]
    folder_id = os.environ["GDRIVE_FOLDER_ID"]

    info = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build("drive", "v3", credentials=credentials)

    for path in paths:
        if not os.path.isfile(path):
            print(f"skip (not found): {path}")
            continue
        filename = os.path.basename(path)
        metadata = {"name": filename, "parents": [folder_id]}
        media = MediaFileUpload(path, resumable=True)
        uploaded = service.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
        print(f"uploaded {filename} -> {uploaded.get('webViewLink', uploaded.get('id'))}")


if __name__ == "__main__":
    file_paths = sys.argv[1:]
    if not file_paths:
        print("usage: python upload_to_drive.py <file1> [file2 ...]", file=sys.stderr)
        sys.exit(1)
    upload(file_paths)
