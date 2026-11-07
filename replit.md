# Running on Replit

This is the imported Unbusyness static website. Preserve its existing HTML structure; no framework, package installation, or build step is required.

## Preview

Use the **Start website** workflow (the Run button). It runs:

```sh
python3 -m http.server 5000 --bind 0.0.0.0
```

Run from the repository root. Open `/` for the welcome page, `/building-managers/`, `/hotels/`, or `/home/` for the waitlist pages, and the HTML files under `/demo/` for the interactive demos.

The Python standard-library server is for development preview, not a production server. For publishing, serve the static site with an appropriate static hosting configuration.

## External services

No secrets or external services are required to preview the site. Fonts load from Google Fonts.

Waitlist forms intentionally remain in preview mode: `WAITLIST_ENDPOINT` is empty in each marketing page. No sign-ups are sent or saved. Connecting real sign-ups requires a real endpoint and storage/email service; do not insert a dummy URL or credentials.

See `README.md` for the page inventory and marketing claims that must be confirmed before going public.
