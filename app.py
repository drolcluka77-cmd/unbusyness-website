"""Small WSGI app for the Unbusyness static site and waitlist email endpoint."""

from __future__ import annotations

import json
import logging
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

import psycopg

from waitlist_db import (
    DatabaseConfigurationError,
    begin_notification_attempt,
    check_database,
    record_notification_result,
    save_signup,
)


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
    def __init__(self, message, code="invalid_form"):
        super().__init__(message)
        self.code = code


class MissingSmtpConfiguration(Exception):
    pass


def _response(start_response, status: str, body: bytes = b"", content_type="text/plain; charset=utf-8", headers=None):
    headers = list(headers or [])
    response_headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("X-Content-Type-Options", "nosniff"),
    ]
    # A caller-supplied Cache-Control replaces the default (two conflicting headers would mean "no-store").
    if not any(name.lower() == "cache-control" for name, _ in headers):
        response_headers.append(("Cache-Control", "no-store"))
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
            raise BadRequest("A field is too long.", "field_too_long")
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
        raise BadRequest("Invalid list.", "invalid_list")
    if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise BadRequest("Invalid email address.", "invalid_email")
    if cleaned.get("consent") is not True:
        raise BadRequest("Consent is required.", "consent_required")
    return cleaned


def _build_message(data: dict) -> EmailMessage:
    segment = data["segment"]
    message = EmailMessage()
    message["Subject"] = f"New Unbusyness waitlist signup — {SEGMENT_LABELS[segment]}"
    message["From"] = RECIPIENT
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


