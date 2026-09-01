# render.py <base.mp4> <marcas.json> <logo_cliente_rgba.png> <marca_dagua.png> <nome> <saida.mp4>
# Passe unico:
#   1) troca a logo da abertura dentro da tela do celular pela logo do cliente
#   2) troca o nome no titulo "BEM-VINDO A ..."
#   3) aplica a marca d'agua ABAIXO do celular
#   4) ja entrega no tamanho que o WhatsApp aceita
import cv2, numpy as np, json, sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plano import M_affine, OUT_W, OUT_H, FPS_OUT
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
BASE, MARCAS, LOGO, WM, NOME, OUT = sys.argv[1:7]
FONT = os.path.join(D, 'Oswald-600.ttf')

SS      = 2      # super-amostragem: desenha em 2x para a logo sair nitida
WM_H    = 215    # altura da marca d'agua
WM_Y    = 1696   # fica abaixo da tela do celular em todos os quadros

marcas = json.load(open(MARCAS))
T_logo = cv2.imread(os.path.join(D, 'logo_antiga.png')).astype(np.float32)
T_txt  = cv2.imread(os.path.join(D, 'texto_antigo.png')).astype(np.float32)
cli    = cv2.imread(LOGO, cv2.IMREAD_UNCHANGED)
wm     = cv2.imread(WM,  cv2.IMREAD_UNCHANGED)
COR    = np.percentile(T_txt.reshape(-1,3), 99.5, axis=0)
TXT    = (NOME.strip().upper() + '.') if NOME.strip() else ''

if wm is not None:
    s = WM_H / wm.shape[0]
    wm = cv2.resize(wm, (int(round(wm.shape[1]*s)), WM_H), interpolation=cv2.INTER_AREA)

def nitidez(img, amt=0.55):
    b = cv2.GaussianBlur(img, (0,0), 1.0)
    return np.clip(img + (img-b)*amt, 0, 255)

def encaixar(rgba, w, h):
    sh, sw = rgba.shape[:2]
    s = min(w/sw, h/sh)
    nw, nh = max(1,int(round(sw*s))), max(1,int(round(sh*s)))
    it = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    r = cv2.resize(rgba, (nw, nh), interpolation=it).astype(np.float32)
    out = np.zeros((h, w, 3), np.float32)
    a = r[:,:,3:4]/255.0
    ox, oy = (w-nw)//2, (h-nh)//2
    out[oy:oy+nh, ox:ox+nw] = nitidez(r[:,:,:3]*a)
    return out

def render_txt(txt, cap_h, maxw):
    size = max(8, int(cap_h/0.72))
    for _ in range(10):
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox('M'); h = b[3]-b[1]
        if h == cap_h: break
        size = max(8, size + (1 if h < cap_h else -1))
    f = ImageFont.truetype(FONT, size)
    bb = f.getbbox(txt)
    im = Image.new('L', (bb[2]-bb[0]+4, bb[3]-bb[1]+4), 0)
    ImageDraw.Draw(im).text((-bb[0], -bb[1]), txt, font=f, fill=255)
    m = np.array(im).astype(np.float32)/255.0
    if m.shape[1] > maxw:
        s = maxw/m.shape[1]
        m = cv2.resize(m, (int(m.shape[1]*s), max(1,int(m.shape[0]*s))))
    return m[:,:,None]*COR[None,None,:]

TXT_IMG = render_txt(TXT, 27, 358) if TXT else None

def somar(dst, delta, M, bx, by, ss=1):
    """Soma um patch (definido em coordenadas do mundo) usando a mesma camera
    do video, para acompanhar o movimento do celular."""
    h, w = delta.shape[:2]
    Mp = np.zeros((2,3), np.float32)
    Mp[:, :2] = M[:, :2] / float(ss)
    Mp[0, 2] = M[0,0]*bx + M[0,1]*by + M[0,2]
    Mp[1, 2] = M[1,0]*bx + M[1,1]*by + M[1,2]
    c = np.array([[0,0],[w,0],[0,h],[w,h]], np.float32)
    d = c @ Mp[:,:2].T + Mp[:,2]
    x0 = max(0,int(d[:,0].min())-2); y0 = max(0,int(d[:,1].min())-2)
    x1 = min(OUT_W,int(d[:,0].max())+3); y1 = min(OUT_H,int(d[:,1].max())+3)
    if x1 <= x0 or y1 <= y0: return
    Ms = Mp.copy(); Ms[0,2] -= x0; Ms[1,2] -= y0
    wd = cv2.warpAffine(delta, Ms, (x1-x0, y1-y0), flags=cv2.INTER_AREA,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    dst[y0:y1, x0:x1] = np.clip(dst[y0:y1,x0:x1].astype(np.float32)+wd, 0, 255).astype(np.uint8)

cache = {}
def peca_logo(w, h):
    key = (w, h)
    if key not in cache:
        old = cv2.resize(T_logo, (w*SS, h*SS), interpolation=cv2.INTER_CUBIC)
        new = encaixar(cli, w*SS, h*SS) if cli is not None else old.copy()
        po = float(np.percentile(old, 99.5)); pn = float(np.percentile(new, 99.5))
        r = (po + 1e-6) / (pn + 1e-6)
        cache[key] = (new*min(max(r, 0.35), 2.0), old)
    return cache[key]

def peca_nome():
    if 'N' not in cache:
        old = T_txt
        W_ = max(old.shape[1], (TXT_IMG.shape[1]+2) if TXT_IMG is not None else 0)
        H_ = max(old.shape[0], (TXT_IMG.shape[0]+4) if TXT_IMG is not None else 0)
        d = np.zeros((H_, W_, 3), np.float32)
        d[:old.shape[0], :old.shape[1]] -= old
        if TXT_IMG is not None:
            th, tw = TXT_IMG.shape[:2]
            d[2:2+th, 0:tw] += TXT_IMG
        cache['N'] = d
    return cache['N']

cap = cv2.VideoCapture(BASE)
cmd = ["ffmpeg","-y","-loglevel","error",
       "-f","rawvideo","-vcodec","rawvideo","-s",f"{OUT_W}x{OUT_H}",
       "-pix_fmt","bgr24","-r",str(FPS_OUT),"-i","pipe:0","-i",BASE,
       "-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","26",
       "-maxrate","1200k","-bufsize","2400k","-pix_fmt","yuv420p",
       "-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest", OUT]
pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)

wm_a = (wm[:,:,3:4]/255.0) if (wm is not None and wm.shape[2]==4) else None
WX = (OUT_W - wm.shape[1])//2 if wm is not None else 0
fi = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    ent = marcas.get(str(fi))
    if ent:
        M = M_affine(fi)
        for e in ent:
            x, y, w, h = e["b"]; k = float(e.get("a",1.0))
            if e["k"] == "logo":
                an = float(e.get("an", k))
                new, old = peca_logo(w, h)
                somar(fr, new*an - old*k, M, x, y, ss=SS)
            elif e["k"] == "nome" and TXT_IMG is not None:
                somar(fr, peca_nome()*k, M, x, y)
    if wm_a is not None:
        hh, ww = wm.shape[:2]
        roi = fr[WM_Y:WM_Y+hh, WX:WX+ww].astype(np.float32)
        fr[WM_Y:WM_Y+hh, WX:WX+ww] = np.clip(roi*(1-wm_a)+wm[:,:,:3]*wm_a,0,255).astype(np.uint8)
    pipe.stdin.write(fr.tobytes())
    fi += 1
pipe.stdin.close(); pipe.wait()
print("RENDER OK:", OUT, fi, "frames")
