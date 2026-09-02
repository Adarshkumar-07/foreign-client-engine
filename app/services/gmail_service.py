import os
import json
import base64
import secrets
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose"
]

TOKEN_PATH = "token.json"
OAUTH_STATE_PATH = "oauth_state.json"


def _client_config():
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET are not configured."
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GMAIL_REDIRECT_URI", "")]
        }
    }


def get_gmail_service():
    """Return an authenticated Gmail API service using a web OAuth token."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(
                TOKEN_PATH,
                SCOPES
            )
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail is not connected. Open /api/gmail/login first."
        )

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def gmail_is_connected():
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return {
            "connected": True,
            "email": profile.get("emailAddress")
        }
    except Exception:
        return {
            "connected": False,
            "email": None
        }


def get_authorization_url():
    redirect_uri = os.getenv("GMAIL_REDIRECT_URI")
    if not redirect_uri:
        raise RuntimeError("GMAIL_REDIRECT_URI is not configured.")

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    # google-auth-oauthlib generates a PKCE verifier inside the Flow.
    # The callback creates a new Flow, so persist the verifier between
    # the authorization request and the token exchange.
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    with open(OAUTH_STATE_PATH, "w", encoding="utf-8") as oauth_state:
        json.dump(
            {
                "state": state,
                "code_verifier": flow.code_verifier
            },
            oauth_state
        )

    return authorization_url, state


def complete_authorization(code: str):
    redirect_uri = os.getenv("GMAIL_REDIRECT_URI")
    if not redirect_uri:
        raise RuntimeError("GMAIL_REDIRECT_URI is not configured.")

    code_verifier = None
    if os.path.exists(OAUTH_STATE_PATH):
        try:
            with open(OAUTH_STATE_PATH, "r", encoding="utf-8") as oauth_state:
                saved_state = json.load(oauth_state)
            code_verifier = saved_state.get("code_verifier")
        except Exception:
            code_verifier = None

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    if code_verifier:
        flow.code_verifier = code_verifier

    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_PATH, "w", encoding="utf-8") as token:
        token.write(creds.to_json())

    # The verifier is single-use. Remove it after a successful exchange.
    try:
        os.remove(OAUTH_STATE_PATH)
    except FileNotFoundError:
        pass

    return gmail_is_connected()


def _encode_message(recipient: str, subject: str, body: str):
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = recipient
    message["subject"] = subject

    return base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()


def create_gmail_draft(recipient: str, subject: str, body: str):
    service = get_gmail_service()

    draft = service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": _encode_message(recipient, subject, body)
            }
        }
    ).execute()

    return {
        "status": "DRAFT_CREATED",
        "draft_id": draft.get("id"),
        "recipient": recipient,
        "subject": subject
    }


def send_gmail_message(recipient: str, subject: str, body: str):
    service = get_gmail_service()

    sent = service.users().messages().send(
        userId="me",
        body={
            "raw": _encode_message(recipient, subject, body)
        }
    ).execute()

    return {
        "status": "SENT",
        "message_id": sent.get("id"),
        "recipient": recipient,
        "subject": subject
    }
