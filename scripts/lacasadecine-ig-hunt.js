#!/usr/bin/env node
require('dotenv').config({ path: '/Users/jofreeyzaguirre/claude/unabasi-leads/.env', override: true });
const puppeteer = require('puppeteer');
const fs = require('fs');
const sleep = ms => new Promise(r => setTimeout(r, ms));

function pf(s) { if (!s) return null; const m = s.match(/([\d.,]+)\s*([KMkm])?\s*(?:Followers|followers|seguidores|Seguidores)/); if (!m) return null; let n = parseFloat(m[1].replace(/,/g, '')); if ((m[2] || '').toLowerCase() === 'k') n *= 1000; if ((m[2] || '').toLowerCase() === 'm') n *= 1e6; return Math.round(n); }
function postCount(s) { if (!s) return null; const m = s.match(/([\d.,]+)\s*([KMkm])?\s*(?:Posts|posts|publicaciones)/); if (!m) return null; let n = parseFloat(m[1].replace(/,/g, '')); if ((m[2] || '').toLowerCase() === 'k') n *= 1000; return Math.round(n); }

const HANDLES = [
  'la_casa_de_cine',
  'lacasadecinemx',
  'lacasadecine_mx',
  'casadecine',
  'casadecinemx',
  'la.casa.de.cine',
  'chisco_laresgoiti',
  'chiscolaresgoiti',
  'jordimariscal_',
  'jordimariscal',
];

(async () => {
  const br = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'] });
  const p = await br.newPage();
  await p.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');
  const results = [];
  for (const h of HANDLES) {
    try {
      await p.goto('https://www.instagram.com/' + h + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(4500);
      const d = await p.evaluate(() => ({ og: (document.querySelector('meta[property="og:description"]') || {}).content || '', ogt: (document.querySelector('meta[property="og:title"]') || {}).content || '', title: document.title || '' }));
      if (d.title.includes("Profile isn't")) { console.log('  @' + h + ' → NOT FOUND'); results.push({ handle: h, status: 'not_found' }); await sleep(4500); continue; }
      const followers = pf(d.og);
      const posts = postCount(d.og);
      const ogtLow = d.ogt.toLowerCase();
      const ogLow = d.og.toLowerCase();
      const nameMatch = ogtLow.includes('casa') || ogtLow.includes('cine') || ogtLow.includes('laresgoiti') || ogtLow.includes('mariscal') || ogLow.includes('lacasadecine') || ogLow.includes('canela') || ogLow.includes('2033');
      console.log('  @' + h.padEnd(22) + ' followers=' + followers + ' posts=' + posts + ' nameMatch=' + nameMatch + ' ogt="' + d.ogt.slice(0, 50) + '"');
      results.push({ handle: h, followers, posts, nameMatch, ogt: d.ogt });
    } catch (e) { console.log('  @' + h + ' err: ' + e.message); results.push({ handle: h, status: 'error', err: e.message }); }
    await sleep(5500);
  }
  try { await br.close(); } catch { }
  fs.writeFileSync('/tmp/lacasadecine-ig-hunt.json', JSON.stringify(results, null, 2));
})();
