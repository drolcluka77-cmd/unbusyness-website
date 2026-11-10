import io
import json
import os
import smtplib
import unittest
from unittest.mock import MagicMock, patch

import psycopg

from app import application
from waitlist_db import save_signup


class WaitlistApiTests(unittest.TestCase):
    def setUp(self):
        self.request_number = 0
        from app import _request_times
        _request_times.clear()

    def call_api(self, payload):
        self.request_number += 1
        body = json.dumps(payload).encode("utf-8")
        environ = {
            "PATH_INFO": "/api/waitlist",
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
            "HTTP_HOST": "example.test",
            "HTTP_ORIGIN": "https://example.test",
            "REMOTE_ADDR": f"198.51.100.{self.request_number}",
        }
        result = {}

        def start_response(status, headers):
            result["status"] = status

        result["body"] = b"".join(application(environ, start_response))
        return result

    @staticmethod
    def valid_payload(**overrides):
        return {
            "segment": "residents",
            "email": "resident@example.invalid",
            "consent": True,
            **overrides,
        }

    def test_paused_email_stores_submission_and_confirms_visitor(self):
        with (
            patch.dict(os.environ, {"WAITLIST_EMAIL_ENABLED": "false"}),
            patch("app.save_signup", return_value=42) as save_signup,
            patch("app.begin_notification_attempt") as begin_attempt,
            patch("app._send_email") as send_email,
        ):
            response = self.call_api(self.valid_payload())

        self.assertEqual(response["status"], "201 Created")
        self.assertEqual(json.loads(response["body"]), {"ok": True})
        save_signup.assert_called_once()
        begin_attempt.assert_not_called()
        send_email.assert_not_called()

    def test_email_failure_does_not_cancel_saved_signup_or_confirmation(self):
        with (
            patch.dict(os.environ, {"WAITLIST_EMAIL_ENABLED": "true"}),
            patch("app.save_signup", return_value=43),
            patch("app.begin_notification_attempt", return_value=True),
            patch("app._send_email", side_effect=smtplib.SMTPAuthenticationError(535, b"rejected")),
            patch("app.record_notification_result") as record_result,
        ):
            response = self.call_api(self.valid_payload())

        self.assertEqual(response["status"], "201 Created")
        self.assertEqual(json.loads(response["body"]), {"ok": True})
        record_result.assert_called_once_with(43, "failed", "SMTPAuthenticationError (535)")

    def test_database_failure_does_not_claim_success_or_send_email(self):
        with (
            patch("app.save_signup", side_effect=psycopg.OperationalError("database unavailable")),
            patch("app._send_email") as send_email,
        ):
            response = self.call_api(self.valid_payload())

        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(json.loads(response["body"])["code"], "storage_unavailable")
        send_email.assert_not_called()

    def test_honeypot_is_accepted_without_database_or_smtp(self):
        with (
            patch("app.save_signup") as save_signup,
            patch("app._send_email") as send_email,
        ):
            response = self.call_api(self.valid_payload(website="bot"))

        self.assertEqual(response["status"], "200 OK")
        save_signup.assert_not_called()
        send_email.assert_not_called()

    def test_consent_is_required_before_storage(self):
        with patch("app.save_signup") as save_signup:
            response = self.call_api(self.valid_payload(consent=False))

        self.assertEqual(response["status"], "400 Bad Request")
        self.assertEqual(json.loads(response["body"])["code"], "consent_required")
        save_signup.assert_not_called()

    def test_home_form_payload_is_accepted(self):
        payload = self.valid_payload(
            name="Test resident", phone="", city="Test city", home="flat-own",
            managerUsesUnbusyness="no", manager="Test manager", contactManager=True,
            address="Test address", wants=["repairs"], language="sl",
        )
        with (
            patch.dict(os.environ, {"WAITLIST_EMAIL_ENABLED": "false"}),
            patch("app.save_signup", return_value=44) as store,
            patch("app._send_email") as send_email,
        ):
            response = self.call_api(payload)
        self.assertEqual(response["status"], "201 Created")
        store.assert_called_once_with(payload)
        send_email.assert_not_called()

    def test_rejected_fields_return_specific_codes_without_storage(self):
        with patch("app.save_signup") as store:
            for fields, code in [
                ({"email": "not-an-email"}, "invalid_email"),
                ({"address": "x" * 2001}, "field_too_long"),
                ({"segment": "unknown"}, "invalid_list"),
            ]:
                with self.subTest(code=code):
                    response = self.call_api(self.valid_payload(**fields))
                    self.assertEqual(response["status"], "400 Bad Request")
                    self.assertEqual(json.loads(response["body"])["code"], code)
            store.assert_not_called()

    def test_rate_limit_returns_specific_code_without_storage_or_smtp(self):
        with (
            patch("app._is_rate_limited", return_value=True),
            patch("app.save_signup") as store,
            patch("app._send_email") as send_email,
        ):
            response = self.call_api(self.valid_payload())
        self.assertEqual(response["status"], "429 Too Many Requests")
        self.assertEqual(json.loads(response["body"])["code"], "rate_limited")
        store.assert_not_called()
        send_email.assert_not_called()

    def test_database_helper_uses_parameterized_insert(self):
        payload = self.valid_payload(name="A test applicant")
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.fetchone.return_value = (84,)

        with patch("waitlist_db._connect", return_value=connection):
            signup_id = save_signup(payload)

        self.assertEqual(signup_id, 84)
        query, params = connection.execute.call_args.args
        self.assertIn("INSERT INTO public.waitlist_signups", query)
        self.assertIn("%s", query)
        self.assertEqual(params[0], payload["segment"])
        self.assertEqual(params[1], payload["email"])
        self.assertEqual(json.loads(params[2]), payload)
        self.assertIs(params[3], True)



