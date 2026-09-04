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

# 1) tira a marca antiga da tela usando a MESMA FOTO com a tela vazia.
#    Nada de inpaint nem de sintetizar fundo: a area recebe os pixels reais
#    de arte_limpa.png, com o nivel casado ao arte_base.png pelo anel em volta,
#    para que nao exista nenhuma aresta. Fora dessa area nada e tocado.
LIMPA = os.path.join(BASE_DIR, 'arte_limpa.png')
limpa = cv2.imread(LIMPA)

FOLGA = 10
bx1, by1 = max(0, X1-FOLGA), max(0, Y1-FOLGA)
bx2, by2 = min(arte.shape[1], X2+FOLGA), min(arte.shape[0], Y2+FOLGA)

if limpa is not None and limpa.shape == arte.shape:
    ANEL = 26
    ax1, ay1 = max(0, bx1-ANEL), max(0, by1-ANEL)
    ax2, ay2 = min(arte.shape[1], bx2+ANEL), min(arte.shape[0], by2+ANEL)
    A_base  = arte[ay1:ay2, ax1:ax2].astype(np.float32)
    A_limpa = limpa[ay1:ay2, ax1:ax2].astype(np.float32)
    hh, ww = A_base.shape[:2]

    dentro = np.zeros((hh, ww), np.uint8)
    dentro[by1-ay1:by2-ay1, bx1-ax1:bx2-ax1] = 1

    # campo de correcao: as duas fotos sao a mesma cena, mas com renderizacao
    # levemente diferente. Onde elas ja batem (fora da marca antiga) medimos a
    # diferenca e a espalhamos suavemente, para o encaixe nao ter degrau nenhum.
    dif = A_base - A_limpa
    valido = (np.abs(dif).max(2) < 8.0).astype(np.float32)
    valido *= (1 - dentro).astype(np.float32) + (dentro.astype(np.float32) * 0)
    corrigida = A_limpa.copy()
    if valido.sum() > 500:
        peso = cv2.GaussianBlur(valido, (0,0), 45.0)
        for c in range(3):
            num = cv2.GaussianBlur(dif[..., c]*valido, (0,0), 45.0)
            campo = num / np.maximum(peso, 1e-4)
            corrigida[..., c] = np.clip(A_limpa[..., c] + campo, 0, 255)

    macio = cv2.GaussianBlur(dentro.astype(np.float32), (0,0), 6.0)[..., None]
    arte[ay1:ay2, ax1:ax2] = np.clip(A_base*(1-macio) + corrigida*macio, 0, 255).astype(np.uint8)
    print('tela limpa: pixels reais de arte_limpa.png, nivel casado pelo anel')
else:
    # sem arte_limpa.png no repo: volta ao metodo de reconstrucao
    print('AVISO: arte_limpa.png nao encontrada — usando reconstrucao do fundo')
    roi = arte[by1:by2, bx1:bx2].astype(np.float32)
    hh, ww = roi.shape[:2]
    g = cv2.cvtColor(arte[Y1:Y2, X1:X2], cv2.COLOR_BGR2GRAY)
    _, m = cv2.threshold(g, 14, 255, cv2.THRESH_BINARY)
    m = cv2.dilate(m, np.ones((5,5), np.uint8), iterations=4)
    alvo = np.zeros((hh, ww), np.uint8)
    alvo[Y1-by1:Y2-by1, X1-bx1:X2-bx1] = (m > 0).astype(np.uint8)
    gr = cv2.cvtColor(np.clip(roi,0,255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    bg = ((alvo == 0) & (gr < 60))
    if bg.sum() > 500:
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32); yy /= hh; xx /= ww
        P = np.stack([np.ones_like(xx), xx, yy, xx*xx, xx*yy, yy*yy], -1)
        macio = cv2.GaussianBlur(alvo.astype(np.float32), (0,0), 2.0)[..., None]
        refeito = roi.copy()
        for c in range(3):
            coef, *_ = np.linalg.lstsq(P[bg], roi[..., c][bg], rcond=None)
            refeito[..., c] = np.clip((P.reshape(-1,6) @ coef).reshape(hh, ww), 0, 255)
        roi = macio*refeito + (1-macio)*roi
    arte[by1:by2, bx1:bx2] = np.clip(roi, 0, 255).astype(np.uint8)

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

# alpha duro: o que nao e logo tem que ser zero exato, senao aparece o quadrado
a[a < 0.06] = 0.0
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
a[a < 0.06] = 0.0
bgr = bgr * (a > 0)[..., None]        # nenhum pixel de cor fora da logo

ox, oy = X1 + (LW - nw) // 2, Y1 + (LH - nh) // 2
dst = arte[oy:oy+nh, ox:ox+nw].astype(np.float32)
al  = a[..., None]
arte[oy:oy+nh, ox:ox+nw] = np.clip(dst * (1 - al) + bgr * al, 0, 255).astype(np.uint8)

cv2.imwrite(SAIDA, arte, [cv2.IMWRITE_JPEG_QUALITY, 92])
print('ARTE PRONTA:', SAIDA, '| logo:', nw, 'x', nh)
