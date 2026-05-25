"""
Gmail MCP Server (stdio)
=======================

Built-in Gmail MCP server so `clent` can always expose Gmail tools without
depending on an external `gmail` executable.

OAuth is performed lazily: the server starts and advertises tools even when the
credentials/token files are missing. The first actual Gmail tool call will
prompt the user to complete OAuth (via a local browser flow) if needed.
"""

from __future__ import annotations

import argparse
import base64
import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Suppress noisy MCP protocol debug messages (e.g. "Processing request of type ...")
logging.getLogger("mcp.server").setLevel(logging.WARNING)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

mcp = FastMCP("gmail")

_CREDS_PATH: Path | None = None
_TOKEN_PATH: Path | None = None
_SERVICE = None


def _b64url_decode(data: str) -> str:
    if not data:
        return ""
    s = data.replace("-", "+").replace("_", "/")
    pad = "=" * ((4 - len(s) % 4) % 4)
    raw = base64.b64decode((s + pad).encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def _extract_headers(payload: dict) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for h in payload.get("headers", []) or []:
        name = str(h.get("name") or "").strip()
        value = str(h.get("value") or "").strip()
        if name:
            headers[name] = value
    return headers


def _extract_text_plain(payload: dict) -> str:
    """
    Best-effort extraction of text/plain bodies from Gmail message payload.
    """
    if not isinstance(payload, dict):
        return ""

    body = payload.get("body") or {}
    data = body.get("data")
    mime_type = (payload.get("mimeType") or "").lower()

    if isinstance(data, str) and mime_type == "text/plain":
        return _b64url_decode(data)

    parts = payload.get("parts") or []
    if isinstance(parts, list):
        texts: List[str] = []
        for part in parts:
            texts.append(_extract_text_plain(part))
        return "\n".join([t for t in texts if t.strip()])

    return ""


def _get_service():
    global _SERVICE

    if _SERVICE is not None:
        return _SERVICE

    if _CREDS_PATH is None or _TOKEN_PATH is None:
        raise RuntimeError("Gmail server not initialized (missing paths).")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Gmail dependencies are missing. Install: google-api-python-client google-auth google-auth-oauthlib"
        ) from exc

    creds = None
    if _TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    if creds is None or not creds.valid:
        if creds is not None and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials file not found: {_CREDS_PATH}. "
                    "Create one in Google Cloud Console and place it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        try:
            _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            _TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        except OSError:
            # Token persistence is best-effort; still allow the current run.
            pass

    _SERVICE = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _SERVICE


@mcp.tool(description="Search Gmail using Gmail's query syntax. Returns message IDs + basic metadata.")
def gmail_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    service = _get_service()

    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=int(max_results))
        .execute()
    )
    messages = resp.get("messages") or []

    results: List[Dict[str, Any]] = []
    for m in messages:
        mid = m.get("id")
        if not mid:
            continue
        meta = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            )
            .execute()
        )
        payload = meta.get("payload") or {}
        results.append(
            {
                "id": meta.get("id"),
                "threadId": meta.get("threadId"),
                "labelIds": meta.get("labelIds") or [],
                "snippet": meta.get("snippet") or "",
                "internalDate": meta.get("internalDate"),
                "headers": _extract_headers(payload),
            }
        )

    return results


@mcp.tool(description="Fetch a Gmail message and return headers + best-effort plain text body.")
def gmail_get_message(message_id: str) -> Dict[str, Any]:
    service = _get_service()

    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = msg.get("payload") or {}
    return {
        "id": msg.get("id"),
        "threadId": msg.get("threadId"),
        "labelIds": msg.get("labelIds") or [],
        "snippet": msg.get("snippet") or "",
        "headers": _extract_headers(payload),
        "body_text": _extract_text_plain(payload),
    }


@mcp.tool(description="Send an email via Gmail.")
def gmail_send(
    to: List[str] | str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
) -> Dict[str, Any]:
    service = _get_service()

    to_list = [to] if isinstance(to, str) else list(to or [])
    if not to_list:
        raise ValueError("'to' must be a non-empty string or list of strings")

    msg = EmailMessage()
    msg["To"] = ", ".join([t for t in to_list if t])
    msg["Subject"] = subject or ""
    if cc:
        msg["Cc"] = ", ".join([c for c in cc if c])
    if bcc:
        msg["Bcc"] = ", ".join([b for b in bcc if b])
    msg.set_content(body or "")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    return {
        "id": sent.get("id"),
        "threadId": sent.get("threadId"),
        "labelIds": sent.get("labelIds") or [],
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--creds-file-path", required=True)
    p.add_argument("--token-path", required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _CREDS_PATH = Path(args.creds_file_path).expanduser()
    _TOKEN_PATH = Path(args.token_path).expanduser()
    mcp.run(transport="stdio")

