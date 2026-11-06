import subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP="/tmp/claude-0/-home-user-shubham/d805e061-24d3-576e-8105-e20f5e0d5ddb/scratchpad"
SRC=f"{SP}/src"; PRJ="/home/user/shubham/client-edits/sonu-crackers"
FONTS="/home/user/shubham/tfs-promo/fonts"
MODE=sys.argv[1]  # preview | final
W,H,FPS,CRF,PRESET=(1080,1920,30,22,"veryfast") if MODE=="preview" else (2160,3840,60,15,"fast")
S=W/1080
TMP=f"{SP}/build/{MODE}"; os.makedirs(TMP,exist_ok=True)
OUT=f"{PRJ}/sonu_crackers_promo_v1_{MODE}.mp4"
# (start,end,file,ss,f) f = slow factor (setpts=f*PTS)
SEG=[
(0.00,4.40,f"{PRJ}/hook_fire_kling25.mp4",0.0,1.0),
(4.40,6.60,f"{SRC}/133826.mp4",0.5,1.0),
(6.60,8.70,f"{SRC}/133606.mp4",0.4,1.0),
(8.70,10.00,f"{SRC}/133806.mp4",0.0,1.0),
(10.00,11.98,f"{SRC}/133818.mp4",2.0,1.0),
(11.98,13.55,f"{SRC}/134238.mp4",0.0,1.7),
(13.55,15.44,f"{SRC}/133923a.mp4",2.5,1.0),
(15.44,16.85,f"{SRC}/134316.mp4",0.0,1.25),
(16.85,18.75,f"{SRC}/134248.mp4",0.5,1.0),
(18.75,20.40,f"{SRC}/133753.mp4",0.6,1.0),
(20.40,21.45,f"{SRC}/133633.mp4",0.0,1.05),
(21.45,22.60,f"{SRC}/134057.mp4",0.5,1.0),
(22.60,23.65,f"{SRC}/133729.mp4",0.1,1.0),
(23.65,25.52,f"{SRC}/133412.mp4",0.0,1.13),
(25.52,28.52,f"{SRC}/133627.mp4",0.1,1.0),
(28.52,32.00,f"{SRC}/133600_fire2.mp4",0.6,1.0),
]
# text events: (start,end,[(text,kind)])  kind: s=small, h=hero
EV=[
(0.25,1.95,[("AAG ABHI LAGI","s"),("NAHI","h"),("HAI...","s")]),
(2.95,4.30,[("PAR","s"),("LAGNE","h"),("WALI HAI.","s")]),
(4.55,6.55,[("IS DIWALI, HAR PACKET","s"),("READY","h")]),
(6.85,8.60,[("BAS EK","s"),("CHINGARI","h"),("KI DER","s")]),
(8.85,11.95,[("BADA MORPANKH","h"),("khule toh aasmaan mor ban jaaye","s")]),
(12.15,15.40,[("WHISTLING WHEEL","h"),("zameen par ghoome, seeti bajaaye","s")]),
(15.60,16.80,[("SARTHI BOMB","h")]),
(16.95,17.80,[("DYNAMITE","h")]),
(17.95,18.75,[("SADDAM","h")]),
(18.90,20.40,[("NAAM HI","s"),("DHAMAKA","h")]),
(20.55,22.40,[("CHAKRI  ANAR  ROCKET","h")]),
(22.45,23.60,[("HAR PACKET MEIN","s"),("ALAG MAZA","h")]),
(23.80,25.40,[("KAHAN SE","s"),("LENA HAI?","h")]),
(25.75,28.45,[("SONU CRACKERS","h"),("DHAMAKA SHURU HONE WALA HAI","s")]),
(28.70,32.00,[("DHYAAN SE, DOOR SE JALANA","s"),("SONU CRACKERS","h"),("RATLAM (M.P.)","s")]),
]
def font(p,sz): return ImageFont.truetype(f"{FONTS}/{p}",int(sz*S))
def spaced(d,xy,t,f,fill,sp=0):
    x,y=xy
    for ch in t:
        d.text((x,y),ch,font=f,fill=fill,anchor="ls"); x+=d.textlength(ch,font=f)+sp
