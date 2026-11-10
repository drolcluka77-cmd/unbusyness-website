"""Persistence helpers for waitlist submissions and notification state."""

from __future__ import annotations

import json
import os

import psycopg


class DatabaseConfigurationError(RuntimeError):
    pass


def _connect():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")
    return psycopg.connect(database_url, connect_timeout=5)


def check_database() -> None:
    with _connect() as connection:
        connection.execute("SELECT 1").fetchone()


def save_signup(data: dict) -> int:
    with _connect() as connection:
        row = connection.execute(
            """
            INSERT INTO public.waitlist_signups
                (segment, email, payload, consent, notification_status)
            VALUES (%s, %s, %s::jsonb, %s, 'pending')
            RETURNING id
            """,
            (
                data["segment"],
                data["email"],
                json.dumps(data, ensure_ascii=False),
                data["consent"],
            ),
        ).fetchone()
    return row[0]


def begin_notification_attempt(signup_id: int) -> bool:
    with _connect() as connection:
        row = connection.execute(
            """
            UPDATE public.waitlist_signups
            SET notification_status = 'sending',
                notification_attempts = notification_attempts + 1,
                notification_attempted_at = NOW(),
                notification_error = NULL
            WHERE id = %s
              AND notification_status = 'pending'
            RETURNING id
            """,
            (signup_id,),
        ).fetchone()
    return row is not None


def record_notification_result(signup_id: int, status: str, error: str | None = None) -> None:
    if status not in {"sent", "failed"}:
        raise ValueError("status must be sent or failed")
    with _connect() as connection:
        connection.execute(
            """
            UPDATE public.waitlist_signups
            SET notification_status = %s,
                notification_sent_at = CASE WHEN %s = 'sent' THEN NOW() ELSE NULL END,
                notification_error = %s
            WHERE id = %s
              AND notification_status = 'sending'
            """,
            (status, status, error, signup_id),
        )
