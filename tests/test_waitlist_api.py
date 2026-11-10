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
        save_signup.assert_not_called()

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


if __name__ == "__main__":
    unittest.main()
