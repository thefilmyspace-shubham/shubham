# Beat grid: "Punked Up Fun" (Mixkit) = 130 BPM. Video t=0 at music bar 22 (40.6875s).
BEAT = 60/130
BAR = 4*BEAT
MUSIC_IN = 0.072115 + 88*BEAT          # 40.6875
def b(n): return n*BEAT                  # video time of beat n
JUMP_V = b(68)                           # music jumps here: bar 39 -> bar 47 (same phrase position)
MUSIC_JUMP_TO = 0.072115 + 188*BEAT      # 86.841
DROP = b(40)                             # big hit after breakdown (music 59.149)
END_HIT = b(72)                          # outro hit (music 88.687)
DUR = 39.0
FPS = 30
W, H = 1080, 1920

# footage segments: (v_start, v_end, shot, src_in, speed)
SEG = []
def seg(v0, v1, shot, src_in, speed=1.0): SEG.append((v0, v1, shot, src_in, speed))
seg(b(8),  b(12), 'hero_b',  10.10, (11.95-10.10)/(b(12)-b(8)))
seg(b(12), b(16), 'table_c', 4.95,  (6.80-4.95)/(b(16)-b(12)))
seg(b(16), b(18), 'nozzle_c',10.20, (11.15-10.20)/(b(18)-b(16)))
seg(b(18), b(20), 'badge_c', 8.92,  (9.88-8.92)/(b(20)-b(18)))
# 20-24 catalogue cards (graphics)
PULL_SPLIT = b(24) + (19.10-18.00)/((19.10-18.00+23.02-22.48)/(b(28)-b(24)))
seg(b(24), PULL_SPLIT, 'pull_b', 18.00, (19.10-18.00)/(PULL_SPLIT-b(24)))
seg(PULL_SPLIT, b(28), 'pull_a', 22.48, (23.02-22.48)/(b(28)-PULL_SPLIT))   # badge is smeared before 22.48
seg(b(28), b(30.6), 'load_c1', 17.10, (18.32-17.10)/(b(30.6)-b(28)))
seg(b(30.6), b(32.4), 'load_c2', 18.88, (19.72-18.88)/(b(32.4)-b(30.6)))
seg(b(32.4), b(36), 'load_b', 21.25, (22.95-21.25)/(b(36)-b(32.4)))
seg(b(36), b(40), 'aim_c', 20.42, (21.52-20.42)/(b(40)-b(36)))
seg(b(40), b(44), 'fire_c', 21.50, (22.52-21.50)/(b(43)-b(40)))
# 44-48 pack card (graphics)
seg(b(48), b(52), 'table_c', 6.90, (8.62-6.90)/(b(52)-b(48)))
seg(b(52), b(56), 'hold_a2', 8.70, (10.55-8.70)/(b(56)-b(52)))
seg(b(56), b(60), 'hold_a1', 7.00, (8.30-7.00)/(b(60)-b(56)))
# 60-68 partner graphic
seg(b(68), b(69.5), 'close_b', 17.00, (17.66-17.00)/(b(69.5)-b(68)))
seg(b(69.5), b(72), 'hold_a3', 14.02, (15.18-14.02)/(b(72)-b(69.5)))
# 72-> end card (graphics)

# transitions (time of cut, kind) -> used for whoosh SFX + wipe graphics
CUTS = [(b(4),'chev'),(b(8),'zoom'),(b(12),'whip'),(b(16),'chev'),(b(18),'zoom'),(b(20),'zoom'),(b(22),'zoom'),
        (b(24),'chev'),(b(28),'whip'),(b(32.4),'zoom'),(b(36),'zoom'),(b(40),'flash'),(b(44),'chev'),(b(48),'whip'),
        (b(52),'whip'),(b(56),'whip'),(b(60),'chev'),(b(68),'flash'),(b(72),'flash')]