def _smtp_login(server, username: str, password: str):
    """Use AUTH LOGIN explicitly; some servers reject PLAIN despite advertising both."""
    server.ehlo_or_helo_if_needed()
    responses = iter((username, password))

    def answer(_challenge):
        return next(responses)

    server.auth("LOGIN", answer, initial_response_ok=False)


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

    message = _build_message(data)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
            _smtp_login(server, username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            _smtp_login(server, username, password)
            server.send_message(message)


def _smtp_error_summary(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPResponseException):
        return f"{type(exc).__name__} ({exc.smtp_code})"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        codes = sorted({str(response[0]) for response in exc.recipients.values()})
        return f"SMTPRecipientsRefused ({', '.join(codes)})"
    return type(exc).__name__


RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _byte_range(header: str, size: int):
    """Parse a single 'bytes=a-b' range. Returns (start, end) inclusive, None to ignore, or 'invalid'."""
    match = RANGE_RE.fullmatch(header.strip())
    if not match or size == 0:
        return None
    first, last = match.groups()
    if first == "" and last == "":
        return None
    if first == "":  # suffix range: the last N bytes
        length = int(last)
        if length == 0:
            return "invalid"
        return max(0, size - length), size - 1
    start = int(first)
    end = int(last) if last else size - 1
    if start >= size or end < start:
        return "invalid"
    return start, min(end, size - 1)


def _cache_header(suffix: str) -> str:
    if suffix == ".html":
        return "no-cache"
    if suffix in {".mp4", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg", ".ico"}:
        return "public, max-age=86400"
    return "public, max-age=3600"


def _serve_static(path_info: str, start_response, environ=None):
    environ = environ or {}
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
    content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
    headers = [("Cache-Control", _cache_header(requested.suffix.lower())), ("Accept-Ranges", "bytes")]
    try:
        size = requested.stat().st_size
        wanted = _byte_range(environ.get("HTTP_RANGE", ""), size) if environ.get("HTTP_RANGE") else None
        if wanted == "invalid":
            return _response(start_response, "416 Range Not Satisfiable", b"", content_type, headers + [("Content-Range", f"bytes */{size}")])
        if wanted:
            # Safari (iPhone, iPad, Mac) only plays video when the server answers byte ranges.
            start, end = wanted
            with requested.open("rb") as handle:
                handle.seek(start)
                body = handle.read(end - start + 1)
            return _response(start_response, "206 Partial Content", body, content_type, headers + [("Content-Range", f"bytes {start}-{end}/{size}")])
        body = requested.read_bytes()
    except OSError:
        return _response(start_response, "404 Not Found", b"Not found")
    return _response(start_response, "200 OK", body, content_type, headers)


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/health":
        try:
            check_database()
        except (DatabaseConfigurationError, psycopg.Error, OSError) as exc:
            logging.error("Database health check failed (%s)", type(exc).__name__)
            return _response(start_response, "503 Service Unavailable", b"database unavailable")
        return _response(start_response, "200 OK", b"ok")

    if path == "/api/waitlist":
        if method != "POST":
            return _json_response(start_response, "405 Method Not Allowed", {"error": "Method not allowed."})
        origin = environ.get("HTTP_ORIGIN", "")
        host = environ.get("HTTP_HOST", "")
        if origin:
            origin_host = urlsplit(origin).netloc.casefold()
            if not host or origin_host != host.casefold():
                logging.warning("Waitlist request rejected: origin_blocked")
                return _json_response(start_response, "403 Forbidden", {"error": "Request not allowed.", "code": "origin_blocked"})
        if _is_rate_limited(_client_key(environ)):
            logging.warning("Waitlist request rejected: rate_limited")
            return _json_response(start_response, "429 Too Many Requests", {"error": "Please try again later.", "code": "rate_limited"})
        try:
            data = _parse_signup(environ)
        except BadRequest as exc:
            logging.warning("Waitlist request rejected: %s", exc.code)
            return _json_response(start_response, "400 Bad Request", {"error": "Please check the form and try again.", "code": exc.code})
        if data.get("website"):
            return _json_response(start_response, "200 OK", {"ok": True})
        try:
            signup_id = save_signup(data)
        except (DatabaseConfigurationError, psycopg.Error, OSError) as exc:
            logging.error("Waitlist signup could not be stored (%s)", type(exc).__name__)
            return _json_response(start_response, "503 Service Unavailable", {"error": "We couldn't save your sign-up. Please try again.", "code": "storage_unavailable"})
        email_enabled = os.environ.get("WAITLIST_EMAIL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        if not email_enabled:
            logging.info("Waitlist signup %s stored; notification pending; SMTP remains paused.", signup_id)
            return _json_response(start_response, "201 Created", {"ok": True})

        try:
            claimed = begin_notification_attempt(signup_id)
        except (DatabaseConfigurationError, psycopg.Error, OSError) as exc:
            logging.error("Notification attempt for signup %s could not be recorded (%s).", signup_id, type(exc).__name__)
            return _json_response(start_response, "201 Created", {"ok": True})
        if not claimed:
            logging.error("Waitlist signup %s was stored but its notification could not be claimed.", signup_id)
            return _json_response(start_response, "201 Created", {"ok": True})
        try:
            _send_email(data)
        except Exception as exc:
            summary = _smtp_error_summary(exc)
            try:
                record_notification_result(signup_id, "failed", summary)
            except (DatabaseConfigurationError, psycopg.Error, OSError) as db_exc:
                logging.error("Notification status for signup %s could not be saved (%s).", signup_id, type(db_exc).__name__)
            logging.error("Waitlist notification for signup %s failed: %s", signup_id, summary)
        else:
            try:
                record_notification_result(signup_id, "sent")
            except (DatabaseConfigurationError, psycopg.Error, OSError) as db_exc:
                logging.error("Sent notification status for signup %s could not be saved (%s).", signup_id, type(db_exc).__name__)
        logging.info("Waitlist signup %s stored; visitor confirmation can be shown.", signup_id)
        return _json_response(start_response, "201 Created", {"ok": True})

    if method not in {"GET", "HEAD"}:
        return _response(start_response, "405 Method Not Allowed", b"Method not allowed")
    result = _serve_static(path, start_response, environ)
    if method == "HEAD" and result:
        # Keep the status/headers generated by the static handler but omit its body.
        return [b""]
    return result
