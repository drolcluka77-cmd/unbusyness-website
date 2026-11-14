# unbusyness.com: marketing site and waitlists

Every page is one self-contained HTML file (styles and scripts inline, fonts from Google Fonts), with no build step. A small Python app (`app.py`, run with Gunicorn on Replit) serves the pages and the waitlist endpoint `/api/waitlist`; see "Waitlist submissions" below and `replit.md`. Videos are served with byte ranges so they play in Safari on iPhone and Mac.

Tests: `python -m unittest tests.test_waitlist_api`.

## Pages

| Path | What it is |
|---|---|
| `/` | Welcome page: greeting with the cortisol meter and an SL/EN switch in the header, then "who are you". Each choice opens its own page (resident → `/home/`, building manager → `/building-managers/`, tradesperson → `/contractor/`, hotel → `/hotels/`). |
| `/building-managers/` | Waitlist for building managers (upravniki), SL/EN |
| `/hotels/` | Waitlist for "Unbusyness for Hotels", plus a GEO for hotels section with prices (from €399 a month with 20 rooms, then €12 per room; website from €1,499 one-off), SL/EN |
| `/manager` | Redirects to `/building-managers/` (the address used on the old unbusyness.com). |
| `/contractor/` | Waitlist for tradespeople (plumbers, HVAC, electricians, other trades): hero sign-up, why + 30-second film, how it works, six features (three with short films), final sign-up. SL/EN. `/contractor/sl/` redirects to the Slovenian version. |
| `/investors/` | Request for the investor presentation (email, phone). Linked from the footer of the waitlist pages. |
| `/hosts/` | Waitlist for "Unbusyness for Hosts" (Airbnb and short-term rental hosts): AI host chat, platform fees, three pillars (AI host, NFC/QR tag per apartment, direct bookings + AI search), how the tag works, savings estimate, pilot prices (AI host €12 per apartment per month, minimum €49; GEO and direct bookings from €149 a month with 3 apartments, then €35 each; website from €999 one-off), form (segment `hosts`), FAQ, and a "Why GEO matters" section (guests ask AI where to stay → AI recommends you by name → direct booking without platform commission). SL/EN |
| `/home/` | Waitlist for Unbusyness Home (residents and homeowners): digital passport, reminders, reliable tradespeople, property passport, recommend-to-your-manager, SL/EN |
| `/demo/building-managers-desktop.html`, `-phone.html` | Interactive demo for building managers (made-up data) |
| `/demo/hotels-desktop.html`, `-phone.html` | Interactive hotel demo (made-up data) |
| `/demo/hosts-phone.html` | Interactive phone demo for Airbnb hosts: overnight summary, guest chats handled by the AI host, jobs, apartments with a preview of the guest page the NFC/QR tag opens, direct bookings and AI visibility (made-up data) |
| `/demo/home-phone.html` | Interactive Unbusyness Home phone app demo, including the property passport (made-up data) |
| `/demo/trades-desktop.html`, `trades-phone.html` | Unbusyness Business demos for tradespeople (English only, made-up data). The old addresses `/unbusyness-demo.html` and `/unbusyness-mobile-demo.html` redirect here. |
| `/media/` | Preview videos and poster images used on `/contractor/`. `unbusyness-preview.mp4` is the 30-second brand film (plumber under a sink, call, job, logo). `unbusyness-home-preview.mp4` is the 26-second Home film, also shown on `/home/`. `unbusyness-receptionist-preview.mp4`, `-crew-preview.mp4` and `-care-plan-preview.mp4` are the three 30-second feature films. |

The five waitlist pages (`/contractor/`, `/building-managers/`, `/hotels/`, `/hosts/`, `/home/`) share a row of audience tabs under the header (For trades · For building managers · For hotels · For Airbnb hosts · For your home) so visitors can switch; on phones it becomes a two-column grid.

Every demo except the trades demos has a Slovenian file and an English `-en.html` file; a small bar in each demo links back to its waitlist and switches language.

The welcome page links to the full pages in the `PAGES` object near the top of its script.

## Languages, search engines and AI crawlers

The root pages (`index.html`, `contractor/`, `building-managers/`, `hotels/`, `home/`, `investors/`) are the **sources**: English in the HTML, Slovenian in each page's `SL` dictionary. Visitors never see them directly. `tools/build_pages.py` writes a static copy per language, and those are what is served and indexed:

| Path | What it is |
|---|---|
| `/sl/…`, `/en/…` | Generated pages with the text already in the HTML, their own title, meta description, canonical, `hreflang` (sl, en, x-default), Open Graph/Twitter tags and JSON-LD (Organization, WebSite, WebPage, SoftwareApplication, FAQPage where the page has an FAQ). The SL/EN switch opens the other copy. **Do not edit them; edit the source and rebuild.** |
| `/`, `/hotels/`, … | `app.py` answers with a redirect to `/sl/…` or `/en/…`: `?lang=` first, then the visitor's last choice (cookie `ub-lang`), then the browser language; English by default. |
| `/sitemap.xml`, `/robots.txt`, `/llms.txt` | Written by the same script. `robots.txt` keeps `/api/` and `/demo/` out of search. |
| `/media/og/` | 1200×630 sharing images, drawn by `node tools/og_images.cjs` (needs Playwright). |

After changing any source page (or the titles and descriptions at the top of `tools/build_pages.py`), run:

```sh
python3 tools/build_pages.py
```

It needs `node` (used to read each page's Slovenian dictionary). Text that exists in one language only can be wrapped in `<!--l:sl-->…<!--/l-->` / `<!--l:en-->…<!--/l-->` (used for the "What is Unbusyness?" text on the welcome page).

## Waitlist submissions

Every valid form submission is saved in the Replit PostgreSQL database before the visitor sees confirmation. The schema is documented in `db/schema.sql`; the full form payload, consent, and email-notification status are stored in `public.waitlist_signups`. SMTP notifications are currently paused (`WAITLIST_EMAIL_ENABLED=false`) until NEOSERV responds; no SMTP login is attempted while paused. New submissions stay `pending` and can be reviewed in the Replit database pane.

After NEOSERV confirms the SMTP setup and the user authorizes resuming delivery, notifications can be enabled for new submissions. Older pending submissions remain visible in the database list for follow-up. SMTP host, port, username, and password stay in Replit Secrets (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`).

The endpoint accepts `residents`, `building_managers`, `tradespeople`, `hotels`, and `investors`, plus the welcome page's `resident`, `manager`, `trade`, and `hotel` segments. Replies to notifications go to the person who submitted the form.

## Design

- Contractor page: same colours, Plus Jakarta Sans for everything (as on the original unbusyness.com/contractor).
- Building managers, hotels and the welcome page: evergreen `#1F4D45`, sand, apricot `#E8915F`; Fraunces headings and Plus Jakarta Sans body text.
- Unbusyness Home: blush background `#F8E8DE`, terracotta `#B0582F`, white rounded cards, Plus Jakarta Sans for everything.
- Every page has light and dark mode and works at phone width.

## Check before going public

These claims are on the pages but are not decided or verified yet:
- Free pilot or setup by the team (building managers and hotels pages)
- Supported languages and EU data storage
- Setup times ("10 minutes", etc.)
- Tradesperson vetting and punctuality ratings (Home)
- The pages say pricing is not decided yet. Keep that until it is.

Do not use the name of the hotel brochure that inspired the hotels page.

Contact in the footers: info@unbusyness.com · +386 40 290 963
