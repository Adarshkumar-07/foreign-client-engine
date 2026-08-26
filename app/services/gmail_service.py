import os
import base64

from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose"
]


def get_gmail_service():
    """
    Authenticate with Gmail API and return
    an authorized Gmail service.
    """

    creds = None

    token_path = "token.json"
    credentials_path = "credentials.json"

    # Load existing login token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(
            token_path,
            SCOPES
        )

    # Refresh expired token
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # First-time authentication
    if not creds or not creds.valid:

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                "credentials.json not found. "
                "Download Gmail API OAuth credentials "
                "and place them in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        # Save token for future use
        with open(
            token_path,
            "w"
        ) as token:
            token.write(
                creds.to_json()
            )

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def create_gmail_draft(
    recipient: str,
    subject: str,
    body: str
):
    """
    Create a Gmail draft.
    Does NOT send the email.
    """

    service = get_gmail_service()

    message = MIMEText(
        body,
        "plain"
    )

    message["to"] = recipient
    message["subject"] = subject

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    draft_body = {
        "message": {
            "raw": encoded_message
        }
    }

    draft = service.users().drafts().create(
        userId="me",
        body=draft_body
    ).execute()

    return {
        "status": "DRAFT_CREATED",
        "draft_id": draft.get("id"),
        "recipient": recipient,
        "subject": subject
    }