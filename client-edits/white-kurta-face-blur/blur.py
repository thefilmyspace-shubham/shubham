import json,cv2,numpy as np,subprocess
R=json.load(open('heads2.json'))
cap=cv2.VideoCapture('../sdr.mp4'); W,Hh=1080,1920
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30000/1001','-i','-','-c:v','libx264','-preset','medium','-crf','12','-pix_fmt','yuv420p','../blurred.mp4'],stdin=subprocess.PIPE)
i=0
while True:
    ok,img=cap.read()
    if not ok: break
    mask=np.zeros((Hh,W),np.float32); smax=0
    for g in 'AB':
        h=R[g]['h'][i] if i<len(R[g]['h']) else None
        if h is None: continue
        cx,cy,s=h; k=1.15 if R[g]['src'][i]=='d' else 1.4
        rx=max(s*0.72*k,26); ry=rx*1.3
        cv2.ellipse(mask,(int(cx),int(cy-0.12*s)),(int(rx),int(ry)),0,0,360,1.0,-1); smax=max(smax,rx)
    if smax:
        f=int(smax*0.25)|1; mask=cv2.GaussianBlur(mask,(f*2+1,f*2+1),0)
        ys,xs=np.where(mask>0.01); y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
        pad=int(smax); y0=max(0,y0-pad);x0=max(0,x0-pad);y1=min(Hh,y1+pad);x1=min(W,x1+pad)
        roi=img[y0:y1,x0:x1]
        # pixelate + heavy blur
        bs=max(int(smax/4),6)
        small=cv2.resize(roi,(max(1,roi.shape[1]//bs),max(1,roi.shape[0]//bs)),interpolation=cv2.INTER_AREA)
        pix=cv2.resize(small,(roi.shape[1],roi.shape[0]),interpolation=cv2.INTER_LINEAR)
        kk=int(smax*0.6)|1; bl=cv2.GaussianBlur(pix,(kk,kk),0)
        m=mask[y0:y1,x0:x1,None]
        img[y0:y1,x0:x1]=(roi*(1-m)+bl*m).astype(np.uint8)
    p.stdin.write(img.tobytes()); i+=1
p.stdin.close(); p.wait(); print('frames',i)
