# Dino Car reel -- 30 s, VO-led cut (client's ElevenLabs voice-over, re-timed by tools/vo_retime.py). 4K60 output.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 30.0
VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 The Dino Monster Truck!  (+ roar)
ROAR = VO[0]['end'] + 0.03
# 1 No batteries needed, just push and go.  (+ zoom)
S_PUSH = VO[1]['start']
PUSH0 = w(1, 3)                # "just": the hand starts pushing
HAND_IN = PUSH0 - 0.34
RELEASE = VO[1]['end'] - 0.04  # hand lets go, the car zooms off
# 2 It flips 360 degree and its dino mouth opens wide.
S_STUNT = VO[2]['start']
LAUNCH = S_STUNT + 0.62        # car leaves the ramp
LAND = LAUNCH + 0.70
S_MOUTH = w(2, 5) - 0.10       # "its"
# the head chomps like the real toy: (open time, lift in degrees, hold open) -- the last one wide on "wide"
CHOMPS = [(S_MOUTH + 0.18, 12, 0.08), (w(2, 7) - 0.04, 13, 0.06), (w(2, 9) - 0.14, 16, 0.32)]
CHOMP_SHUT = [t0 + 0.16 + hold + 0.10 for t0, amp, hold in CHOMPS]
# 3+4 Four fun colours. Blue, pink, green and yellow.
S_COLORS = gap(3)
COL_POPS = [w(4, 0), w(4, 1), w(4, 2), w(4, 4)]
# 5 BIS approved, made of virgin polymer, safe for little hands.
S_SAFE = gap(5)
SAFE_POPS = [w(5, 0), w(5, 2), w(5, 6), w(5, 6) + 0.55]
# 6 12 per display box, it sells itself on the counter.
S_BOX = gap(6)
BOX_LAND = S_BOX + 0.42
COUNTER = w(6, 4)              # "it sells itself on the counter"
# 7 192 pieces per carton with pan India delivery.
S_CARTON = gap(7)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]   # x, y, landing
TRUCK = w(7, 4) - 0.05         # "with pan India delivery"
# 8 Distributors and wholesalers, place your bulk order today.
S_BULK = gap(8)
# 9 Funhoods, childhood full of fun.
S_END = gap(9)

CUTS = [(S_PUSH, 'zoom'), (S_STUNT, 'zoom'), (S_MOUTH, 'zoom'), (S_COLORS, 'chev'), (S_SAFE, 'zoom'),
        (S_BOX, 'chev'), (S_CARTON, 'chev'), (S_BULK, 'zoom'), (S_END, 'flash')]
# music: "Cupcakes" (Michael Ramir C., Mixkit) -- 138 BPM, bar 0 downbeat at 0.402 s -> reel 0.0
MUSIC_IN = 0.402
