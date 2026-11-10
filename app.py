"""Small WSGI app for the Unbusyness static site and waitlist email endpoint."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import smtplib
import ssl
import threading
import time
from collections import defaultdict, deque
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
RECIPIENT = "info@unbusyness.com"
MAX_BODY_BYTES = 32_768
MAX_FIELD_CHARS = 2_000
ALLOWED_SEGMENTS = {
    "resident",
    "manager",
    "trade",
    "hotel",
    "residents",
    "building_managers",
    "tradespeople",
    "hotels",
    "investors",
}
SEGMENT_LABELS = {
    "resident": "Resident",
    "manager": "Building manager",
    "trade": "Tradesperson",
    "hotel": "Hotel",
    "residents": "Residents",
    "building_managers": "Building managers",
    "tradespeople": "Tradespeople",
    "hotels": "Hotels",
    "investors": "Investor request",
}
FIELD_LABELS = {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "company": "Company",
    "trade": "Trade",
    "field1": "Additional information",
    "field2": "Additional information",
    "buildings": "Buildings",
    "rooms": "Rooms",
    "country": "Country",
    "city": "City",
    "home": "Home type",
    "manager": "Building manager",
    "managerUsesUnbusyness": "Manager uses Unbusyness",
    "contactManager": "Contact the manager",
    "address": "Address",
    "pains": "Needs",
    "wants": "Interests",
    "role": "Role",
    "message": "Message",
    "language": "Language",
    "page": "Page",
}
STATIC_EXTENSIONS = {
    ".avif",
    ".css",
    ".gif",
    ".html",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mp4",
    ".png",
    ".svg",
    ".webm",
    ".webp",
}
EMAIL_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
RATE_WINDOW_SECONDS = 300
RATE_LIMIT = 10
_rate_lock = threading.Lock()
_request_times: dict[str, deque[float]] = defaultdict(deque)


class BadRequest(Exception):
    pass


class MissingSmtpConfiguration(Exception):
    pass


def _response(start_response, status: str, body: bytes = b"", content_type="text/plain; charset=utf-8", headers=None):
    response_headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ]
    if headers:
        response_headers.extend(headers)
    start_response(status, response_headers)
    return [body]


def _json_response(start_response, status: str, payload: dict):
    return _response(
        start_response,
        status,
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        "application/json; charset=utf-8",
    )


def _client_key(environ) -> str:
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    # Replit's proxy sets this header for browser requests. Ignore malformed values.
    candidate = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if candidate and len(candidate) <= 64 and re.fullmatch(r"[0-9a-fA-F:.]+", candidate):
        return candidate
    return environ.get("REMOTE_ADDR", "unknown")[:64]


def _is_rate_limited(client_key: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        requests = _request_times[client_key]
        while requests and now - requests[0] > RATE_WINDOW_SECONDS:
            requests.popleft()
        if len(requests) >= RATE_LIMIT:
            return True
        requests.append(now)
        return False


def _clean_value(value):
    if isinstance(value, str):
        value = value.strip()
        if len(value) > MAX_FIELD_CHARS:
            raise BadRequest("A field is too long.")
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        if len(value) > 50:
            raise BadRequest("Too many values.")
        return [_clean_value(item) for item in value]
    raise BadRequest("Unsupported field value.")


def _parse_signup(environ) -> dict:
    if environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
        raise BadRequest("Expected JSON.")
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise BadRequest("Invalid content length.") from exc
    if length <= 0 or length > MAX_BODY_BYTES:
        raise BadRequest("Invalid request size.")
    try:
        raw = environ["wsgi.input"].read(length)
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BadRequest("Invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise BadRequest("Expected a JSON object.")

    cleaned = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,49}", key):
            raise BadRequest("Invalid field name.")
        cleaned[key] = _clean_value(value)

    segment = cleaned.get("segment")
    email = cleaned.get("email")
    if segment not in ALLOWED_SEGMENTS:
        raise BadRequest("Invalid list.")
    if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise BadRequest("Invalid email address.")
    if cleaned.get("consent") is not True:
        raise BadRequest("Consent is required.")
    return cleaned


def _build_message(data: dict, sender: str) -> EmailMessage:
    segment = data["segment"]
    message = EmailMessage()
    message["Subject"] = f"New Unbusyness waitlist signup — {SEGMENT_LABELS[segment]}"
    message["From"] = sender
    message["To"] = RECIPIENT
    message["Reply-To"] = data["email"]
    lines = [
        f"New sign-up for: {SEGMENT_LABELS[segment]}",
        "",
        "Submitted details:",
    ]
    for key, value in data.items():
        if key in {"segment", "consent", "website"}:
            continue
        label = FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value) if value is not None else ""
        lines.append(f"{label}: {rendered}")
    lines.extend(["", "Consent to be contacted: Yes"])
    message.set_content("\n".join(lines))
    return message


def _send_email(data: dict):
    host = os.environ.get("SMTP_HOST", "").strip()
    port_value = os.environ.get("SMTP_PORT", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    if not all((host, port_value, username, password)):
        raise MissingSmtpConfiguration
    if any(char in username for char in "\r\n<>"):
        raise MissingSmtpConfiguration
    try:
        port = int(port_value)
    except ValueError as exc:
        raise MissingSmtpConfiguration from exc
    if not 1 <= port <= 65535:
        raise MissingSmtpConfiguration

    message = _build_message(data, username)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(message)


def _serve_static(path_info: str, start_response):
    decoded = unquote(path_info or "/")
    if "\x00" in decoded or decoded.startswith("//"):
        return _response(start_response, "400 Bad Request", b"Bad request")
    relative = decoded.lstrip("/") or "index.html"
    requested = (ROOT / relative).resolve()
    if not requested.is_relative_to(ROOT) or any(part.startswith(".") for part in requested.relative_to(ROOT).parts):
        return _response(start_response, "404 Not Found", b"Not found")
    if requested.is_dir():
        requested = requested / "index.html"
    if requested.suffix.lower() not in STATIC_EXTENSIONS or not requested.is_file():
        return _response(start_response, "404 Not Found", b"Not found")
    try:
        body = requested.read_bytes()
    except OSError:
        return _response(start_response, "404 Not Found", b"Not found")
    content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
    headers = [("Cache-Control", "no-cache" if requested.suffix.lower() == ".html" else "public, max-age=3600")]
    return _response(start_response, "200 OK", body, content_type, headers)


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/health":
        return _response(start_response, "200 OK", b"ok")

    if path == "/api/waitlist":
        if method != "POST":
            return _json_response(start_response, "405 Method Not Allowed", {"error": "Method not allowed."})
        origin = environ.get("HTTP_ORIGIN", "")
        host = environ.get("HTTP_HOST", "")
        if origin:
            origin_host = urlsplit(origin).netloc.casefold()
            if not host or origin_host != host.casefold():
                return _json_response(start_response, "403 Forbidden", {"error": "Request not allowed."})
        if _is_rate_limited(_client_key(environ)):
            return _json_response(start_response, "429 Too Many Requests", {"error": "Please try again later."})
        try:
            data = _parse_signup(environ)
        except BadRequest:
            return _json_response(start_response, "400 Bad Request", {"error": "Please check the form and try again."})
        if data.get("website"):
            return _json_response(start_response, "200 OK", {"ok": True})
        try:
            _send_email(data)
        except MissingSmtpConfiguration:
            return _json_response(start_response, "503 Service Unavailable", {"error": "Waitlist email is not configured."})
        except (smtplib.SMTPException, OSError, ssl.SSLError):
            return _json_response(start_response, "502 Bad Gateway", {"error": "The sign-up email could not be sent."})
        return _json_response(start_response, "200 OK", {"ok": True})

    if method not in {"GET", "HEAD"}:
        return _response(start_response, "405 Method Not Allowed", b"Method not allowed")
    result = _serve_static(path, start_response)
    if method == "HEAD" and result:
        # Keep the status/headers generated by the static handler but omit its body.
        return [b""]
    return result
