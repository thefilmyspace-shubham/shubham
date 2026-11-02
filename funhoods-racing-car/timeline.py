# PVC Racing Car reel -- 32 s, VO-led cut (Magnific / ElevenLabs VO "Gavin", re-timed by tools/vo_retime.py). 4K60.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 32.0
VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 On your marks... get set... VROOM!
LIGHTS = [w(0, 0), w(0, 3), w(0, 5)]                            # red, red, green
VROOM = w(0, 5)
# 1 Say hello to the Funhoods Racing Car!
S_SPIN = gap(1)
# 2 Give it a push... let go... and watch it race!
S_PUSH = gap(2)
PUSH0 = w(2, 0) + 0.10         # "Give": the glove starts pushing
RELEASE = w(2, 4) + 0.05       # "let go"
RACE = w(2, 6)                 # "and watch it race": the car takes off
# 3 Press the roof... bright lights and loud music!  (+ jingle in the pause after)
S_LIGHTS = gap(3)
PRESS = w(3, 0) + 0.10
GLOW = w(3, 3) - 0.05          # "bright lights"
NOTES = w(3, 6) - 0.05         # "loud music"
# 4 Four-wheel drive, a sturdy body and chunky tyres.
S_4WD = gap(4)
CALL_BODY, CALL_TYRES = w(4, 4) - 0.05, w(4, 7) - 0.05
# 5 Cool style, multiple models, multiple colours!
S_MODELS = gap(5)
MODEL_POPS = [w(5, 2) + 0.15 * i for i in range(2)]
# 6 A bold window box that grabs every eye in the store.
S_BOX = gap(6)
BOX_LAND = w(6, 5) - 0.10      # "grabs every eye": lands on the counter
# 7 Thirty-six pieces per carton, shipped anywhere in India.
S_CARTON = gap(7)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]   # x, y, landing
TRUCK = w(7, 4) - 0.05         # "shipped anywhere in India"
# 8 Distributors and wholesalers, stock up for the season!
S_BULK = gap(8)
STOCK = w(8, 3) - 0.08         # "stock up"
# 9 Funhoods, childhood full of fun.
S_END = gap(9)

CUTS = [(S_SPIN, 'zoom'), (S_PUSH, 'chev'), (S_LIGHTS, 'zoom'), (S_4WD, 'chev'), (S_MODELS, 'zoom'),
        (S_BOX, 'chev'), (S_CARTON, 'chev'), (S_BULK, 'zoom'), (S_END, 'flash')]
# music: "Jumping Around" (Ahjay Stelino, Mixkit) -- 110 BPM, bar 0 downbeat at 0.491 s -> reel 0.0
MUSIC_IN = 0.491
