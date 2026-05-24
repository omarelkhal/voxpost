"""OAuth 2.0 flow and Gmail API credential management."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def load_credentials(token_path: Path, client_secrets: Path) -> Credentials | None:
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(token_path, creds)
    return creds


def save_credentials(token_path: Path, creds: Credentials) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")


def run_connect_flow(
    token_path: Path,
    client_secrets: Path,
    port: int = 8765,
) -> Credentials:
    """Run local OAuth and persist refresh token."""
    if not client_secrets.exists():
        raise FileNotFoundError(
            f"OAuth client secrets not found: {client_secrets}. See docs/SETUP.md."
        )

    def _flow() -> InstalledAppFlow:
        return InstalledAppFlow.from_client_secrets_file(
            str(client_secrets), GMAIL_SCOPES
        )

    try:
        creds = _flow().run_local_server(port=port, open_browser=True)
    except OSError as err:
        if err.errno != 98:  # EADDRINUSE
            raise
        # Stale listener or another app on the default port — use any free port.
        creds = _flow().run_local_server(port=0, open_browser=True)

    save_credentials(token_path, creds)
    return creds


def get_gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_profile_email(service) -> str:
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]
