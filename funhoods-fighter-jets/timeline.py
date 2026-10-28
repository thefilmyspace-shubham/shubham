# Fighter Jets reel -- 30 s, VO-led cut (Magnific / ElevenLabs VO, audio/vo_timing.json from tools/vo_timing.py). 4K60.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 30.0
VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 Ready for take-off? Meet the Funhoods Fighter Jet Squad!
FLY_IN = 0.05
TITLE_SWAP = w(0, 3) - 0.08    # "Meet"
# 1 Six jets, six bold designs, all in one pack!
S_SIX = gap(1)
SIX_POPS = [w(1, 0) + 0.06 + 0.10 * i for i in range(3)] + [w(1, 2) + 0.06 + 0.10 * i for i in range(3)]
# 2 Pull it back... and let it fly!
S_PULL = gap(2)
HAND_IN = S_PULL + 0.02
PULL0 = w(2, 0) + 0.04         # "Pull": the glove starts pulling the jet back
PULL1 = w(2, 3) + 0.05         # pulled all the way back ("and")
RELEASE = w(2, 4)              # "let": lets go, the jet zooms off
# 3 A fire jet, a camo jet and four more colourful flyers.
S_DESIGNS = gap(3)
FIRE, CAMO = w(3, 1) - 0.06, w(3, 4) - 0.06
FOUR = [w(3, 7) + 0.08 * i for i in range(4)]
# 4 BIS certified, non-toxic and BPA free, proudly Made in India.
S_SAFE = gap(4)
SAFE_POPS = [w(4, 0), w(4, 2), w(4, 5), w(4, 7)]
# 5 Bright, eye-catching packs that fly off the shelves!
S_PACK = gap(5)
PACK_LAND = S_PACK + 0.40
FLY_OFF = w(5, 5) - 0.05       # "fly off the shelves"
# 6 144 per carton, delivered anywhere in India.
S_CARTON = gap(6)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]   # x, y, landing
TRUCK = w(6, 3) - 0.05         # "delivered anywhere in India"
# 7 Distributors and wholesalers, book your bulk stock now!
S_BULK = gap(7)
# 8 Funhoods, childhood full of fun.
S_END = gap(8)

CUTS = [(S_SIX, 'chev'), (S_PULL, 'zoom'), (S_DESIGNS, 'chev'), (S_SAFE, 'zoom'), (S_PACK, 'chev'),
        (S_CARTON, 'chev'), (S_BULK, 'zoom'), (S_END, 'flash')]
# music: "Fun Times" (Ahjay Stelino, Mixkit) -- 145 BPM, bar 0 downbeat at 0.072 s -> reel 0.0
MUSIC_IN = 0.072
