// Draws the 1200x630 social sharing images in media/og/ (one per page and language).
// Usage: node tools/og_images.cjs   (needs Playwright with Chromium)
const { chromium } = require('playwright');
const path = require('path');
const OUT = path.join(__dirname, '..', 'media', 'og');
const CARDS = {
  welcome: { sl: ['unbusyness.com', 'AI pisarniški pomočnik za upravnike, obrtnike in hotele', 'Klici, prijave okvar, ponudbe in izvajalci na enem mestu.'],
             en: ['unbusyness.com', 'AI office assistant for building managers, trades and hotels', 'Calls, fault reports, quotes and contractors in one place.'] },
  'building-managers': { sl: ['Za upravnike stavb', 'Aplikacija za upravnike stavb', 'Prijave okvar, stanovalci, čiščenje in vzdrževanje, povezano z izvajalci.'],
                         en: ['For building managers', 'Software for building managers', 'Fault reports, residents, cleaning and maintenance, connected to contractors.'] },
  contractor: { sl: ['Za obrtnike', 'AI-pomočnik za obrtnike', 'Klici, ponudbe in računi, urejeni, medtem ko delate.'],
                en: ['For trades', 'The AI office manager for trades', 'Calls, quotes and invoices handled while you work.'] },
  hotels: { sl: ['Za hotele', 'Naloge za hotelsko osebje prek WhatsAppa', 'Vsaka prošnja z odgovorno osebo, ciljnim časom in stopnjevanjem.'],
            en: ['For hotels', 'Hotel tasks on WhatsApp', 'Every request with one owner, a target time and escalation.'] },
  home: { sl: ['Unbusyness Home', 'Digitalni potni list vašega doma', 'Opomniki pred roki in zanesljiv mojster, ko se kaj pokvari.'],
          en: ['Unbusyness Home', "Your home's digital passport", 'Reminders before things are due, and a reliable tradesperson when something breaks.'] },
  investors: { sl: ['Za vlagatelje', 'Unbusyness za vlagatelje', 'AI pisarniški pomočnik za storitvena podjetja.'],
               en: ['For investors', 'Unbusyness for investors', 'An AI office assistant for service businesses.'] },
};
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const page = ([eyebrow, title, sub]) => `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;background:#173D37;color:#F3F6F4;font-family:'Inter',sans-serif;position:relative;overflow:hidden}
.glow{position:absolute;right:-160px;top:-160px;width:620px;height:620px;border-radius:50%;background:radial-gradient(circle,rgba(242,165,122,.35),transparent 68%)}
.in{position:absolute;inset:64px 72px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:16px;font-weight:800;font-size:34px;letter-spacing:-.02em}
.eye{margin-top:auto;font-size:22px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#F2A57A}
h1{margin-top:14px;font-family:'Inter Display','Inter',sans-serif;font-weight:700;font-size:66px;line-height:1.04;letter-spacing:-.025em;max-width:960px}
p{margin-top:22px;font-size:28px;line-height:1.35;color:#CFE0DA;max-width:900px}
</style></head><body><div class="glow"></div><div class="in">
<div class="brand"><svg width="56" height="56" viewBox="0 0 48 48"><circle cx="24" cy="24" r="24" fill="#FBFAF7"/><path d="M14.5 19 V25.5 a9.5 9.5 0 0 0 19 0 V19" fill="none" stroke="#1F4D45" stroke-width="4" stroke-linecap="round"/><circle cx="24" cy="15.5" r="3.4" fill="#E8915F"/></svg>unbusyness</div>
<div class="eye">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div></body></html>`;
(async () => {
  require('fs').mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1200, height: 630 } });
  for (const [name, langs] of Object.entries(CARDS)) for (const [lang, card] of Object.entries(langs)) {
    await pg.setContent(page(card)); await pg.screenshot({ path: path.join(OUT, `${name}-${lang}.png`) });
  }
  await b.close(); console.log('wrote', Object.keys(CARDS).length * 2, 'images to media/og/');
})();
