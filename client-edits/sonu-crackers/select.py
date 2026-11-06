import numpy as np, json
SRCD="/tmp/claude-0/-home-user-shubham/d805e061-24d3-576e-8105-e20f5e0d5ddb/scratchpad/src"
HOOK="/home/user/shubham/client-edits/sonu-crackers/hook_fire_kling25.mp4"
def jit(c): return np.load(f"jit/{c}.mp4.npy")
# slot: start,end, candidates in preference order, forced f (or None)
SLOTS=[
(0.00,4.40,["hook_fire_kling25"],"fixed"),
(4.40,6.60,["133826","134018"],None),
(6.60,8.70,["133606","133530"],None),
(8.70,10.00,["133806"],None),
(10.00,11.98,["133818"],None),
(11.98,13.55,["134238"],"fit"),          # only Whistling Wheel clip: slow to fill
(13.55,15.44,["133923a","133923b"],None),
(15.44,16.85,["134301","134344","134316"],None),
(16.85,18.75,["134248"],None),
(18.75,20.40,["133753","134611"],None),
(20.40,21.45,["134032","133633"],None),
(21.45,22.60,["134109","134057","134102"],None),
(22.60,23.65,["133757","133729"],None),
(23.65,25.52,["133412"],None),
(25.52,28.52,["133627"],None),
(28.52,32.00,["133600_fire2"],None),
]
OK=0.45
out=[]
for a,b,cands,forced in SLOTS:
    T=b-a; best=None
    for c in cands:
        j=jit(c); n=len(j); dur=n/60
        if forced=="fixed":
            best=(False,1.0,float(j[:int(T*60)].mean()),c,0.0); break
        fs=[T/((n-1)/60)] if forced=="fit" else [1.0,1.25,1.5,2.0]
        for f in fs:
            need=int(round(T/f*60))
            if need>n-1: continue
            # skip first 6 frames (camera settle) when there is room
            lo=min(6,max(0,n-1-need))
            starts=range(lo,max(lo+1,n-need))
            sc=[(j[s:s+need].mean()/f,s) for s in starts]
            score,s=min(sc)
            cand=(score>OK, f, score, c, s/60)
            if best is None or cand<best: best=cand
            if score<=OK: break
        if best and not best[0]: break   # first preferred clip that is stable enough wins
    _,f,score,c,ss=best
    fn=HOOK if c.startswith("hook") else f"{SRCD}/{c}.mp4"
    out.append([a,b,fn,round(ss,3),round(f,3)])
    print(f"{a:5.2f}-{b:5.2f} {c:14s} ss {ss:4.2f} slow x{f:.2f}  jitter/out-frame {score:.2f}{'  <-- still above target' if score>OK else ''}")
json.dump(out,open("build/seg_v2.json","w"),indent=0)
