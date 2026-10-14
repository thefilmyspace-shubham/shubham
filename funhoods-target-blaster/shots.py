# Verified clean source ranges (seconds) -- product matches catalogue, no morphing.
SRC = {'A': ('src/ai_a.mov', 24), 'B': ('src/ai_b.mov', 24), 'C': ('src/ai_c.mp4', 30)}
SHOTS = {
    'hero_b':   ('B', 10.10, 11.95),
    'table_b':  ('B', 6.10, 8.10),
    'nozzle_c': ('C', 10.20, 11.15),
    'badge_c':  ('C', 8.92, 9.88),
    'pull_b':   ('B', 18.00, 19.10),
    'pull_a':   ('A', 22.48, 23.05),
    'load_c1':  ('C', 17.10, 18.32),
    'load_c2':  ('C', 18.88, 19.72),
    'load_b':   ('B', 21.25, 22.95),
    'aim_c':    ('C', 20.42, 21.52),
    'fire_c':   ('C', 21.52, 23.00),
    'table_c':  ('C', 4.90, 8.65),
    'hold_a1':  ('A', 7.00, 8.30),
    'hold_a2':  ('A', 8.70, 10.58),
    'hold_a3':  ('A', 14.00, 15.20),
    'close_b':  ('B', 17.00, 17.70),
    # v2 (30 s): only B/C shots (A shows 5 darts on the table), no dart-insertion shots
    'pull_b2':  ('B', 17.75, 19.10),
    'lift_b':   ('B', 9.20, 10.10),    # 4 darts on the table, no packaging in frame
    'fire_c1':  ('C', 21.50, 22.40),   # first (single) dart only
}
def frames(shot):
    s, t0, t1 = SHOTS[shot]; fps = SRC[s][1]
    import math
    return s, list(range(int(math.floor(t0*fps)), int(math.ceil(t1*fps))+1))
