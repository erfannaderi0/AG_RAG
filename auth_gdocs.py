from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    SCOPES,
    redirect_uri='http://localhost:8080/'
)

creds = flow.run_local_server(port=8080)

# Save the token so you don't have to re-authenticate every time
with open('token.json', 'w') as f:
    f.write(creds.to_json())

print("Auth successful. Token saved to token.json")