class StaticFileTests(unittest.TestCase):
    def get(self, path, range_header=None):
        environ = {"PATH_INFO": path, "REQUEST_METHOD": "GET", "HTTP_HOST": "example.test"}
        if range_header:
            environ["HTTP_RANGE"] = range_header
        result = {}

        def start_response(status, headers):
            result["status"] = status
            result["headers"] = headers

        result["body"] = b"".join(application(environ, start_response))
        return result

    @staticmethod
    def header(response, name):
        values = [value for key, value in response["headers"] if key.lower() == name.lower()]
        return values

    def test_video_byte_range_for_safari(self):
        full = self.get("/media/unbusyness-preview.mp4")
        self.assertEqual(full["status"], "200 OK")
        self.assertEqual(self.header(full, "Accept-Ranges"), ["bytes"])
        size = len(full["body"])

        first = self.get("/media/unbusyness-preview.mp4", "bytes=0-1")
        self.assertEqual(first["status"], "206 Partial Content")
        self.assertEqual(first["body"], full["body"][:2])
        self.assertEqual(self.header(first, "Content-Range"), [f"bytes 0-1/{size}"])

        open_ended = self.get("/media/unbusyness-preview.mp4", "bytes=100-")
        self.assertEqual(open_ended["body"], full["body"][100:])

        suffix = self.get("/media/unbusyness-preview.mp4", "bytes=-10")
        self.assertEqual(suffix["body"], full["body"][-10:])

        too_far = self.get("/media/unbusyness-preview.mp4", f"bytes={size}-")
        self.assertEqual(too_far["status"], "416 Range Not Satisfiable")

    def test_one_cache_header_per_response(self):
        video = self.get("/media/unbusyness-preview.mp4")
        self.assertEqual(self.header(video, "Cache-Control"), ["public, max-age=86400"])
        page = self.get("/contractor/")
        self.assertEqual(page["status"], "200 OK")
        self.assertEqual(self.header(page, "Cache-Control"), ["no-cache"])

    def test_source_and_hidden_files_are_not_served(self):
        for path in ("/app.py", "/waitlist_db.py", "/.replit", "/README.md", "/db/schema.sql", "/pyproject.toml", "/tests/test_waitlist_api.py", "/../etc/passwd"):
            self.assertEqual(self.get(path)["status"], "404 Not Found", path)

    def test_new_pages_are_served(self):
        for path in ("/investors/", "/manager/", "/contractor/sl/"):
            self.assertEqual(self.get(path)["status"], "200 OK", path)


if __name__ == "__main__":
    unittest.main()
