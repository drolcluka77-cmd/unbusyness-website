# Running on Replit

This is the Unbusyness website with a small Python WSGI backend for the waitlist email endpoint. Keep the existing HTML site structure.

## Preview

Use the **Start website** workflow (the Run button). It runs Gunicorn on port 5000 and serves the website and `/api/waitlist`.

```sh
gunicorn --bind 0.0.0.0:5000 --reload app:application
```

Open `/` for the welcome page, `/building-managers/`, `/hotels/`, `/home/`, or `/contractor/` for the waitlist pages. Demo pages are under `/demo/`.

Publishing uses an autoscale deployment running `gunicorn --bind 0.0.0.0:5000 --workers 2 app:application`.

## SMTP secrets

Configure these Replit Secrets for the environment where the app runs:

- `SMTP_HOST`
- `SMTP_PORT` (`465` for SSL or `587` for STARTTLS)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

Waitlist sign-ups are emailed to `info@unbusyness.com`; they are not saved in a database. Keep all SMTP credentials in Replit Secrets, never in source files. Fonts load from Google Fonts. See `README.md` for the page inventory and claims that need confirmation before going public.
