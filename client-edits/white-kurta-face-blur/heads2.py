import json,cv2,numpy as np
from scipy.ndimage import median_filter, gaussian_filter1d
T=json.load(open('tracks.json')); N=len(T)
GROUPS={'A':([(1,0,503),(133,532,577),(143,610,834)], 0, 938, {842:[401,776,40],880:[390,777,40],914:[379,778,40],922:[375,783,40],938:[354,782,40]}),
        'B':([(192,932,992),(211,1010,1034),(225,1046,1205),(294,1251,N-1)], 932, N-1, {1206:[690,742,55],1214:[698,755,55],1222:[700,752,55],1230:[710,755,55],1238:[715,750,55],1246:[700,750,55]})}
def head(d):
    x1,y1,x2,y2=d['b']; h=y2-y1; kp=np.array(d['kp']); kc=np.array(d['kc'])
    f=[i for i in range(5) if kc[i]>0.4]
    sw=np.linalg.norm(kp[5]-kp[6]) if kc[5]>0.4 and kc[6]>0.4 else 0
    s=max(sw*0.85, 0.12*h, 30)
    if f: cx,cy=kp[f,0].mean(),kp[f,1].mean()
    elif sw: cx,cy=(kp[5,0]+kp[6,0])/2,(kp[5,1]+kp[6,1])/2-0.75*sw
    else: cx,cy=(x1+x2)/2,y1+0.08*h
    return [cx,cy,s]
frames=[]
cap=cv2.VideoCapture('../sdr.mp4')
while True:
    ok,img=cap.read()
    if not ok: break
    frames.append(cv2.resize(img,(540,960)))
def run(H,start,idxs):
    c=H[start]; s=c[2]*1.6/2
    box=(int((c[0]-s)/2),int((c[1]-s*0.6)/2),max(int(s),8),max(int(s),8))
    tr=cv2.TrackerCSRT_create(); tr.init(frames[start],box); out={}
    for i in idxs:
        ok,bb=tr.update(frames[i])
        if not ok: break
        x,y,w,h=bb; out[i]=[(x+w/2)*2,(y+h*0.3)*2,c[2]]
    return out
res={}
for g,(segs,A,B,manual) in GROUPS.items():
    H=[None]*N; src=['']*N
    for tid,a,b in segs:
        for i in range(a,b+1):
            for d in T[i]:
                if d['id']==tid: H[i]=head(d); src[i]='d'
    for k,v in manual.items(): H[k]=v; src[k]='m'
    # manual region: linear interp between manual keys (and last det)
    gaps=[];i=A
    while i<=B:
        if H[i] is None:
            j=i
            while j<=B and H[j] is None: j+=1
            gaps.append((i,j-1)); i=j
        else: i+=1
    for a,b in gaps:
        pre=a-1; post=b+1 if b+1<=B else None
        if src[pre]=='m' or (post is not None and src[post]=='m') or b-a<3:
            for i in range(a,b+1):
                t=(i-pre)/((post or b+1)-pre); P=H[pre]; Q=H[post] if post is not None else P
                H[i]=[P[k]*(1-t)+Q[k]*t for k in range(3)]; src[i]='i'
            continue
        fw=run(H,pre,range(a,b+1)); bw=run(H,post,range(b,a-1,-1)) if post is not None else {}
        for i in range(a,b+1):
            t=(i-a+1)/(b-a+2); P=fw.get(i); Q=bw.get(i)
            H[i]=[P[k]*(1-t)+Q[k]*t for k in range(3)] if P and Q else (P or Q); src[i]='t'
    arr=np.full((N,3),np.nan)
    for i in range(A,B+1):
        if H[i]: arr[i]=H[i]
    seg=arr[A:B+1]
    for k in range(3):
        col=seg[:,k]; m=~np.isnan(col)
        col[~m]=np.interp(np.where(~m)[0],np.where(m)[0],col[m]); col=median_filter(col,5); seg[:,k]=gaussian_filter1d(col,2 if k<2 else 6)
    arr[A:B+1]=seg
    res[g]=dict(h=[None if np.isnan(r[0]) else r.tolist() for r in arr],src=src,range=[A,B])
    print(g,'gaps',gaps)
json.dump(res,open('heads2.json','w'))