def tw(d,t,f,sp): return sum(d.textlength(c,font=f)+sp for c in t)-sp
def cap(f): return -f.getbbox("H",anchor="ls")[1]
def make_png(i,lines):
    big=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(big)
    items=[]
    for t,k in lines:
        if k=="h":
            sz=210
            while True:
                f=font("Anton.ttf",sz); w=tw(d,t,f,3*S)
                if w<=0.88*W or sz<60: break
                sz-=6
            items.append((t,f,w,"h",3*S))
        else:
            sz=58; f=font("Inter-ExtraBold.ttf",sz); sp=4*S
            while tw(d,t,f,sp)>0.88*W: sz-=3; f=font("Inter-ExtraBold.ttf",sz)
            items.append((t,f,tw(d,t,f,sp),"s",sp))
    gap=34*S
    total=sum(cap(it[1]) for it in items)+gap*(len(items)-1)
    y=H*0.885-total
    shadow=Image.new("RGBA",(W,H),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    herolayer=Image.new("L",(W,H),0); hd=ImageDraw.Draw(herolayer)
    smalllayer=Image.new("L",(W,H),0); sl=ImageDraw.Draw(smalllayer)
    herobox=[]
    for t,f,w,k,sp in items:
        x=(W-w)/2; c=cap(f); base=y+c
        if k=="h":
            spaced(hd,(x,base),t,f,255,sp); spaced(sd,(x,base+6*S),t,f,(0,0,0,235),sp); herobox.append((y,y+c))
        else:
            spaced(sl,(x,base),t,f,255,sp); spaced(sd,(x,base+3*S),t,f,(0,0,0,220),sp)
        y+=c+gap
    shadow=shadow.filter(ImageFilter.GaussianBlur(7*S))
    out=Image.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,0)),shadow)
    if herobox:
        y0=min(b[0] for b in herobox); y1=max(b[1] for b in herobox)
        col=Image.new("RGB",(1,H))
        for yy in range(H):
            tt=min(1,max(0,(yy-y0)/max(1,(y1-y0))))
            col.putpixel((0,yy),(255,int(205-105*tt),int(40-25*tt)))
        grad=col.resize((W,H)).convert("RGBA"); grad.putalpha(herolayer)
        out=Image.alpha_composite(out,grad)
    white=Image.new("RGBA",(W,H),(255,255,255,255)); white.putalpha(smalllayer)
    out=Image.alpha_composite(out,white)
    p=f"{TMP}/t{i}.png"; out.save(p); return p
pngs=[make_png(i,l) for i,(a,b,l) in enumerate(EV)]
cmd=["ffmpeg","-v","error","-y"]
for (a,b,fn,ss,f) in SEG:
    cmd+=["-ss",f"{ss}","-t",f"{(b-a)/f+0.05:.3f}","-i",fn]
nseg=len(SEG)
for i,(a,b,l) in enumerate(EV):
    cmd+=["-loop","1","-framerate",str(FPS),"-t",f"{b-a:.3f}","-i",pngs[i]]
cmd+=["-i",f"{PRJ}/audio_bed_v1.mp3"]
fc=[]
for k,(a,b,fn,ss,f) in enumerate(SEG):
    fc.append(f"[{k}:v]setpts={f}*PTS,fps={FPS},scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,eq=contrast=1.04:saturation=1.08,trim=duration={b-a:.3f},setpts=PTS-STARTPTS[v{k}]")
fc.append("".join(f"[v{k}]" for k in range(nseg))+f"concat=n={nseg}:v=1:a=0[base0]")
cur="base0"
for i,(a,b,l) in enumerate(EV):
    idx=nseg+i; d=b-a
    fc.append(f"[{idx}:v]format=rgba,fade=t=in:st=0:d=0.16:alpha=1,fade=t=out:st={d-0.12:.3f}:d=0.12:alpha=1,setpts=PTS+{a}/TB[t{i}]")
    nxt=f"o{i}"
    fc.append(f"[{cur}][t{i}]overlay=x=0:y='{40*S:.1f}*pow(1-min(1,max(0,(t-{a})/0.22)),2)':eof_action=pass:format=auto[{nxt}]")
    cur=nxt
fc.append(f"[{cur}]format=yuv420p[vout]")
cmd+=["-filter_complex",";".join(fc),"-map","[vout]","-map",f"{nseg+len(EV)}:a","-c:v","libx264","-preset",PRESET,"-crf",str(CRF),"-r",str(FPS),"-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-t","32","-movflags","+faststart",OUT]
print("running",MODE); r=subprocess.run(cmd); print("rc",r.returncode)
