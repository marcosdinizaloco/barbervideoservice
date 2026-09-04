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
FAIXA_Y = 1694   # topo da faixa preta (logo abaixo da tela do celular)
WM_H    = 186    # altura da marca d'agua dentro da faixa
WM_Y    = FAIXA_Y + (OUT_H - FAIXA_Y - WM_H)//2   # logo centralizada na faixa

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

FOLGA = 0.96   # a logo nunca encosta na borda da caixa: sem risco de linha

def encaixar(rgba, w, h):
    sh, sw = rgba.shape[:2]
    s = min(w/sw, h/sh) * FOLGA
    nw, nh = max(1,int(round(sw*s))), max(1,int(round(sh*s)))
    it = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    r = cv2.resize(rgba, (nw, nh), interpolation=it).astype(np.float32)
    if r.ndim == 2: r = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_GRAY2BGR).astype(np.float32)
    out = np.zeros((h, w, 3), np.float32)
    a = (r[:,:,3:4]/255.0) if r.shape[2] == 4 else np.ones((nh, nw, 1), np.float32)
    a = np.where(a < 0.02, 0.0, a)             # alpha duro: nada de veu retangular
    ox, oy = (w-nw)//2, (h-nh)//2
    out[oy:oy+nh, ox:ox+nw] = r[:,:,:3]*a
    # o realce e feito na tela inteira do patch: o estouro cai no preto,
    # e nao vira uma linha na aresta da caixa
    return nitidez(out)

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

def colar(dst, M, bx, by, w, h):
    """Apaga o DESENHO antigo dentro de uma area, sem tocar no resto da tela.
    Nada de tapar a caixa inteira: isso deixava um retangulo de preto diferente.
    Aqui a mascara e o proprio desenho antigo (pixels claros), e o buraco e
    preenchido com o degrade e o grao da tela em volta."""
    Mp = M.copy()
    Mp[0,2] = M[0,0]*bx + M[0,1]*by + M[0,2]
    Mp[1,2] = M[1,0]*bx + M[1,1]*by + M[1,2]
    c4 = np.array([[0,0],[w,0],[0,h],[w,h]], np.float32)
    d = c4 @ Mp[:,:2].T + Mp[:,2]
    FOLGA_PX = 24
    x0 = max(0, int(d[:,0].min())-FOLGA_PX); y0 = max(0, int(d[:,1].min())-FOLGA_PX)
    x1 = min(OUT_W, int(d[:,0].max())+FOLGA_PX); y1 = min(OUT_H, int(d[:,1].max())+FOLGA_PX)
    if x1-x0 < 8 or y1-y0 < 8: return

    Ms = Mp.copy(); Ms[0,2] -= x0; Ms[1,2] -= y0
    quad = cv2.warpAffine(np.ones((h, w), np.float32), Ms, (x1-x0, y1-y0),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    dentro = quad > 0.5
    if dentro.sum() < 64: return

    roi = dst[y0:y1, x0:x1].astype(np.float32)
    hh, ww = roi.shape[:2]
    g = roi.mean(2)

    nivel = float(np.median(g[dentro]))
    alvo = dentro & (g > nivel + 3.0) & (g > 5.0)          # o desenho antigo
    if alvo.sum() < 30: return                             # nao ha o que apagar
    alvo = cv2.dilate(alvo.astype(np.uint8), np.ones((5,5), np.uint8), iterations=2) > 0
    alvo = alvo & dentro

    bg = (dentro & ~alvo) & (g < 90)                       # tela limpa em volta
    if bg.sum() < 200:
        bg = (~alvo) & (g < 90)
    if bg.sum() < 200: return

    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    yy /= hh; xx /= ww
    A = np.stack([np.ones_like(xx), xx, yy, xx*xx, xx*yy, yy*yy], -1)
    Af = A[bg]

    bgu = bg.astype(np.uint8)
    _, rot = cv2.distanceTransformWithLabels(1 - bgu, cv2.DIST_L2, 3,
                                             labelType=cv2.DIST_LABEL_PIXEL)
    iy, ix = np.where(bgu > 0)
    ordem = rot[bgu > 0]
    n = int(rot.max()) + 1
    my = np.zeros(n, np.int32); mx = np.zeros(n, np.int32)
    my[ordem] = iy; mx[ordem] = ix
    py, px = np.mgrid[0:hh, 0:ww]
    ny, nx = my[rot], mx[rot]
    sy = np.clip(2*ny - py, 0, hh-1); sx = np.clip(2*nx - px, 0, ww-1)
    fora = bgu[sy, sx] == 0
    sy = np.where(fora, ny, sy); sx = np.where(fora, nx, sx)

    macio = cv2.GaussianBlur(alvo.astype(np.float32), (0,0), 2.0)[..., None]
    novo = roi.copy()
    for c in range(3):
        coef, *_ = np.linalg.lstsq(Af, roi[..., c][bg], rcond=None)
        est = (A.reshape(-1,6) @ coef).reshape(hh, ww)
        res = roi[..., c] - est
        novo[..., c] = np.clip(est + res[sy, sx], 0, 255)
    saida = roi*(1-macio) + novo*macio
    dst[y0:y1, x0:x1] = np.clip(saida, 0, 255).astype(np.uint8)

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
            if e["k"] == "cobrir":
                colar(fr, M, x, y, w, h)
            elif e["k"] == "logo":
                # 1) cobre a area da logo antiga com o proprio preto da tela
                #    (nada de subtracao, que deixava fantasma e retangulo)
                colar(fr, M, x, y, w, h)
                # 2) soma SO os pixels da logo master
                an = float(e.get("an", k))
                if an > 0.001:
                    new, _ = peca_logo(w, h)
                    somar(fr, new*an, M, x, y, ss=SS)
            elif e["k"] == "nome" and TXT_IMG is not None:
                somar(fr, peca_nome()*k, M, x, y)
    # faixa preta chapada no rodape: a logo assenta nela, nunca sobre a mao
    fr[FAIXA_Y:] = 0
    if wm_a is not None:
        hh, ww = wm.shape[:2]
        roi = fr[WM_Y:WM_Y+hh, WX:WX+ww].astype(np.float32)
        fr[WM_Y:WM_Y+hh, WX:WX+ww] = np.clip(roi*(1-wm_a)+wm[:,:,:3]*wm_a,0,255).astype(np.uint8)
    pipe.stdin.write(fr.tobytes())
    fi += 1
pipe.stdin.close(); pipe.wait()
print("RENDER OK:", OUT, fi, "frames")
