// Render anim.html to frames with headless Chromium.
//   node render.js --stills 1,5,10            -> build/stills/*.png (1080x1920)
//   node render.js --fps 60 --scale 2 --part 0 --parts 4   -> build/frames/f000000.jpg ... (2160x3840)
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const HERE = __dirname;
const MIME = { '.html': 'text/html', '.json': 'application/json', '.png': 'image/png', '.woff2': 'font/woff2' };
(async () => {
  const srv = http.createServer((q, r) => {
    const p = path.join(HERE, decodeURIComponent(q.url.split('?')[0]));
    if (!p.startsWith(HERE) || !fs.existsSync(p)) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(r);
  }).listen(0);
  const port = srv.address().port;
  const scale = +arg('scale', 1), fps = +arg('fps', 30);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
  pg.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await pg.goto(`http://localhost:${port}/anim.html`);
  const total = await pg.evaluate(() => window.init());
  const stills = arg('stills');
  if (stills) {
    fs.mkdirSync(`${HERE}/build/stills`, { recursive: true });
    for (const t of stills.split(',')) { await pg.evaluate(t => window.draw(t), +t); await pg.screenshot({ path: `${HERE}/build/stills/s${(+t).toFixed(2)}.png` }); }
  } else {
    const dir = arg('dir', `${HERE}/build/frames`); fs.mkdirSync(dir, { recursive: true });
    const n = Math.round(total * fps), part = +arg('part', 0), parts = +arg('parts', 1);
    for (let i = part; i < n; i += parts) {
      await pg.evaluate(t => window.draw(t), i / fps);
      await pg.screenshot({ path: `${dir}/f${String(i).padStart(6, '0')}.jpg`, quality: 95 });
    }
    console.log('frames', n);
  }
  await b.close(); srv.close();
})();
