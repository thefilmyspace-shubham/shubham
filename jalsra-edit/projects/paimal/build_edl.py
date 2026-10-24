#!/usr/bin/env python3
"""Paimal speech -> edl.json for docu.py.

Every B-roll is a real source: the client's two newspaper cuttings, or a news article captured (and its quote verified
on the page) by article_shot.py. Claims with no source found online (Alkapuri rust, Lohar Road-Topkhana four-lane,
mayor-in-council approval, firm paid for Ravan Dahan) stay on the A-roll with no B-roll.
"""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
R = 'projects/paimal/'
WEB = R + 'web/'

# ------------------------------------------------------------------ A-roll cuts
sil = json.load(open(os.path.join(D, 'audio/silences.json')))
sil += [[126.20, 127.92]]  # pause with a breath in it (camera-mic half)
sil.sort(); merged = []
for a, b in sil:
    if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
    else: merged.append([a, b])
sil = merged
segs, cur = [], 0.85
for a, b in sil:
    if a < 0.5: continue
    if b > 168: segs.append([cur, 168.6]); break
    if b - a > 0.36: segs.append([cur, a + 0.12]); cur = b - 0.08
# zoom-only punch-ins inside long stretches (no time removed): split at these word boundaries
SPLITS = [17.70, 60.88, 116.20, 135.05, 139.05, 150.47, 160.0, 163.05, 165.14]
out = []
for s0, s1 in segs:
    pts = [s0] + [x for x in SPLITS if s0 + 1.0 < x < s1 - 1.0] + [s1]
    out += [[a, b] for a, b in zip(pts, pts[1:])]
EMPH = [(41.0, 44.2, 1.32), (66.0, 70.8, 1.3), (135.5, 139.3, 1.3), (160.0, 163.1, 1.28)]
segments, flip = [], False
for s0, s1 in out:
    z = next((e[2] for e in EMPH if e[0] <= s0 + 0.05 and s1 <= e[1] + 0.05), None)
    if z is None: z = 1.2 if flip else 1.07; flip = not flip
    segments.append([round(s0, 3), round(s1, 3), z])
segments[0][2] = 1.04

# ------------------------------------------------------------------ B-rolls
def web(name, crop, **kw):
    return dict(img=WEB + name + '.png', css=True, crop=crop, **kw)

CUT_DOGS = R + 'assets/clip_dogs_bhaskar_2025-12-27.jpg'
CUT_LED = R + 'assets/clip_led_naidunia_2023-04-29.jpg'

