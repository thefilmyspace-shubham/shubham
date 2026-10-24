// Renders reel.html frame-by-frame with Playwright.
// usage: node render.js preview  -> key-moment stills into preview/
//        node render.js full     -> all frames into frames/
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'); const path = require('path');
const FPS = 30, DUR = 40.5;
(async () => {
  const mode = process.argv[2] || 'preview';
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'reel.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  if (mode === 'preview') {
    const times = process.argv.slice(3).map(Number);
    const ts = times.length ? times : [0.8, 3.1, 6.5, 10.5, 12.7, 13.6, 15.3, 17.0, 18.9, 21.6, 23.6, 25.6, 29.2, 31.9, 33.3, 35.3, 36.4, 38.7, 40.0];
    fs.mkdirSync('preview', { recursive: true });
    for (const t of ts) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: `preview/t${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 85 });
    }
  } else {
    fs.mkdirSync('frames', { recursive: true });
    const n = Math.ceil(DUR * FPS);
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => render(t), i / FPS);
      await page.screenshot({ path: `frames/f${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 93 });
      if (i % 150 === 0) console.log('frame', i, '/', n);
    }
  }
  await browser.close();
})();
