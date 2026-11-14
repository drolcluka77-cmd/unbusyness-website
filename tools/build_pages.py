#!/usr/bin/env python3
"""Builds the crawlable language versions of the site.

The pages at the root (index.html, contractor/, building-managers/, hotels/, home/, investors/)
are the sources: English in the HTML, Slovenian in each page's SL dictionary, switched by JavaScript.
Search engines and AI crawlers only see one language that way, so this script writes a static copy
of every page per language:

    /sl/<page>/index.html   Slovenian text already in the HTML
    /en/<page>/index.html   English text

Each copy gets its own <title>, meta description, canonical, hreflang links, Open Graph tags and
JSON-LD, and its SL/EN switch goes to the other copy. It also writes sitemap.xml, robots.txt and llms.txt.
The server (app.py) redirects the old addresses (/, /hotels/, ...) to the right language.

Run after every change to a source page:   python3 tools/build_pages.py   (needs node)
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://unbusyness.com"
LANGS = ("sl", "en")
EMAIL = "info@unbusyness.com"
PHONE = "+386 40 290 963"

# slug: source folder ("" = welcome page). og: image in media/og/. app: SoftwareApplication details (None = no app).
PAGES = [
    {
        "slug": "", "og": "welcome", "app": None,
        "title": {"sl": "Unbusyness – AI pisarniški pomočnik za upravnike, obrtnike in hotele",
                  "en": "Unbusyness – AI office assistant for building managers, trades and hotels"},
        "desc": {"sl": "Unbusyness sprejema klice in prijave okvar, pripravlja ponudbe in naloge ter vas neposredno poveže z izvajalci. Za upravnike stavb, obrtnike, hotele, gostitelje na Airbnbju in stanovalce.",
                 "en": "Unbusyness answers calls and fault reports, prepares quotes and jobs, and connects you directly with contractors. For building managers, trades, hotels, Airbnb hosts and residents."},
    },
    {
        "slug": "building-managers/", "og": "building-managers",
        "app": {"name": {"sl": "Unbusyness za upravnike stavb", "en": "Unbusyness for Building Managers"},
                "category": "BusinessApplication", "audience": {"sl": "Upravniki stavb", "en": "Building and property managers"}},
        "title": {"sl": "Aplikacija za upravnike stavb: prijave okvar in vzdrževanje | Unbusyness",
                  "en": "Software for building managers: fault reports and maintenance | Unbusyness"},
        "desc": {"sl": "Unbusyness je aplikacija za upravnike stavb: prijave okvar, zahtevki stanovalcev, zbori lastnikov, čiščenje ter redno in nujno vzdrževanje, z neposredno povezavo do izvajalcev.",
                 "en": "Unbusyness is an app for building and property managers: fault reports, resident requests, owners' meetings, cleaning, and planned and emergency maintenance, connected directly to your contractors."},
    },
    {
        "slug": "contractor/", "og": "contractor",
        "app": {"name": {"sl": "Unbusyness za obrtnike", "en": "Unbusyness for Trades"},
                "category": "BusinessApplication", "audience": {"sl": "Obrtniki in storitvena podjetja", "en": "Trades and home-service businesses"}},
        "title": {"sl": "AI-pomočnik za obrtnike: klici, ponudbe in računi | Unbusyness",
                  "en": "AI office manager for trades: calls, quotes and invoices | Unbusyness"},
        "desc": {"sl": "Pisarniški pomočnik z umetno inteligenco za vodoinštalaterje, električarje, serviserje ogrevanja in druge obrtnike: sprejema klice, pripravlja ponudbe in opominja na neplačane račune.",
                 "en": "The AI office manager for plumbers, electricians, heating engineers and other trades: it answers your calls, drafts your quotes and chases unpaid invoices."},
    },
    {
        "slug": "hotels/", "og": "hotels",
        "app": {"name": {"sl": "Unbusyness za hotele", "en": "Unbusyness for Hotels"},
                "category": "BusinessApplication", "audience": {"sl": "Hoteli in hotelske skupine", "en": "Hotels and hotel groups"}},
        "title": {"sl": "Naloge za hotelsko osebje prek WhatsAppa | Unbusyness za hotele",
                  "en": "Hotel task management on WhatsApp | Unbusyness for Hotels"},
        "desc": {"sl": "Unbusyness sporočila, glasovna sporočila in fotografije osebja na WhatsAppu spremeni v naloge z odgovorno osebo, ciljnim časom in samodejnim stopnjevanjem. Za gospodinjstvo, vzdrževanje in recepcijo.",
                 "en": "Unbusyness turns your staff's WhatsApp messages, voice notes and photos into tracked jobs with one owner, a target time and automatic escalation. For housekeeping, maintenance and front desk."},
    },
    {
        "slug": "hosts/", "og": "hosts",
        "app": {"name": {"sl": "Unbusyness za gostitelje", "en": "Unbusyness for Hosts"},
                "category": "BusinessApplication", "audience": {"sl": "Gostitelji na Airbnbju in Bookingu", "en": "Airbnb and short-term rental hosts"}},
        "title": {"sl": "AI-gostitelj za Airbnb apartmaje in neposredne rezervacije | Unbusyness",
                  "en": "AI host for Airbnb hosts, plus your own direct bookings | Unbusyness"},
        "desc": {"sl": "Unbusyness za gostitelje na Airbnbju in Bookingu: AI-gostitelj odgovarja gostom 24/7, težave spremeni v naloge za čiščenje in popravila, oznaka NFC/QR v apartmaju in lastna stran za neposredne rezervacije brez provizije platform.",
                 "en": "Unbusyness for Airbnb and short-term rental hosts: a 24/7 AI host that answers guests and turns problems into jobs for cleaning and repairs, an NFC/QR tag in every apartment, and your own site for commission-free direct bookings."},
    },
    {
        "slug": "home/", "og": "home",
        "app": {"name": {"sl": "Unbusyness Home", "en": "Unbusyness Home"},
                "category": "LifestyleApplication", "audience": {"sl": "Stanovalci in lastniki domov", "en": "Residents and homeowners"}},
        "title": {"sl": "Unbusyness Home: digitalni potni list doma, opomniki in zanesljivi mojstri",
                  "en": "Unbusyness Home: your home's digital passport, reminders and reliable tradespeople"},
        "desc": {"sl": "Vse o vašem stanovanju, hiši, avtu, aparatih in garancijah na enem mestu. Opomniki pred roki in zanesljiv mojster, ko se kaj pokvari.",
                 "en": "Everything about your flat, house, car, appliances and warranties in one place. Reminders before things are due, and a reliable tradesperson when something breaks."},
    },
    {
        "slug": "investors/", "og": "investors", "app": None,
        "title": {"sl": "Unbusyness za vlagatelje", "en": "Unbusyness for Investors"},
        "desc": {"sl": "Zahtevajte predstavitev Unbusyness za vlagatelje: pisarniški pomočnik z umetno inteligenco za storitvena podjetja in aplikacija Unbusyness Home.",
                 "en": "Request the Unbusyness investor presentation: an AI office assistant for service businesses and the Unbusyness Home app."},
    },
]
SLUGS = [p["slug"].rstrip("/") for p in PAGES if p["slug"]]
OG_LOCALE = {"sl": "sl_SI", "en": "en_GB"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def url(lang: str, slug: str) -> str:
    return f"{BASE}/{lang}/{slug}"


class Locator(HTMLParser):
    """Finds the start tag and content span of every element carrying data-t, data-t-ph or data-t-aria."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=False)
        self.starts = [0]
        for m in re.finditer("\n", text):
            self.starts.append(m.end())
        self.stack, self.found = [], []
        self.feed(text)
        self.close()

    def _off(self):
        line, col = self.getpos()
        return self.starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self._off()
        raw = self.get_starttag_text()
        item = {"tag": tag, "attrs": dict(attrs), "start": start, "cstart": start + len(raw), "raw": raw, "cend": None}
        if any(k.startswith("data-t") and k != "data-theme" for k in item["attrs"]):
            self.found.append(item)
        if tag not in VOID:
            self.stack.append(item)

    def handle_startendtag(self, tag, attrs):
        start = self._off()
        raw = self.get_starttag_text()
        item = {"tag": tag, "attrs": dict(attrs), "start": start, "cstart": start + len(raw), "raw": raw, "cend": None}
        if any(k.startswith("data-t") and k != "data-theme" for k in item["attrs"]):
            self.found.append(item)

    def handle_endtag(self, tag):
        pos = self._off()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                self.stack[i]["cend"] = pos
                del self.stack[i:]
                return


