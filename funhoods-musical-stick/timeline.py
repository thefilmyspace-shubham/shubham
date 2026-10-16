# Musical Stick reel -- 30 s, same music edit / beat grid as the Target Blaster reel. 4K60 output.
BEAT = 60/130
def b(n): return n*BEAT
def mbar(k): return 0.072115 + 4*k*BEAT
MUSIC = [(0, mbar(22)), (12, mbar(27)), (32, mbar(32)), (52, mbar(47))]
DROP = b(32)
END_HIT = b(56)
DUR = 30.0
FPS = 60
K = 2                          # design space 1080x1920, rendered at 2160x3840
DW, DH = 1080, 1920

# AI b-roll (Kling 2.5, 5 s, 1080x1920): (v_start, v_end, clip, src_in, src_out)
SEG = []
def seg(v0, v1, clip, s0, s1): SEG.append((v0, v1, clip, s0, s1))
seg(b(8),  b(12), 'k1', 0.2, 2.4)    # box push-in      -- STORIES, MUSIC & FUN
seg(b(16), b(20), 'k3', 0.3, 2.4)    # stick hero float -- feature 02
seg(b(20), b(24), 'k2', 0.2, 2.2)    # box arc          -- 1 PICK A PAL
seg(b(32), b(36), 'k4', 0.6, 2.6)    # sticks glide     -- PRESS & PLAY! (drop)
seg(b(36), b(44), 'k2', 1.2, 4.9)    # box arc          -- WHY STOCK IT
seg(b(52), b(56), 'k1', 2.5, 4.9)    # box push-in      -- STOCK UP NOW!

CUTS = [(b(4),'chev'),(b(8),'zoom'),(b(12),'chev'),(b(16),'zoom'),(b(20),'chev'),(b(24),'zoom'),
        (b(32),'flash'),(b(36),'chev'),(b(44),'chev'),(b(52),'flash'),(b(56),'flash')]
TAPS = [b(24.6), b(25.6), b(26.6)]     # button presses in step 2
