# v2 -- 30 s cut. Beat grid: "Punked Up Fun" (Mixkit) = 130 BPM; every cut lands on a beat.
BEAT = 60/130
BAR = 4*BEAT
def b(n): return n*BEAT                  # video time of beat n
def mbar(k): return 0.072115 + 4*k*BEAT  # music time of bar k
# music edit: (video start beat, music start time); each piece plays until the next one starts
MUSIC = [(0, mbar(22)),    # bars 22-24 full band (logo, pack, hero)
         (12, mbar(27)),   # breakdown bars 27-31 (features, how it works) -> drop
         (32, mbar(32)),   # drop: bars 32-36 (fire, why stock, bulk orders)
         (52, mbar(47))]   # bar 47 fill -> bar 48 hit at beat 56 (end card)
DROP = b(32)
END_HIT = b(56)
DUR = 30.0
FPS = 30
W, H = 1080, 1920

# footage segments: (v_start, v_end, shot, src_in, speed)
SEG = []
def seg(v0, v1, shot, src_in, src_out):
    SEG.append((v0, v1, shot, src_in, (src_out - src_in)/(v1 - v0)))
seg(b(8),  b(12), 'hero_b',   10.10, 11.95)
seg(b(12), b(16), 'badge_c',  8.70,  9.88)   # v5: slower pace -- 2 features x 4 beats
# 16-20 catalogue card (4 darts)
seg(b(20), b(24), 'pull_b2',  17.75, 19.10)
# 24-28 LOAD DARTS = motion graphic: catalogue blaster cut-out + foam dart sliding into the UPPER barrel
# (no AI clip shows upper-barrel loading; the client's phone video was reference only)
LOAD = (b(24), b(28))
LOAD_SEAT = 1.25                         # seconds after LOAD start when the dart seats
seg(b(28), b(32), 'aim_c',    20.42, 21.50)
seg(b(32), b(36), 'fire_c1',  21.50, 22.40)
# 36-44 styled pack (why stock it), 44-52 BULK ORDERS ONLY (192 pcs carton, pan India delivery)
seg(b(52), b(53.5), 'close_b', 17.00, 17.66)
seg(b(53.5), b(56), 'lift_b',  9.20, 10.10)
# 56 -> end card

CUTS = [(b(4),'chev'),(b(8),'zoom'),(b(12),'zoom'),(b(16),'zoom'),
        (b(20),'chev'),(b(24),'zoom'),(b(28),'zoom'),(b(32),'flash'),(b(36),'chev'),(b(44),'chev'),
        (b(52),'flash'),(b(56),'flash')]