brolls = [
    # 1. "9 महीने तक लकड़पीठा में रोड नहीं बनी ... चक्का जाम किया"
    dict(t0=6.0, t1=11.96, labels=[dict(text='पत्रिका  •  22 अक्टूबर 2026', t=0.15)], pieces=[
        web('patrika_lakkadpitha', [10, 465, 392, 261], id='photo', w=980, pos=[540, 1130], rot=1.4, at=6.0, seed=2),
        web('patrika_lakkadpitha', [0, 138, 412, 190], id='head', w=1000, pos=[540, 650], rot=-1.3, at=6.62, seed=3,
            hl=[dict(quote=0, at=10.95, d=0.5)]),
    ], cam=[dict(t=0, cx=540, cy=1000, zoom=1.0), dict(at=7.0, cx=540, cy=900, zoom=1.04),
            dict(at=10.55, focus='head', mark='hl', zoom=1.42, screen_y=820)]),
    # 2. "मकान तोड़ने की जल्दी थी, लेकिन रोड बनाने की जल्दी नहीं हुई"
    dict(t0=15.05, t1=19.98, labels=[dict(text='दैनिक भास्कर  •  9 मार्च 2026', t=0.15)], pieces=[
        web('bhaskar_bulldozer', [0, 86, 412, 108], id='head', w=1000, pos=[540, 690], rot=-1.0, at=15.05, seed=4,
            hl=[dict(quote=0, at=15.55, d=0.55)]),
        web('bhaskar_bulldozer', [16, 507, 380, 285], id='photo', w=960, pos=[540, 1170], rot=1.6, at=15.4, fx='slide',
            seed=5, **{'from': [0, 1100]}),
    ], cam=[dict(t=0, cx=540, cy=930, zoom=1.0), dict(at=15.45, focus='head', mark='hl', zoom=1.38, screen_y=860),
            dict(at=17.75, focus='photo', zoom=1.12, screen_y=960)]),
    # 3. "कमिश्नर साहब गए, महापौर जी आए"
    dict(t0=27.62, t1=30.9, labels=[dict(text='ETV भारत  •  21 अक्टूबर 2026', t=0.12)], pieces=[
        web('etv_mayor_commissioner', [0, 356, 412, 232], id='photo', w=1000, pos=[540, 830], rot=-1.2, at=27.62, seed=6),
        web('etv_mayor_commissioner', [8, 1981, 404, 60], id='quote', w=1000, pos=[540, 1250], rot=1.0, at=27.95,
            fx='slide', seed=7, hl=[dict(quote=0, at=28.25, d=0.6)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=1000, zoom=1.02), dict(at=28.1, focus='quote', mark='hl', zoom=1.22, screen_y=1060)]),
    # 4a. "महापौर जी कहते हैं कि सिस्टम लाचार है"
    dict(t0=38.25, t1=40.48, labels=[dict(text='वंदेमातरम न्यूज़  •  22 अक्टूबर 2026', t=0.1)], pieces=[
        web('vm_mayor', [14, 128, 384, 128], id='head', w=1000, pos=[540, 700], rot=-1.1, at=38.25, seed=8),
        web('vm_mayor', [10, 2403, 394, 163], id='quote', w=1000, pos=[540, 1180], rot=0.9, at=38.55, fx='slide', seed=9,
            hl=[dict(quote=0, at=39.35, d=0.42)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=950, zoom=1.0), dict(at=39.05, focus='quote', mark='hl', zoom=1.36, screen_y=900)]),
    # 4b. "अधिकारी को रतलाम शहर की चिंता नहीं है, ना इंजीनियरों को..."
    dict(t0=45.18, t1=50.05, labels=[dict(text='दैनिक भास्कर  •  21 अक्टूबर 2026', t=0.1)], pieces=[
        web('bhaskar_mayor_quote', [0, 86, 412, 108], id='head', w=1000, pos=[540, 640], rot=1.0, at=45.18, seed=10,
            hl=[dict(quote=0, at=45.55, d=0.3)]),
        web('bhaskar_mayor_quote', [16, 507, 380, 285], id='photo', w=900, pos=[540, 1080], rot=-1.6, at=45.6, seed=11),
        web('bhaskar_mayor_quote', [0, 864, 412, 66], id='quote', w=1000, pos=[540, 1350], rot=0.6, at=47.5,
            fx='slide', seed=12, hl=[dict(quote=1, at=48.15, d=0.5)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=900, zoom=1.0), dict(at=45.4, focus='head', mark='hl', zoom=1.32, screen_y=760),
            dict(at=46.6, cx=540, cy=1000, zoom=1.02), dict(at=47.75, focus='quote', mark='hl', zoom=1.3, screen_y=1000)]),
    # 5. "ऊपर से लेकर नीचे तक कमीशनखोरी चल रही है"
    dict(t0=71.12, t1=74.14, labels=[dict(text='वंदेमातरम न्यूज़  •  15 सितंबर 2023', t=0.1)], pieces=[
        web('vm_commission', [14, 128, 384, 198], id='head', w=1000, pos=[540, 700], rot=-0.9, at=71.12, seed=13,
            hl=[dict(quote=1, at=71.5, d=0.45)]),
        web('vm_commission', [10, 1970, 394, 126], id='quote', w=1000, pos=[540, 1260], rot=1.1, at=72.3, fx='slide',
            seed=14, hl=[dict(quote=0, at=72.7, d=0.38)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=900, zoom=1.0), dict(at=71.3, focus='head', mark='hl', zoom=1.3, screen_y=820),
            dict(at=72.45, focus='quote', mark='hl', i=1, zoom=1.3, screen_y=980)]),
    # 6. dog sterilisation: "32,000 कुत्तों का बधियाकरण ... करोड़ों रुपया"
    dict(t0=78.02, t1=84.74, max_zoom=1.4, labels=[dict(text='दैनिक भास्कर  •  6 फ़रवरी 2026', t=0.1),
                                    dict(text='दैनिक भास्कर (रतलाम)  •  27 दिसंबर 2025', at=79.62)], pieces=[
        web('bhaskar_dogs', [0, 86, 412, 108], id='online', w=1000, pos=[540, 560], rot=-1.2, at=78.02, seed=15,
            hl=[dict(quote=0, at=78.55, d=0.45)]),
        dict(img=CUT_DOGS, crop=[8, 28, 716, 742], id='cut', w=1010, pos=[540, 1040], rot=0.8, at=79.62, upscale=1.4,
             paper=[236, 234, 228], tear=7, seed=16, pad=10,
             circle=[dict(rect=[437, 262, 152, 46], at=80.15), dict(rect=[180, 262, 210, 46], at=83.8)],
             hl=[dict(rect=[438, 326, 248, 44], at=81.45, d=0.55)]),
    ], cam=[dict(t=0, cx=540, cy=760, zoom=1.0), dict(at=78.4, focus='online', mark='hl', zoom=1.25, screen_y=800),
            dict(at=79.55, cx=540, cy=1040, zoom=0.98), dict(at=79.95, focus='cut', mark='circle', i=0, zoom=1.62, screen_y=900),
            dict(at=81.25, focus='cut', mark='hl', zoom=1.55, screen_y=900),
            dict(at=83.55, focus='cut', mark='circle', i=1, zoom=1.62, screen_y=900)]),
    # 7. LED: "700 रुपये का एलईडी बल्ब ... 2,900 रुपये में खरीदा गया ... एक फर्म को बहुत सारे टेंडर"
    dict(t0=89.62, t1=99.0, max_zoom=1.5, labels=[dict(text='नईदुनिया (रतलाम)  •  29 अप्रैल 2023', t=0.12)], pieces=[
        dict(img=CUT_LED, crop=[40, 28, 1005, 470], id='cut', w=1030, pos=[540, 960], rot=-0.8, at=89.62, upscale=1.4,
             paper=[232, 230, 226], tear=6, seed=17, pad=10,
             circle=[dict(rect=[55, 47, 98, 54], at=91.3), dict(rect=[588, 47, 126, 54], at=93.72)],
             hl=[dict(rect=[[488, 422, 54, 24], [303, 446, 238, 24], [303, 470, 125, 24]], at=96.55, d=0.42)]),
    ], cam=[dict(t=0, cx=540, cy=960, zoom=1.0), dict(at=91.0, focus='cut', mark='circle', i=0, zoom=1.75, screen_y=900),
            dict(at=93.4, focus='cut', mark='circle', i=1, zoom=1.75, screen_y=900), dict(at=95.1, cx=540, cy=960, zoom=1.05),
            dict(at=96.25, focus='cut', mark='hl', i=1, zoom=1.85, screen_y=1040)]),
    # 8. Ravan Dahan: "रावण दहन के अंदर किस प्रकार से भ्रष्टाचार हुआ"
    dict(t0=105.36, t1=112.2, labels=[dict(text='वंदेमातरम न्यूज़  •  3 अक्टूबर 2025', t=0.12)], pieces=[
        web('vm_ravan', [14, 128, 384, 128], id='head', w=1000, pos=[540, 690], rot=-1.0, at=105.36, seed=18,
            hl=[dict(quote=1, at=109.6, d=0.42)]),
        web('vm_ravan', [10, 3033, 394, 124], id='quote', w=1000, pos=[540, 1190], rot=1.2, at=107.0, fx='slide', seed=19,
            hl=[dict(quote=0, at=110.75, d=0.36)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=900, zoom=1.0), dict(at=106.1, focus='head', zoom=1.12, screen_y=820),
            dict(at=107.2, cx=540, cy=960, zoom=1.0), dict(at=109.35, focus='head', mark='hl', zoom=1.36, screen_y=820),
            dict(at=110.5, focus='quote', mark='hl', i=1, zoom=1.34, screen_y=980)]),
    # 9. tax money: "आपके द्वारा जो टैक्स दिया गया ... वो पैसा इनके भ्रष्टाचार में जा रहा है"
    dict(t0=122.66, t1=132.8, labels=[dict(text='ETV भारत  •  6 अप्रैल 2026', t=0.12)], pieces=[
        web('etv_tax', [0, 176, 412, 78], id='head', w=1000, pos=[540, 620], rot=-1.0, at=122.66, seed=20,
            hl=[dict(quote=1, at=123.25, d=0.5)]),
        web('etv_tax', [0, 356, 412, 232], id='photo', w=980, pos=[540, 1040], rot=1.3, at=123.05, seed=21),
        web('etv_tax', [8, 1518, 404, 58], id='quote', w=1000, pos=[540, 1360], rot=-0.7, at=127.35, fx='slide', seed=22,
            hl=[dict(quote=0, at=130.4, d=0.55)], **{'from': [0, 900]}),
    ], cam=[dict(t=0, cx=540, cy=820, zoom=1.0), dict(at=123.0, focus='head', mark='hl', zoom=1.3, screen_y=820),
            dict(at=124.2, cx=540, cy=1000, zoom=1.0), dict(at=127.6, cx=540, cy=1150, zoom=1.04),
            dict(at=130.1, focus='quote', mark='hl', i=1, zoom=1.32, screen_y=980)]),
]

KEYWORDS = ['लकड़पीठा', 'चक्का', 'जाम', 'नपुंसक', 'लाचार', 'भ्रष्टाचार', 'कमीशनखोरी', 'बधियाकरण', '32,000', 'करोड़ों',
            '700', '2,900', 'एलईडी', 'टेंडर', 'अलकापुरी', 'जंग', 'रावण', 'दहन', 'टैक्स', 'ट्रिपल', 'इंजन', 'तोपखाना',
            'फोरलेन', 'लोहार', '9', 'महीने', 'मकान', 'तोड़ने', 'रतलाम']

edl = {
    'source': 'footage/paimal_1440.mp4',
    'dialogue': R + 'audio/dialogue_clean.wav',
    'words': R + 'words.json',
    'face': [0.52, 0.37],
    'grade': {'contrast': 1.07, 'saturation': 0.94, 'lift': -0.012, 'warmth': 0.006},
    'segments': segments,
    'brolls': brolls,
    'subs': {'on': False, 'font': 'fonts/Mukta-Bold.ttf', 'size': 62, 'y': 1525, 'max_chars': 20, 'max_words': 4,
             'keywords': KEYWORDS},
    'music': {'file': 'music/paimal_intense_170s.mp3'},
    'sfx_emphasis': [41.21, 66.02, 135.64],
    'tail': 2.4,
}
json.dump(edl, open(os.path.join(D, 'edl.json'), 'w'), ensure_ascii=False, indent=1)
tot = sum(b - a for a, b, _ in segments)
print(f'{len(segments)} segments, {tot:.2f}s timeline, {len(brolls)} B-rolls')
