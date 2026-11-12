# Running on Replit

This is the Unbusyness website with a small Python WSGI backend for the waitlist email endpoint. Keep the existing HTML site structure.

## Preview

Use the **Start website** workflow (the Run button). It runs Gunicorn on port 5000 and serves the website and `/api/waitlist`.

```sh
gunicorn --bind 0.0.0.0:5000 --reload app:application
```

Open `/` for the welcome page, `/building-managers/`, `/hotels/`, `/home/`, or `/contractor/` for the waitlist pages; they redirect to the Slovenian (`/sl/...`) or English (`/en/...`) copy. Demo pages are under `/demo/`.

The `/sl/` and `/en/` folders are generated. After editing a root page (`index.html`, `contractor/index.html`, ...), run `python3 tools/build_pages.py` and commit the result; see "Languages, search engines and AI crawlers" in `README.md`.

Publishing uses an autoscale deployment running `gunicorn --bind 0.0.0.0:5000 --workers 2 app:application`.

## Waitlist data and email

Valid waitlist submissions are saved in the Replit PostgreSQL database first. Visitors see confirmation after the database write succeeds. The schema is documented in `db/schema.sql`; the `public.waitlist_signups` table contains the submitted fields, consent, and notification status. Use the Replit database pane to review pending submissions; do not expose this personal data through an unauthenticated public route.

Publish after schema changes so Replit applies the development table to the production database. Development and production records are separate.

SMTP is explicitly paused until NEOSERV responds. Keep the shared environment variable `WAITLIST_EMAIL_ENABLED` set to `false`; do not attempt SMTP logins or retry notifications automatically before then. The four SMTP credentials remain in Replit Secrets and must never be written to source files.

After NEOSERV confirms the SMTP settings and the user authorizes resuming delivery, notifications may be enabled for new sign-ups. Older pending records remain visible in the Replit database pane for follow-up. Email failures are recorded on the signup and in logs, but never prevent the visitor's confirmation after a successful database save.

See `README.md` for the page inventory and claims that need confirmation before going public. Fonts load from Google Fonts.
