import subprocess, numpy as np, os, json, sys
SRC=sys.argv[1]; OUTJ=sys.argv[2]; files=sys.argv[3:]; os.makedirs('jit',exist_ok=True)
w,h=240,426
def frames(p):
    raw=subprocess.run(["ffmpeg","-v","error","-i",p,"-vf",f"fps=60,scale={w}:{h},format=gray","-f","rawvideo","-"],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8).reshape(-1,h,w).astype(np.float32)
win=np.outer(np.hanning(h),np.hanning(w)).astype(np.float32)
def shift(a,b):
    A=np.fft.rfft2(a*win); B=np.fft.rfft2(b*win)
    R=A*np.conj(B); R/=np.abs(R)+1e-6
    r=np.fft.irfft2(R,s=a.shape); i=np.unravel_index(np.argmax(r),r.shape)
    dy,dx=i
    def sub(c,n,axis):
        a=r[(dy-1)%h,dx] if axis==0 else r[dy,(dx-1)%w]
        b=r[dy,dx]
        cc=r[(dy+1)%h,dx] if axis==0 else r[dy,(dx+1)%w]
        den=a-2*b+cc
        return c+(0.5*(a-cc)/den if abs(den)>1e-9 else 0)
    fy=sub(dy,h,0); fx=sub(dx,w,1)
    fy=fy-h if fy>h/2 else fy; fx=fx-w if fx>w/2 else fx
    return fx,fy
res={}
for f in files:
    F=frames(os.path.join(SRC,f)); F=F-F.mean(axis=(1,2),keepdims=True)
    m=np.array([shift(F[i+1],F[i]) for i in range(len(F)-1)],float)
    # jitter: deviation of per-frame motion from smooth (15-frame) motion, in output-1080 px
    k=15; ker=np.ones(k)/k
    sm=np.stack([np.convolve(m[:,j],ker,'same') for j in range(2)],1)
    jit=np.linalg.norm(m-sm,axis=1)*(1080/w)
    pan=np.linalg.norm(sm,axis=1)*(1080/w)
    # best 1.0s window
    n=60; best=(1e9,0)
    if len(jit)>n:
        c=np.convolve(jit,np.ones(n)/n,'valid'); i=int(np.argmin(c)); best=(float(c[i]),i/60)
    np.save(f'jit/{f}.npy',jit); res[f]=dict(dur=len(F)/60,jit=float(jit.mean()),jit_p90=float(np.percentile(jit,90)),pan=float(pan.mean()),best1s=best[0],best_at=best[1])
    print(f"{f:22s} dur {len(F)/60:4.2f} jitter {jit.mean():5.2f}px p90 {np.percentile(jit,90):5.2f} drift {pan.mean():5.2f}px/f  best1s {best[0]:5.2f}@{best[1]:.2f}",flush=True)
np.save("jit_dummy.npy",np.zeros(1))
json.dump(res,open(OUTJ,"w"),indent=1)
