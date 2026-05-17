from __future__ import annotations

import asyncio
import base64
from datetime import datetime
from email.utils import parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.models import EmailItem

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient:
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json") -> None:
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.service = None

    def authenticate(self) -> None:
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        self.service = build("gmail", "v1", credentials=creds)

    async def fetch_unread_messages(self, max_results: int = 1000) -> list[EmailItem]:
        if not self.service:
            raise RuntimeError("Gmail client not authenticated")
        messages = await asyncio.to_thread(
            lambda: self.service.users().messages().list(userId="me", q="is:unread", maxResults=max_results).execute()
        )
        ids = [m["id"] for m in messages.get("messages", [])]
        tasks = [self._fetch_one(mid) for mid in ids]
        return await asyncio.gather(*tasks)

    async def _fetch_one(self, message_id: str) -> EmailItem:
        payload = await asyncio.to_thread(
            lambda: self.service.users().messages().get(userId="me", id=message_id, format="metadata", metadataHeaders=["Subject", "From"]).execute()
        )
        headers = {h["name"]: h["value"] for h in payload.get("payload", {}).get("headers", [])}
        sender = headers.get("From", "unknown")
        _, sender_addr = parseaddr(sender)
        domain = sender_addr.split("@")[-1].lower() if "@" in sender_addr else "unknown"
        return EmailItem(
            id=payload["id"],
            thread_id=payload.get("threadId", ""),
            subject=headers.get("Subject", "(No Subject)"),
            sender=sender,
            sender_domain=domain,
            snippet=payload.get("snippet", ""),
            internal_date=datetime.utcfromtimestamp(int(payload.get("internalDate", "0")) / 1000),
        )

    async def batch_modify(self, email_ids: list[str], *, add_labels: list[str] | None = None, remove_labels: list[str] | None = None) -> None:
        if not self.service:
            raise RuntimeError("Gmail client not authenticated")
        chunk_size = 500
        for idx in range(0, len(email_ids), chunk_size):
            chunk = email_ids[idx : idx + chunk_size]
            body = {"ids": chunk, "addLabelIds": add_labels or [], "removeLabelIds": remove_labels or []}
            await asyncio.to_thread(
                lambda: self.service.users().messages().batchModify(userId="me", body=body).execute()
            )
