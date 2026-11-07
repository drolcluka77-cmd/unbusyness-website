# unbusyness.com: marketing site and waitlists

Static site, no build step. Every page is one self-contained HTML file (styles and scripts inline, fonts from Google Fonts).

## Pages

| Path | What it is |
|---|---|
| `/` | Welcome page: greeting with the cortisol meter, language choice (SL/EN), then "who are you" (resident, building manager, tradesperson with trade choice, hotel). Each choice shows a short sign-up form and links to the full page. |
| `/building-managers/` | Waitlist for building managers (upravniki), SL/EN |
| `/hotels/` | Waitlist for "Unbusyness for Hotels", SL/EN |
| `/home/` | Waitlist for Unbusyness Home (residents and homeowners): digital passport, reminders, reliable tradespeople, property passport, recommend-to-your-manager, SL/EN |
| `/demo/building-managers-desktop.html`, `-phone.html` | Interactive demo for building managers (SL, made-up data) |
| `/demo/hotels-desktop.html`, `-phone.html` | Interactive hotel demo (SL, made-up data) |
| `/demo/home-phone.html` | Interactive Unbusyness Home phone app demo, including the property passport (SL, made-up data) |

The welcome page links to the full pages in the `PAGES` object near the top of its script.

## Forms are not connected yet

Every form posts JSON to `WAITLIST_ENDPOINT` (a constant at the top of each page's script). It is empty, so the pages run in preview mode and say that nothing was sent. To go live, set it to a real endpoint, for example `/api/waitlist` on the Unbusyness app, which should store the sign-up and email info@unbusyness.com.

Each sign-up includes `segment` (`resident`, `manager`, `trade`, `hotel`, `residents`), the contact fields, `language` and `consent: true`.

## Design

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