def set_attr(raw: str, name: str, value: str) -> str:
    value = html.escape(value, quote=True)
    pat = re.compile(r'(\s%s=)("[^"]*"|\'[^\']*\')' % re.escape(name))
    if pat.search(raw):
        return pat.sub(lambda m: f'{m.group(1)}"{value}"', raw, count=1)
    return raw[:-1].rstrip("/") + f' {name}="{value}"' + (" />" if raw.endswith("/>") else ">")


def translate(text: str, sl: dict) -> str:
    """Puts the Slovenian dictionary into the HTML, the same way each page's setLang('sl') does in the browser."""
    edits = []  # (start, end, replacement)
    for el in Locator(text).found:
        a, raw = el["attrs"], el["raw"]
        new_raw = raw
        if a.get("data-t-ph") and sl.get(a["data-t-ph"]):
            new_raw = set_attr(new_raw, "placeholder", sl[a["data-t-ph"]])
        if a.get("data-t-aria") and sl.get(a["data-t-aria"]):
            new_raw = set_attr(new_raw, "aria-label", sl[a["data-t-aria"]])
        if new_raw != raw:
            edits.append((el["start"], el["cstart"], new_raw))
        key = a.get("data-t")
        if key and sl.get(key) and isinstance(sl[key], str) and el["cend"] is not None:
            v = sl[key]
            body = v if ("data-html" in a or re.search(r"<\w", v)) else html.escape(v, quote=False)
            edits.append((el["cstart"], el["cend"], body))
    # An outer replacement wins over edits inside it (as in the browser, where it replaces the inner element).
    edits.sort(key=lambda e: (e[0], -e[1]))
    kept, last_end = [], -1
    for e in edits:
        if e[0] < last_end:
            continue
        kept.append(e)
        last_end = e[1]
    for start, end, rep in sorted(kept, key=lambda e: e[0], reverse=True):
        text = text[:start] + rep + text[end:]
    return text


