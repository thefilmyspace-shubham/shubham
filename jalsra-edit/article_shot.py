#!/usr/bin/env python3
"""Screenshot a real news article (mobile layout) and record where its headline, lead photo and quoted lines sit.

  python3 article_shot.py URL out_prefix --quote "exact sentence from the page" --quote "..."

Writes out_prefix.png (full page, ads/popups hidden) and out_prefix.json with CSS-pixel rects scaled to the PNG:
  {"url", "title", "h1": [x,y,w,h], "img": [x,y,w,h], "quotes": [{"text", "found", "lines": [[x,y,w,h], ...]}], "scale"}
A quote that is not found on the page is reported with "found": false; never fake it.
"""
import argparse, json, os, sys
from playwright.sync_api import sync_playwright

HIDE_CSS = """
iframe, ins, [id*="google_ads"], [class*="ad-"], [class*="-ad"], [class*="ads"], [id*="ads"], [class*="Ad_"],
[class*="advert"], [class*="sticky"], [class*="popup"], [class*="modal"], [id*="taboola"], [class*="taboola"],
[class*="outbrain"], [class*="cookie"], [id*="cookie"], [class*="notification"], [class*="subscribe"],
[class*="Toastify"], [class*="banner"], .fc-consent-root, #onesignal-slidedown-container, [class*="whatsapp"],
[class*="share"], [class*="social"] { display: none !important; }
header, nav, [class*="header"][style*="fixed"] { position: static !important; }
* { animation: none !important; transition: none !important; }
"""

JS_RECTS = r"""
(quotes) => {
  const r = el => { const b = el.getBoundingClientRect(); return [b.left + scrollX, b.top + scrollY, b.width, b.height]; };
  const vis = el => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
  const h1s = [...document.querySelectorAll('h1')].filter(vis);
  const h1 = h1s.length ? h1s.sort((a, b) => b.getBoundingClientRect().width * b.textContent.length - a.getBoundingClientRect().width * a.textContent.length)[0] : null;
  let img = null;
  if (h1) {
    const top = h1.getBoundingClientRect().top;
    const imgs = [...document.querySelectorAll('img, picture img, video')].filter(vis).filter(i => {
      const b = i.getBoundingClientRect(); return b.width >= innerWidth * 0.6 && b.height >= 150 && b.top > top - 400; });
    imgs.sort((a, b) => Math.abs(a.getBoundingClientRect().top - top) - Math.abs(b.getBoundingClientRect().top - top));
    img = imgs[0] || null;
  }
  const norm = s => s.replace(/[\s ]+/g, ' ').replace(/[“”"]/g, '"').trim();
  const out = [];
  for (const q of quotes) {
    const target = norm(q);
    // walk text nodes, build a flat string with node offsets, then map the match back to a Range
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = []; let flat = '';
    while (walker.nextNode()) {
      const n = walker.currentNode; if (!n.parentElement || !vis(n.parentElement)) continue;
      const t = n.textContent.replace(/[\s ]+/g, ' ').replace(/[“”"]/g, '"');
      nodes.push([n, flat.length, t]); flat += t;
    }
    const flatN = flat.replace(/ {2,}/g, ' ');
    let idx = flat.indexOf(target);
    if (idx < 0) { out.push({text: q, found: false, lines: []}); continue; }
    const end = idx + target.length;
    const range = document.createRange();
    for (const [n, off, t] of nodes) {
      if (idx >= off && idx <= off + t.length) { range.setStart(n, Math.min(idx - off, n.textContent.length)); break; }
    }
    for (const [n, off, t] of nodes) {
      if (end >= off && end <= off + t.length) { range.setEnd(n, Math.min(end - off, n.textContent.length)); break; }
    }
    const rects = [...range.getClientRects()].filter(b => b.width > 2).map(b => [b.left + scrollX, b.top + scrollY, b.width, b.height]);
    // merge rects on the same line
    const lines = [];
    for (const b of rects) {
      const L = lines.find(l => Math.abs((l[1] + l[3] / 2) - (b[1] + b[3] / 2)) < b[3] * 0.5);
      if (L) { const x0 = Math.min(L[0], b[0]), x1 = Math.max(L[0] + L[2], b[0] + b[2]); L[0] = x0; L[2] = x1 - x0;
               const y0 = Math.min(L[1], b[1]), y1 = Math.max(L[1] + L[3], b[1] + b[3]); L[1] = y0; L[3] = y1 - y0; }
      else lines.push([...b]);
    }
    out.push({text: q, found: true, lines});
  }
  return {title: document.title, h1: h1 ? r(h1) : null, h1text: h1 ? h1.textContent.trim() : null,
          img: img ? r(img) : null, quotes: out, width: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight};
}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url'); ap.add_argument('out')
    ap.add_argument('--quote', action='append', default=[])
    ap.add_argument('--width', type=int, default=412)
    ap.add_argument('--dpr', type=float, default=3.0)
    ap.add_argument('--wait', type=float, default=4.0)
    ap.add_argument('--max-height', type=int, default=6000, help='CSS px of page to capture')
    ap.add_argument('--click', action='append', default=[], help='text of a "read more" button to press first')
    a = ap.parse_args()
    with sync_playwright() as p:
        exe = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
        kw = {'executable_path': exe} if os.path.exists(exe) else {}
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        b = p.chromium.launch(proxy={'server': proxy} if proxy else None, **kw)
        ctx = b.new_context(viewport={'width': a.width, 'height': 900}, device_scale_factor=a.dpr, is_mobile=True,
                            has_touch=True, locale='hi-IN',
                            user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) '
                                       'Chrome/140.0.0.0 Mobile Safari/537.36')
        page = ctx.new_page()
        page.goto(a.url, wait_until='domcontentloaded', timeout=90000)
        page.wait_for_timeout(int(a.wait * 1000))
        for label in a.click:  # e.g. Bhaskar hides the rest of the story behind "पढ़िए पूरा"
            loc = page.get_by_text(label).first
            try:
                loc.scroll_into_view_if_needed(timeout=5000); loc.click(timeout=5000); page.wait_for_timeout(1500)
            except Exception as ex:
                print('could not click', label, ex.__class__.__name__)
        page.add_style_tag(content=HIDE_CSS)
        # scroll through once so lazy images load, then back to top
        for y in range(0, a.max_height, 600):
            page.evaluate(f'window.scrollTo(0,{y})'); page.wait_for_timeout(150)
        page.evaluate('window.scrollTo(0,0)'); page.wait_for_timeout(800)
        # fixed/sticky bars repeat over a full-page capture: drop fixed ones, pin sticky ones in place
        page.evaluate("""() => { for (const el of document.querySelectorAll('body *')) {
            const p = getComputedStyle(el).position;
            if (p === 'fixed') el.style.setProperty('display', 'none', 'important');
            else if (p === 'sticky') el.style.setProperty('position', 'static', 'important'); } }""")
        page.wait_for_timeout(300)
        info = page.evaluate(JS_RECTS, a.quote)
        h = min(info['height'], a.max_height)
        page.screenshot(path=a.out + '.png', full_page=True, clip={'x': 0, 'y': 0, 'width': a.width, 'height': h})
        info.update(url=a.url, scale=a.dpr, captured_height=h)
        json.dump(info, open(a.out + '.json', 'w'), ensure_ascii=False, indent=1)
        b.close()
    print(info['title']); print('h1:', info['h1text'])
    for q in info['quotes']:
        print(('FOUND ' if q['found'] else 'MISSING ') + q['text'][:70], q['lines'][:3])
    if not all(q['found'] for q in info['quotes']): sys.exit(2)

if __name__ == '__main__':
    main()
