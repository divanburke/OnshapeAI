"""Onshape API-key request signing.

Based on the official Onshape request-signature specification.
See docs/auth/apikeys/ in the Onshape Developer Documentation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlsplit


def build_onshape_headers(
    method: str,
    url: str,
    access_key: str,
    secret_key: str,
    content_type: str = "application/json;charset=UTF-8; qs=0.09",
) -> dict[str, str]:
    """Build Date, On-Nonce and Authorization headers for one HTTP request."""
    if not access_key or not secret_key:
        raise ValueError("Onshape API credentials are not configured.")

    nonce = secrets.token_hex(16)
    date_value = format_datetime(datetime.now(timezone.utc), usegmt=True)
    parsed = urlsplit(url)
    canonical = "\\n".join(
        [method.upper(), nonce, date_value, content_type, parsed.path or "/", parsed.query]
    ).lower() + "\\n"
    digest = hmac.new(
        secret_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).digest()
    signature = base64.b64encode(digest).decode("ascii")

    return {
        "Date": date_value,
        "On-Nonce": nonce,
        "Authorization": f"On {access_key}:HmacSHA256:{signature}",
        "Accept": "application/json;charset=UTF-8; qs=0.09",
        "Content-Type": content_type,
    }
