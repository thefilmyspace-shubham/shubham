# Dino Car "shop story" reel -- 37.5 s, VO-led (VO: Gavin, sample 1, re-timed by tools/vo_retime.py). Until the VO is recorded the phrase times are estimates (PROVISIONAL);
# once audio/vo_timing.json exists (tools/vo_retime.py) every cue follows the real words.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 37.5
_VO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')
LINES = ["Morning at the toy shop. Full shelves... but nobody stops.",
         "Then the Funhoods Dino Car arrives!",
         "Twelve dinos in a bright display box, right on the counter.",
         "One push, and off it goes! A full 360 flip... and that dino mouth opens wide!",
         "Kids crowd in... and by evening, the box is empty. Time to reorder!",
         "Four colours, BIS approved, safe for little hands.",
         "192 pieces per carton, pan India delivery.",
         "Distributors and wholesalers, put the Dino Car in every shop on your route!",
         "Funhoods... Childhood Full of Fun!"]
PROVISIONAL = not os.path.exists(_VO)
if PROVISIONAL:                # words spread evenly at about 3 words / s, short pauses between lines
    VO, t = [], 0.4
    for i, line in enumerate(LINES):
        ws = line.replace("...", " ").split(); d = len(ws) / 3.0
        VO.append({'start': t, 'end': t + d, 'words': [[t + d * k / len(ws), w_] for k, w_ in enumerate(ws)]})
        t += d + (0.45 if i in (0, 3, 4) else 0.3)
else:
    VO = json.load(open(_VO))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 Morning at the toy shop. Full shelves... but nobody stops.
SHUTTER = (0.15, 1.15)         # the shutter rolls up
KIDS_PASS = (0.9, 3.9)         # kids walk past without stopping
# 1 Then the Funhoods Dino Car arrives!
S_ARRIVE = gap(1)
TRUCK_STOP = S_ARRIVE + 0.85   # the truck pulls up
CARTON_LAND = w(1, 6)          # "arrives": the carton hops to the shop door  (words: Then the fun hoods dino car arrives)
# 2 Twelve dinos in a bright display box, right on the counter.
S_COUNTER = gap(2)
BOX_LAND = w(2, 5)             # "display box"
SPOT = BOX_LAND + 0.15         # the lamp turns into a spotlight
# 3 One push, and off it goes! A full 360 flip... and that dino mouth opens wide!
S_DEMO = gap(3)
PUSH0 = w(3, 1)                # "push": the hand pushes
RELEASE = w(3, 3) - 0.04       # "off it goes"
LAUNCH = w(3, 8) - 0.20        # leaves the ramp ("360 flip")
LAND = LAUNCH + 0.70
CHOMPS = [(LAND + 0.55, 9, 0.05), (w(3, 13) - 0.05, 13, 0.06), (w(3, 15) - 0.12, 16, 0.34)]   # (open, lift deg, hold): after landing, "mouth", "wide"
# 4 Kids crowd in... and by evening, the box is empty. Time to reorder!
S_RUSH = gap(4)
GRABS = [S_RUSH + 0.45 + 0.17 * i for i in range(12)]          # the 12 dinos hop out of the box
EVENING = w(4, 4) - 0.1        # "by evening": the window light turns warm
SOLD = w(4, 9)                 # "empty": SOLD OUT stamp
REORDER = w(4, 10)             # "Time to reorder!"
# 5 Four colours, BIS approved, safe for little hands.
S_FACTS = gap(5)
FACT_POPS = [w(5, 0), w(5, 2), w(5, 4), w(5, 4) + 0.6]
# 6 192 pieces per carton, pan India delivery.
S_CARTON = gap(6)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]
TRUCK = w(6, 4) - 0.05         # "pan India delivery"
# 7 Distributors and wholesalers, put the Dino Car in every shop on your route!
S_ROUTE = gap(7)
ROUTE_LIT = [w(7, 3) - 0.1 + 0.7 * i for i in range(3)]          # from "put the Dino Car...": the truck passes each shop, its window lights up
# 8 Funhoods, Childhood Full of Fun!
S_END = gap(8)

CUTS = [(S_ARRIVE, None), (S_COUNTER, 'zoom'), (S_DEMO, 'zoom'), (S_RUSH, 'zoom'), (S_FACTS, 'chev'),
        (S_CARTON, 'zoom'), (S_ROUTE, 'chev'), (S_END, 'flash')]
MUSIC_IN = 0.231                # "Playful" (Mixkit) -- 130 BPM, bar 0 downbeat at 0.231 s