def faq_pairs(text: str, lang: str, sl: dict) -> list[tuple[str, str]]:
    """Question/answer pairs from the visible FAQ (keys qa/qad, qb/qbd, ...)."""
    en = {}
    for el in Locator(text).found:
        k = el["attrs"].get("data-t")
        if k and el["cend"] is not None:
            en.setdefault(k, text[el["cstart"]:el["cend"]])
    src = sl if lang == "sl" else en
    out = []
    for c in "abcdefgh":
        q, a = src.get("q" + c), src.get("q" + c + "d")
        if q and a:
            clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
            out.append((clean(q), clean(a)))
    return out


def json_ld(page: dict, lang: str, faq: list) -> str:
    org = {"@type": "Organization", "@id": f"{BASE}/#organization", "name": "Unbusyness", "url": f"{BASE}/",
           "email": EMAIL, "telephone": PHONE, "contactPoint": {"@type": "ContactPoint", "email": EMAIL, "telephone": PHONE,
           "contactType": "customer support", "availableLanguage": ["Slovenian", "English"]}}
    site = {"@type": "WebSite", "@id": f"{BASE}/#website", "name": "Unbusyness", "url": f"{BASE}/", "inLanguage": ["sl", "en"],
            "publisher": {"@id": f"{BASE}/#organization"}}
    me = url(lang, page["slug"])
    web = {"@type": "WebPage", "@id": me + "#webpage", "url": me, "name": page["title"][lang], "description": page["desc"][lang],
           "inLanguage": lang, "isPartOf": {"@id": f"{BASE}/#website"}, "publisher": {"@id": f"{BASE}/#organization"}}
    graph = [org, site, web]
    if page["app"]:
        app = page["app"]
        graph.append({"@type": "SoftwareApplication", "@id": me + "#app", "name": app["name"][lang], "url": me,
                      "description": page["desc"][lang], "applicationCategory": app["category"], "operatingSystem": "Web",
                      "inLanguage": lang, "publisher": {"@id": f"{BASE}/#organization"},
                      "audience": {"@type": "Audience", "audienceType": app["audience"][lang]}})
        web["about"] = {"@id": me + "#app"}
    if faq:
        graph.append({"@type": "FAQPage", "@id": me + "#faq", "url": me, "inLanguage": lang,
                      "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return '<script type="application/ld+json">\n' + data.replace("</", "<\\/") + "\n</script>"


def head_block(page: dict, lang: str, faq: list) -> str:
    slug, other = page["slug"], ("en" if lang == "sl" else "sl")
    t, d = html.escape(page["title"][lang]), html.escape(page["desc"][lang])
    img = f"{BASE}/media/og/{page['og']}-{lang}.png"
    alt = {"sl": f"/sl/{slug}", "en": f"/en/{slug}"}
    nav = f"""<script>
(function () {{
  // This page is the {lang.upper()} version; the SL/EN switch opens the other version.
  var L = "{lang}", A = {json.dumps(alt)};
  var keep = function (l) {{ try {{ localStorage.setItem("ub-lang", l); }} catch (e) {{}} document.cookie = "ub-lang=" + l + ";path=/;max-age=31536000;samesite=lax"; }};
  keep(L);
  var p = new URLSearchParams(location.search), q = p.get("lang");
  if ((q === "sl" || q === "en") && q !== L) {{ p.delete("lang"); var s = p.toString(); location.replace(A[q] + (s ? "?" + s : "") + location.hash); }}
  document.addEventListener("click", function (e) {{
    var b = e.target.closest && e.target.closest("[data-lang]"); if (!b) return;
    var l = b.getAttribute("data-lang"); if (!A[l]) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (l === L) return;
    keep(l); location.href = A[l] + location.search + location.hash;
  }}, true);
}})();
</script>"""
    return "\n".join([
        f"<title>{t}</title>",
        f'<meta name="description" content="{d}">',
        f'<link rel="canonical" href="{url(lang, slug)}">',
        f'<link rel="alternate" hreflang="sl" href="{url("sl", slug)}">',
        f'<link rel="alternate" hreflang="en" href="{url("en", slug)}">',
        f'<link rel="alternate" hreflang="x-default" href="{BASE}/{slug}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Unbusyness">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{url(lang, slug)}">',
        f'<meta property="og:image" content="{img}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}">',
        f'<meta property="og:locale:alternate" content="{OG_LOCALE[other]}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:description" content="{d}">',
        f'<meta name="twitter:image" content="{img}">',
        json_ld(page, lang, faq),
        nav,
    ])


def build_page(page: dict, lang: str) -> str:
    src_path = ROOT / page["slug"] / "index.html"
    text = src_path.read_text(encoding="utf-8")
    sl = json.loads(subprocess.run(["node", str(ROOT / "tools" / "extract_dict.js"), str(src_path)],
                                   check=True, capture_output=True, text=True).stdout)
    faq = faq_pairs(text, lang, sl)
    # Language-only blocks (<!--l:sl--> ... <!--/l-->): keep this language's, drop the other's.
    other = "en" if lang == "sl" else "sl"
    text = re.sub(r"<!--l:%s-->.*?<!--/l-->\n?" % other, "", text, flags=re.S)
    text = re.sub(r"<!--l:%s-->(.*?)<!--/l-->" % lang, r"\1", text, flags=re.S)
    if lang == "sl" and page["slug"]:
        text = translate(text, sl)
    text = re.sub(r"<html\b[^>]*>", f'<html lang="{lang}">', text, count=1)
    # Start in this language, whatever the browser or an earlier visit said.
    text = re.sub(r"^setLang\((?:start|q === \"sl\" \|\| q === \"en\" \? q : start)\);$", f'setLang("{lang}");', text, flags=re.M)
    text = text.replace('try { lang = localStorage.getItem("ub-lang") || lang; } catch {}',
                        f'try {{ lang = localStorage.getItem("ub-lang") || lang; }} catch {{}}\nlang = "{lang}";')
    text = re.sub(r'\s*document\.title = t\("docTitle"\);', "", text)
    # Internal links go to the same language.
    text = re.sub(r'(?<=["\'])/(%s)/' % "|".join(map(re.escape, SLUGS)), rf"/{lang}/\1/", text)
    text = re.sub(r'(?<=["\'])/(?=["\'#?])', f"/{lang}/", text)
    # Head: drop the source's title/description, add ours right after the viewport tag.
    text = re.sub(r"<title>.*?</title>\n?", "", text, count=1, flags=re.S)
    text = re.sub(r'<meta name="description"[^>]*>\n?', "", text, count=1)
    m = re.search(r'<meta name="viewport"[^>]*>\n', text)
    text = text[:m.end()] + head_block(page, lang, faq) + "\n" + text[m.end():]
    banner = "<!-- Generated by tools/build_pages.py from /%sindex.html. Edit the source page, then run the script. -->\n" % page["slug"]
    return text.replace("<!doctype html>\n", "<!doctype html>\n" + banner, 1)


def sitemap() -> str:
    rows = []
    for p in PAGES:
        for lang in LANGS:
            alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{url(l, p["slug"])}"/>' for l in LANGS)
            alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/{p["slug"]}"/>'
            rows.append(f"  <url>\n    <loc>{url(lang, p['slug'])}</loc>{alts}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(rows) + "\n</urlset>\n")


ROBOTS = f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /demo/

Sitemap: {BASE}/sitemap.xml
"""

LLMS = f"""# Unbusyness

> Unbusyness is AI software for service businesses in Slovenia and the wider Central and Eastern European region. It answers calls and fault reports, turns them into jobs, prepares quotes and invoices, and connects customers directly with contractors. Unbusyness Home is the companion app for residents and homeowners. Pages are available in Slovenian (/sl/) and English (/en/).

Unbusyness is in early access: each product has a waitlist, and the first building managers and hotels are set up by the Unbusyness team and use it free during the pilot.

## Products

- [Unbusyness for building managers]({BASE}/en/building-managers/): fault reports, resident requests, owners' meetings, cleaning, and planned and emergency maintenance, connected directly to contractors. Residents call, text or email as today; no app needed. Slovenian: [{BASE}/sl/building-managers/]({BASE}/sl/building-managers/)
- [Unbusyness for trades]({BASE}/en/contractor/): an AI office manager for plumbers, electricians, heating engineers and other trades. It answers calls 24/7, drafts quotes and chases unpaid invoices; prices and anything sent to customers need the owner's approval. Slovenian: [{BASE}/sl/contractor/]({BASE}/sl/contractor/)
- [Unbusyness for hotels]({BASE}/en/hotels/): staff keep using WhatsApp; messages, voice notes and photos become jobs with one owner, a target time and automatic escalation for housekeeping, maintenance and front desk. Slovenian: [{BASE}/sl/hotels/]({BASE}/sl/hotels/)
- [Unbusyness for Airbnb hosts]({BASE}/en/hosts/): a 24/7 AI host that answers guests in their language and turns reported problems into jobs for cleaners and maintenance; an NFC/QR tag in every apartment with the digital guide; and the host's own booking website optimised for Google and AI search, for direct bookings without platform commission. Pilot prices: €12 per apartment per month (minimum €49), own booking site +€99 per month. Slovenian: [{BASE}/sl/hosts/]({BASE}/sl/hosts/)
- [Unbusyness Home]({BASE}/en/home/): a digital passport for a flat, house, car, appliances and warranties, with reminders before things are due and reliable, punctual tradespeople when something breaks. Slovenian: [{BASE}/sl/home/]({BASE}/sl/home/)

## Company

- [Start page]({BASE}/en/) · [Slovenian]({BASE}/sl/)
- [Investors]({BASE}/en/investors/)
- Contact: {EMAIL}, {PHONE}
"""


def main():
    for page in PAGES:
        for lang in LANGS:
            out = ROOT / lang / page["slug"] / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(build_page(page, lang), encoding="utf-8")
            print("wrote", out.relative_to(ROOT))
    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    (ROOT / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (ROOT / "llms.txt").write_text(LLMS, encoding="utf-8")
    print("wrote sitemap.xml, robots.txt, llms.txt")


if __name__ == "__main__":
    main()
