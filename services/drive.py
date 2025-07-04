from googleapiclient.discovery import build
from services.auth import get_google_credentials
# from config.settings import GOOGLE_DRIVE_FOLDER_ID

def get_drive_service():
    creds = get_google_credentials()
    return build('drive', 'v3', credentials=creds)

def list_resumes(folder_id):
    service = get_drive_service()
    q = (
        f"'{folder_id}' in parents and "
        "("
        "mimeType='application/pdf' or "
        "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or "
        "mimeType='application/msword'"
        ")"
    )
    return service.files().list(q=q).execute().get('files', [])

def download_file(file_id: str, dest_path: str):
    service = get_drive_service()
    req = service.files().get_media(fileId=file_id)
    with open(dest_path, 'wb') as fh:
        fh.write(req.execute())
