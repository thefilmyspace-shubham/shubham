#!/usr/bin/env python3
"""Whisper word timings + corrected spelling (from the client's script, kept to what was actually said) -> words.json"""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
segs = json.load(open(os.path.join(D, 'whisper_hi.json')))
ws, seg_end = [], set()
for s in segs:
    ws += s['words']; seg_end.add(len(ws) - 1)  # last word of each Whisper segment = clause end

FIX = {11: '9', 12: 'महीने', 20: 'वहाँ', 25: 'वहाँ', 30: 'सम्माननीय', 33: 'प्रशासन', 42: 'वहाँ', 51: '9', 52: 'महीने',
       59: 'वहाँ', 72: 'माँग', 74: 'वहाँ', 77: 'कमिश्नर', 78: 'साहब', 80: 'महापौर', 94: 'ये', 99: 'ये', 103: 'महापौर',
       110: 'है।', 113: 'नपुंसक', 120: 'शहर', 121: 'की', 126: 'इंजीनियरों', 129: 'शहर', 130: 'की',
       138: 'माध्यम', 140: 'महापौर जी', 149: 'जनप्रतिनिधि', 154: 'भेजा था।', 155: 'रतलाम', 169: 'शहर', 171: 'हैं,',
       176: 'शहर', 178: 'चले', 180: 'सम्माननीय', 182: 'ये', 186: 'प्रशासन', 188: 'ये', 190: 'भ्रष्टाचार', 194: 'ऊपर',
       196: 'लेकर', 199: 'कमीशनखोरी', 211: 'उदाहरण', 212: 'दिए', 216: 'बधियाकरण', 221: '32,000', 225: 'बधियाकरण',
       233: 'करोड़ों', 234: 'रुपया', 235: 'महापौर', 236: 'परिषद ने', 246: 'एलईडी', 247: 'बल्ब', 252: 'रुपये',
       254: 'एलईडी', 255: 'बल्ब', 258: '2,900', 259: 'रुपये', 265: 'फर्म', 271: 'दिए', 277: 'अलकापुरी', 291: 'गई',
       293: 'रावण', 301: 'रावण', 308: 'भ्रष्टाचार', 321: 'फर्म', 324: 'प्रशासन', 333: 'सम्माननीय', 335: 'ये',
       347: 'टैक्स', 360: 'कार्य', 369: 'भ्रष्टाचार', 374: 'ट्रिपल', 384: 'भ्रष्टाचार', 387: 'गति', 393: 'गति',
       405: 'सम्माननीय', 410: 'माध्यम', 412: 'महापौर जी', 415: 'निवेदन', 423: 'शुरू', 438: 'तोपखाना', 443: 'फोरलेन',
       463: 'झेलनी', 473: 'बहुत-बहुत', 477: 'हिंद'}
MERGE_INTO_PREV = {87: 'अपनी-अपनी', 150: None, 200: None, 222: None, 439: None, 444: None, 474: None}  # idx -> new text of previous (None = keep)
DROP = {404}  # "पी" (mis-hearing of a breath)
FIX[86] = 'अपनी-अपनी'

out = []
for i, (w, a, b, p) in enumerate(ws):
    if i in DROP:
        if i in seg_end and out: out[-1][3] = 1
        continue
    if i in MERGE_INTO_PREV:
        out[-1][2] = b; out[-1][3] = int(i in seg_end); continue
    t = FIX.get(i, w)
    out.append([t, a, b, int(i in seg_end or t[-1] in '।,?!')])
json.dump(out, open(os.path.join(D, 'words.json'), 'w'), ensure_ascii=False)
print(len(out), 'words');
print(' '.join(x[0] for x in out))
