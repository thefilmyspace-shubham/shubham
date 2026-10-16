# Musical Stick reel -- 30 s, same music edit / beat grid as the Target Blaster reel. 4K60 output.
BEAT = 60/130
def b(n): return n*BEAT
# music: "Playground Fun" (Ahjay Stelino, Mixkit) -- 130.000 BPM, bar 0 downbeat at 0.4269 s
def mbar(k): return 0.4269 + 4*k*BEAT
MUSIC = [(0, mbar(16)),    # bars 16-18: section start, full band (logo, reveal, box)
         (12, mbar(35)),   # bars 35-39: breakdown (features, how it works) -> return at bar 40
         (32, mbar(40)),   # bars 40-44: the return = PRESS & PLAY! drop, why stock it, bulk orders
         (52, mbar(87))]   # bar 87 -> bar 88 downbeat on the end card
DROP = b(32)
END_HIT = b(56)
DUR = 30.0
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920

# AI b-roll (Kling 2.5, 5 s, 1080x1920): (v_start, v_end, clip, src_in, src_out)
SEG = []
def seg(v0, v1, clip, s0, s1): SEG.append((v0, v1, clip, s0, s1))
seg(b(16), b(20), 'k3', 0.3, 2.4)    # stick hero float -- feature 02 (Kling clip or start-frame move)
# v2: every box shot is a motion graphic on the brand background (no photo/blur backgrounds)
PICK_RISE = (b(20) + 0.30, 0.75)     # stick rises out of the box: start, duration
STACK = [(290, 1600, b(52) + 0.30), (790, 1600, b(52) + 0.75), (540, 1225, b(53) + 0.45)]   # x, y, landing time

CUTS = [(b(4),'chev'),(b(8),'zoom'),(b(12),'chev'),(b(16),'zoom'),(b(20),'chev'),(b(24),'zoom'),
        (b(32),'flash'),(b(36),'chev'),(b(44),'chev'),(b(52),'flash'),(b(56),'flash')]
TAPS = [b(24.6), b(25.6), b(26.6)]     # button presses in step 2
