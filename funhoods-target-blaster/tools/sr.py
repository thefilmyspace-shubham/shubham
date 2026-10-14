import torch, torch.nn as nn, torch.nn.functional as F, numpy as np, sys, os, time
from PIL import Image
class SRVGG(nn.Module):
    def __init__(s, nf=64, nc=32, up=4):
        super().__init__(); s.up=up
        b=[nn.Conv2d(3,nf,3,1,1), nn.PReLU(nf)]
        for _ in range(nc): b+=[nn.Conv2d(nf,nf,3,1,1), nn.PReLU(nf)]
        b+=[nn.Conv2d(nf,3*up*up,3,1,1)]
        s.body=nn.ModuleList(b); s.upsampler=nn.PixelShuffle(up)
    def forward(s,x):
        o=x
        for l in s.body: o=l(o)
        return s.upsampler(o)+F.interpolate(x,scale_factor=s.up,mode='nearest')
def load(path):
    m=SRVGG(); sd=torch.load(path,map_location='cpu'); m.load_state_dict(sd.get('params',sd)); m.eval(); return m
@torch.inference_mode()
def run(m, img, out_w=1080):
    x=torch.from_numpy(np.asarray(img.convert('RGB'),dtype=np.float32)/255).permute(2,0,1)[None]
    y=m(x).clamp(0,1)
    if out_w:
        oh=round(img.height*out_w/img.width)
        y=F.interpolate(y,size=(oh,out_w),mode='area')
    return Image.fromarray((y[0].permute(1,2,0).numpy()*255+0.5).astype(np.uint8))
if __name__=='__main__':
    # usage: sr.py model in_dir out_dir   (processes all png in in_dir, skipping existing)
    torch.set_num_threads(int(os.environ.get('T','4')))
    m=load(sys.argv[1]); ind, outd = sys.argv[2], sys.argv[3]; os.makedirs(outd,exist_ok=True)
    import warnings; warnings.filterwarnings('ignore')
    fs=sorted(f for f in os.listdir(ind) if f.endswith('.png'))
    sh=os.environ.get('SHARD')
    if sh: i,n=map(int,sh.split('/')); fs=fs[i::n]
    ow=int(os.environ.get('OUTW','1080'))
    traced={}
    for f in fs:
        o=os.path.join(outd,f)
        if os.path.exists(o): continue
        if os.environ.get('JIT','1')=='1':
            im0=Image.open(os.path.join(ind,f)); key=im0.size
            if key not in traced:
                with torch.inference_mode():
                    ex=torch.rand(1,3,im0.height,im0.width)
                    traced[key]=torch.jit.freeze(torch.jit.trace(load(sys.argv[1]).eval(), ex))
            m=traced[key]
        t=time.time(); run(m, Image.open(os.path.join(ind,f)), ow).save(o+'.tmp.png'); os.replace(o+'.tmp.png',o)
        print(f, '%.2fs'%(time.time()-t), flush=True)
