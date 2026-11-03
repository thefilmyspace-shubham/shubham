# PVC Racing Car reel -- 32 s, VO-led cut (Magnific / ElevenLabs VO "Gavin", re-timed by tools/vo_retime.py). 4K60.
# v4: the window box opens the reel (start lights over the box), the car is introduced after it.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 32.0
VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 On your marks... get set... VROOM!  (the window box, start lights above it)
LIGHTS = [w(0, 0), w(0, 3), w(0, 5)]                            # red, red, green
VROOM = w(0, 5)
# 1 A bold window box that grabs every eye in the store.  (same box, continuous: it lands on a shop counter)
S_BOX = gap(1)
BOX_LAND = w(1, 5) - 0.10      # "grabs every eye"
# 2 Say hello to the Funhoods Racing Car!
S_SPIN = gap(2)
# 3 Give it a push... let go... and watch it race!
S_PUSH = gap(3)
PUSH0 = w(3, 0) + 0.10         # "Give": the glove starts pushing
RELEASE = w(3, 4) + 0.05       # "let go"
RACE = w(3, 6)                 # "and watch it race": the car takes off
# 4 Press the roof... bright lights and loud music!  (+ the toy's own music in the pause after)
S_LIGHTS = gap(4)
PRESS = w(4, 0) + 0.10
GLOW = w(4, 3) - 0.05          # "bright lights"
NOTES = w(4, 6) - 0.05         # "loud music"
# 5 Four-wheel drive, a sturdy body and chunky tyres.
S_4WD = gap(5)
CALL_BODY, CALL_TYRES = w(5, 4) - 0.05, w(5, 7) - 0.05
# 6 Cool style, bold looks... built to race!  (one colour only -- no other models / colours are shown)
S_STYLE = gap(6)
LOOKS, BUILT = w(6, 2) - 0.06, w(6, 4) - 0.06
# 7 Thirty-six pieces per carton, shipped anywhere in India.
S_CARTON = gap(7)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]   # x, y, landing
TRUCK = w(7, 4) - 0.05         # "shipped anywhere in India"
# 8 Distributors and wholesalers, stock up for the season!
S_BULK = gap(8)
STOCK = w(8, 3) - 0.08         # "stock up"
# 9 Funhoods, childhood full of fun.
S_END = gap(9)

CUTS = [(S_SPIN, 'chev'), (S_PUSH, 'zoom'), (S_LIGHTS, 'zoom'), (S_4WD, 'chev'), (S_STYLE, 'zoom'),
        (S_CARTON, 'chev'), (S_BULK, 'zoom'), (S_END, 'flash')]
# music: "Jumping Around" (Ahjay Stelino, Mixkit) -- 110 BPM, bar 0 downbeat at 0.491 s -> reel 0.0
MUSIC_IN = 0.491
