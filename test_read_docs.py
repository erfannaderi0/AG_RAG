from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

results = drive_service.files().list(
    q="mimeType='application/vnd.google-apps.document'",
    fields="files(id, name)"
).execute()

for f in results.get('files', []):
    print(f['name'], f['id'])
