import sys, json, numpy as np, cv2
from ultralytics import YOLO
m = YOLO('yolo11m-pose.pt')
cap = cv2.VideoCapture('../sdr.mp4'); out=[]; i=0
for r in m.track(source='../sdr.mp4', stream=True, persist=True, tracker='botsort.yaml', imgsz=1280, conf=0.2, verbose=False, classes=[0]):
    f=[]
    img=r.orig_img
    if r.boxes is not None and len(r.boxes):
        ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else [-1]*len(r.boxes)
        for b,c,tid,kp,kc in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), ids, r.keypoints.xy.cpu().numpy(), r.keypoints.conf.cpu().numpy()):
            x1,y1,x2,y2=b.astype(int); h=y2-y1
            ty1=y1+int(.25*h); ty2=y1+int(.6*h)
            crop=img[max(ty1,0):max(ty2,1), max(x1,0):max(x2,1)]
            if crop.size:
                hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV); white=float(((hsv[...,1]<60)&(hsv[...,2]>150)).mean())
            else: white=0
            f.append(dict(id=int(tid),b=[float(v) for v in b],c=float(c),kp=kp.tolist(),kc=kc.tolist(),w=white))
    out.append(f); i+=1
    if i%200==0: print(i, flush=True)
json.dump(out, open('tracks.json','w'))
