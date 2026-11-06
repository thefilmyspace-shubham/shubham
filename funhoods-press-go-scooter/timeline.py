# Press & Go Scooter reel -- 31 s, VO-led cut (Magnific / ElevenLabs VO "Gavin", re-timed by tools/vo_retime.py). 4K60.
import json, os
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920
DUR = 31.0
VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'vo_timing.json')))
def w(p, i): return VO[p]['words'][i][0]                      # word i of phrase p, on the reel clock
def gap(p): return (VO[p - 1]['end'] + VO[p]['start']) / 2      # middle of the pause before phrase p

# 0 Meet the Funhoods Press and Go Scooter!  (horn "beep beep" SFX first -- never spoken)
LAND0 = 0.30                   # the duck scooter drops in and lands
HORN = 0.34                    # horn SFX starts (audio/sfx_horn_beep_1.mp3, first 0.44 s): its two beeps land at +0.04 and +0.30
BEEPS = [HORN + 0.04, HORN + 0.30]
# 1 Just press the head... watch it turn... and off it goes!
S_PRESS = gap(1)
PRESSES = [w(1, 1), w(1, 3)]   # "press", "head": the finger pushes the head down twice (down only, no turn)
TURN0, TURN1 = w(1, 4) - 0.16, w(1, 7) - 0.03   # "watch it turn": finger away, the head turns a full 360 on its own
POSES = ['F', 'L', 'B', 'R', 'F']                  # front -> left -> back -> right -> front
GO_PRESS = TURN1 + 0.24        # the finger comes back, presses and holds ...
RELEASE = w(1, 8) - 0.05       # ... "off it goes": lets go, the scooter shoots off
# 2 Two cute riders, a little mouse and a happy duck!
S_RIDERS = gap(2)
MOUSE, DUCK = w(2, 5) - 0.06, w(2, 9) - 0.06
# 3 Bright blue, red and orange scooters.
S_COLOURS = gap(3)
COL_POPS = [w(3, 1), w(3, 2), (w(3, 2) + w(3, 4)) / 2, w(3, 4)]   # blue, red, sky blue (between), orange: the 4 colours
# 4 BIS certified, Made in India and non-toxic.
S_SAFE = gap(4)
SAFE_POPS = [w(4, 0), w(4, 2), w(4, 6), w(4, 6) + 0.55]
# 5 In a see-through pouch that shows off every rider.
S_POUCH = gap(5)
SHOWS = w(5, 6) - 0.06
# 6 Two hundred forty pieces per carton, pan India delivery.
S_CARTON = gap(6)
STACK = [(318, 1130, S_CARTON + 0.36), (762, 1130, S_CARTON + 0.64), (540, 828, S_CARTON + 0.98)]   # x, y, landing
TRUCK = w(6, 4) - 0.05         # "pan India delivery"
# 7 Distributors and wholesalers, fill your shelves with Press and Go!
S_BULK = gap(7)
FILL = [w(7, 3) + 0.11 * i for i in range(6)]                   # "fill your shelves": pouches pop onto the peg wall
# 8 Funhoods, Childhood Full of Fun!
S_END = gap(8)

CUTS = [(S_PRESS, 'zoom'), (S_RIDERS, 'chev'), (S_COLOURS, 'zoom'), (S_SAFE, 'chev'), (S_POUCH, 'zoom'),
        (S_CARTON, 'chev'), (S_BULK, 'zoom'), (S_END, 'flash')]
# music: "Kidding Around" (Ahjay Stelino, Mixkit) -- 87.5 BPM, bar 0 downbeat at 0.394 s -> reel 0.0
MUSIC_IN = 0.394
