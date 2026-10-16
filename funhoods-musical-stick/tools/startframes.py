import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W,H=1080,1920
rng=np.random.default_rng(5)
def grad(top,bot,h=H,w=W):
    t=np.linspace(0,1,h)[:,None,None]
    return np.repeat(np.array(top,np.float32)*(1-t)+np.array(bot,np.float32)*t,w,1)
def bokeh(img,n,cols,rmin,rmax,ymax,alpha=70,blur=18):
    lay=Image.new('RGBA',img.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
    for i in range(n):
        r=rng.uniform(rmin,rmax); x=rng.uniform(0,img.width); y=rng.uniform(0,ymax)
        d.ellipse((x-r,y-r,x+r,y+r),fill=cols[i%len(cols)]+(alpha,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
def shadow(img,box,alpha=110,blur=30):
    lay=Image.new('RGBA',img.size,(0,0,0,0)); ImageDraw.Draw(lay).ellipse(box,fill=(60,40,30,alpha)); img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
def table(h):
    yy=np.linspace(0,1,h)[:,None]
    base=np.array([226,190,146])*(0.92+0.10*yy[...,None])
    grain=(np.sin(np.linspace(0,60,W)[None,:]+rng.normal(0,0.6,(h,1)))*6)[...,None]
    return Image.fromarray(np.clip(base+grain,0,255).astype(np.uint8))
toys=[(255,214,60),(255,120,120),(120,200,255),(140,230,150),(255,255,255)]
# SF1 open display box on a wooden table
img=Image.fromarray(grad((176,224,250),(232,244,252)).astype(np.uint8)).convert('RGBA')
bokeh(img,26,toys,40,120,1150,alpha=90,blur=26)
img.paste(table(H-1180),(0,1180)); ImageDraw.Draw(img).rectangle((0,1174,W,1182),fill=(200,160,118,255))
box=Image.open('cut/box_open_top.png'); s=900/box.width; box=box.resize((900,int(box.height*s)),Image.LANCZOS)
shadow(img,(60,1540,1020,1690),alpha=130,blur=34); img.alpha_composite(box,(90,1620-box.height))
img.convert('RGB').save('sf/sf1_box_table.png')
# SF2 stick hero
yy,xx=np.mgrid[0:H,0:W]; r=np.sqrt(((xx-W/2)/W)**2+((yy-H*0.45)/H)**2)
c1=np.array([255,236,150]); c2=np.array([255,170,90])
img=Image.fromarray((c1+(c2-c1)*np.clip(r/0.75,0,1)[...,None]).astype(np.uint8)).convert('RGBA')
bokeh(img,22,[(255,255,255),(255,120,120),(120,190,255)],30,90,H,alpha=80,blur=20)
st=Image.open('cut/marshall_clean.png'); s=1500/st.height; st=st.resize((int(st.width*s),1500),Image.LANCZOS).rotate(-8,Image.BICUBIC,expand=True)
shadow(img,(330,1660,750,1760),alpha=90,blur=30); img.alpha_composite(st,(int(W/2-st.width/2),180))
img.convert('RGB').save('sf/sf2_stick.png')
# SF3 close-up of the sticks in the box
box=Image.open('cut/box_open_top.png'); bw,bh=box.size
crop=box.crop((0,int(bh*0.30),bw,bh)); s=W*1.35/crop.width; crop=crop.resize((int(crop.width*s),int(crop.height*s)),Image.LANCZOS)
img=Image.fromarray(grad((176,224,250),(232,244,252)).astype(np.uint8)).convert('RGBA')
bokeh(img,20,toys[:3],40,110,700,alpha=90,blur=26)
img.paste(table(H-1500),(0,1500)); img.alpha_composite(crop,(int(W/2-crop.width/2),1880-crop.height))
img.convert('RGB').save('sf/sf3_sticks_close.png')
