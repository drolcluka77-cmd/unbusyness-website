# unbusyness.com: marketing site and waitlists

Static site, no build step. Every page is one self-contained HTML file (styles and scripts inline, fonts from Google Fonts).

## Pages

| Path | What it is |
|---|---|
| `/` | Welcome page: greeting with the cortisol meter and an SL/EN switch in the header, then "who are you". Each choice opens its own page (resident → `/home/`, building manager → `/building-managers/`, tradesperson → `/contractor/`, hotel → `/hotels/`). |
| `/building-managers/` | Waitlist for building managers (upravniki), SL/EN |
| `/hotels/` | Waitlist for "Unbusyness for Hotels", SL/EN |
| `/contractor/` | Waitlist for tradespeople (plumbers, HVAC, electricians, other trades): Unbusyness Business, 30-second videos, building managers and Home teasers, investor request, SL/EN. `/contractor/sl/` redirects to the Slovenian version. |
| `/home/` | Waitlist for Unbusyness Home (residents and homeowners): digital passport, reminders, reliable tradespeople, property passport, recommend-to-your-manager, SL/EN |
| `/demo/building-managers-desktop.html`, `-phone.html` | Interactive demo for building managers (made-up data) |
| `/demo/hotels-desktop.html`, `-phone.html` | Interactive hotel demo (made-up data) |
| `/demo/home-phone.html` | Interactive Unbusyness Home phone app demo, including the property passport (made-up data) |
| `/demo/trades-desktop.html`, `trades-phone.html` | Unbusyness Business demos for tradespeople (English only, made-up data). The old addresses `/unbusyness-demo.html` and `/unbusyness-mobile-demo.html` redirect here. |
| `/media/` | Preview videos and poster images used on `/contractor/`. `unbusyness-preview.mp4` is the 30-second brand film (plumber under a sink, call, job, logo). The other four (receptionist, crew, care plan, Home) still have to be copied over from the old site. |

Every demo except the trades demos has a Slovenian file and an English `-en.html` file; a small bar in each demo links back to its waitlist and switches language.

The welcome page links to the full pages in the `PAGES` object near the top of its script.

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
