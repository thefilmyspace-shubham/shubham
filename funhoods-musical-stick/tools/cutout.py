import os, sys, time
os.environ['U2NET_HOME'] = sys.argv[1]
from rembg import remove, new_session
from PIL import Image
sess = new_session('birefnet-general')
# args: models_dir then triples src x0,y0,x1,y1 dst
args = sys.argv[2:]
for i in range(0, len(args), 3):
    src, box, dst = args[i], tuple(int(v) for v in args[i+1].split(',')), args[i+2]
    t = time.time()
    im = Image.open(src).convert('RGB').crop(box)
    out = remove(im, session=sess, post_process_mask=True)
    out = out.crop(out.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    out.save(dst); print(dst, out.size, '%.1fs' % (time.time() - t), flush=True)
