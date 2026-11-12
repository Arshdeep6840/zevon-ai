"""One-time Gmail authorization. Put your OAuth client file (Desktop app type) at data/credentials.json, then:
    pip install -r backend/requirements-google.txt && python scripts/google_auth.py
Test mode with your own Google account is enough for personal use."""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file("data/credentials.json", SCOPES)
creds = flow.run_local_server(port=0)
Path("data/google_token.json").write_text(creds.to_json())
print("Saved data/google_token.json. Restart the backend to enable Gmail tools.")
