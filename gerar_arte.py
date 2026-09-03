# gerar_arte.py <url_ou_arquivo_da_logo> <saida.jpg>
# Troca a logo dentro da tela do celular na arte de prospeccao,
# mantendo todo o resto da tela (textos, icones e botao).
import sys, os, urllib.request, numpy as np, cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTE     = os.path.join(BASE_DIR, 'arte_base.png')

# ==================== AJUSTES ====================
X1, Y1, X2, Y2 = 540, 288, 850, 650   # area da logo antiga dentro da tela
ANGULO   = -7.2                        # inclinacao do celular (medida pelo botao da tela)
OCUPACAO = 0.94                        # quanto da area a logo ocupa
# =================================================

LOGO, SAIDA = sys.argv[1], sys.argv[2]

def carregar(src):
    if str(src).startswith('http'):
        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
        d = urllib.request.urlopen(req, timeout=30).read()
        im = cv2.imdecode(np.frombuffer(d, np.uint8), cv2.IMREAD_UNCHANGED)
    else:
        im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
    if im is None: raise SystemExit('nao abri a imagem: ' + str(src))
    return im

arte = cv2.imread(ARTE)
if arte is None: raise SystemExit('falta arte_base.png em ' + BASE_DIR)

# 1) apaga a logo antiga e reconstroi o fundo da tela
roi = arte[Y1:Y2, X1:X2]
g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
_, m = cv2.threshold(g, 32, 255, cv2.THRESH_BINARY)
m = cv2.dilate(m, np.ones((5, 5), np.uint8), iterations=3)
mask = np.zeros(arte.shape[:2], np.uint8)
mask[Y1:Y2, X1:X2] = m
arte = cv2.inpaint(arte, mask, 7, cv2.INPAINT_TELEA)

# 2) prepara a logo do cliente
logo = carregar(LOGO)
if logo.ndim == 2: logo = cv2.cvtColor(logo, cv2.COLOR_GRAY2BGR)
if logo.shape[2] == 4:
    a   = logo[:, :, 3].astype(np.float32) / 255.0
    bgr = logo[:, :, :3].astype(np.float32)
else:
    bgr = logo.astype(np.float32)
    gl  = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY).astype(np.float32)
    a   = np.clip((gl - 12) / 55.0, 0, 1.0) ** 0.6
    a   = cv2.GaussianBlur(a, (3, 3), 0)

ys, xs = np.where(a > 0.12)
if len(xs) > 20:
    bgr = bgr[ys.min():ys.max()+1, xs.min():xs.max()+1]
    a   = a[ys.min():ys.max()+1, xs.min():xs.max()+1]

LW, LH = X2 - X1, Y2 - Y1
s = min(LW * OCUPACAO / bgr.shape[1], LH * OCUPACAO / bgr.shape[0])
nw, nh = max(1, int(bgr.shape[1] * s)), max(1, int(bgr.shape[0] * s))
it = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
bgr = cv2.resize(bgr, (nw, nh), interpolation=it)
a   = cv2.resize(a,   (nw, nh), interpolation=it)

M = cv2.getRotationMatrix2D((nw / 2, nh / 2), ANGULO, 1.0)
bgr = cv2.warpAffine(bgr, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
a   = cv2.warpAffine(a,   M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=0)

ox, oy = X1 + (LW - nw) // 2, Y1 + (LH - nh) // 2
dst = arte[oy:oy+nh, ox:ox+nw].astype(np.float32)
al  = a[..., None]
arte[oy:oy+nh, ox:ox+nw] = np.clip(dst * (1 - al) + bgr * al, 0, 255).astype(np.uint8)

cv2.imwrite(SAIDA, arte, [cv2.IMWRITE_JPEG_QUALITY, 92])
print('ARTE PRONTA:', SAIDA, '| logo:', nw, 'x', nh)
