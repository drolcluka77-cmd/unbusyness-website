# unbusyness.com: marketing site and waitlists

Static site, no build step. Every page is one self-contained HTML file (styles and scripts inline, fonts from Google Fonts).

## Pages

| Path | What it is |
|---|---|
| `/` | Welcome page: greeting with the cortisol meter and an SL/EN switch in the header, then "who are you". Each choice opens its own page (resident → `/home/`, building manager → `/building-managers/`, tradesperson → `/contractor/`, hotel → `/hotels/`). |
| `/building-managers/` | Waitlist for building managers (upravniki), SL/EN |
| `/hotels/` | Waitlist for "Unbusyness for Hotels", SL/EN |
| `/manager` | Redirects to `/building-managers/` (the address used on the old unbusyness.com). |
| `/contractor/` | Waitlist for tradespeople (plumbers, HVAC, electricians, other trades): hero sign-up, why + 30-second film, how it works, six features (three with short films), final sign-up. SL/EN. `/contractor/sl/` redirects to the Slovenian version. |
| `/investors/` | Request for the investor presentation (email, phone). Linked from the footer of the waitlist pages. |
| `/home/` | Waitlist for Unbusyness Home (residents and homeowners): digital passport, reminders, reliable tradespeople, property passport, recommend-to-your-manager, SL/EN |
| `/demo/building-managers-desktop.html`, `-phone.html` | Interactive demo for building managers (made-up data) |
| `/demo/hotels-desktop.html`, `-phone.html` | Interactive hotel demo (made-up data) |
| `/demo/home-phone.html` | Interactive Unbusyness Home phone app demo, including the property passport (made-up data) |
| `/demo/trades-desktop.html`, `trades-phone.html` | Unbusyness Business demos for tradespeople (English only, made-up data). The old addresses `/unbusyness-demo.html` and `/unbusyness-mobile-demo.html` redirect here. |
| `/media/` | Preview videos and poster images used on `/contractor/`. `unbusyness-preview.mp4` is the 30-second brand film (plumber under a sink, call, job, logo). `unbusyness-home-preview.mp4` is the 26-second Home film, also shown on `/home/`. `unbusyness-receptionist-preview.mp4`, `-crew-preview.mp4` and `-care-plan-preview.mp4` are the three 30-second feature films. |

The four waitlist pages (`/contractor/`, `/building-managers/`, `/hotels/`, `/home/`) share a row of audience tabs under the header (For trades · For building managers · For hotels · For your home) so visitors can switch; on phones it becomes a 2×2 grid.

Every demo except the trades demos has a Slovenian file and an English `-en.html` file; a small bar in each demo links back to its waitlist and switches language.

The welcome page links to the full pages in the `PAGES` object near the top of its script.

## Forms are not connected yet

Every form posts JSON to `WAITLIST_ENDPOINT` (a constant at the top of each page's script). It is empty, so the pages run in preview mode and say that nothing was sent. To go live, set it to a real endpoint, for example `/api/waitlist` on the Unbusyness app, which should store the sign-up and email info@unbusyness.com.

Each sign-up includes `segment` (`residents`, `building_managers`, `tradespeople`, `hotels`; the welcome page sends `resident`, `manager`, `trade`, `hotel`), the contact fields, `language` and `consent: true`. The investor request on `/investors/` sends `segment: "investors"` with email and phone; the endpoint has to accept that list too.

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
