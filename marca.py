#!/usr/bin/env python3
"""marca.py <logo_master.png | splash.png> <marca.png>
Marca d'agua 300x300 com alpha, feita a partir da LOGO MASTER.
Se receber um print de tela (sem alpha), recorta a logo como antes."""
import cv2, numpy as np, sys

ENT, OUT = sys.argv[1], sys.argv[2]
im = cv2.imread(ENT, cv2.IMREAD_UNCHANGED)
if im is None:
    print("ERRO: nao li", ENT); sys.exit(2)
if im.ndim == 2:
    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)

if im.shape[2] == 4:                       # veio a LOGO MASTER: ja tem alpha certo
    bgr = im[:, :, :3].astype(np.float32)
    a   = im[:, :, 3].astype(np.float32) / 255.0
else:                                      # compatibilidade: print da splash
    h, w = im.shape[:2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    y0, y1 = int(h*0.10), int(h*0.95)
    x0, x1 = int(w*0.03), int(w*0.97)
    band = gray[y0:y1, x0:x1]
    caixas = []
    for thr in (50, 38, 28, 20):
        _, th = cv2.threshold(band, thr, 255, cv2.THRESH_BINARY)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25,25), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(th)
        caixas = [st[i] for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 300]
        if caixas: break
    if not caixas:
        print("ERRO: logo nao encontrada"); sys.exit(3)
    bx1 = min(b[0] for b in caixas)+x0; by1 = min(b[1] for b in caixas)+y0
    bx2 = max(b[0]+b[2] for b in caixas)+x0; by2 = max(b[1]+b[3] for b in caixas)+y0
    crop = im[max(0,by1):min(h,by2), max(0,bx1):min(w,bx2)]
    if crop.size == 0:
        print("ERRO: recorte vazio"); sys.exit(3)
    bgr = crop.astype(np.float32)
    g   = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    a   = np.clip((g - 14) / 60.0, 0, 1.0) ** 0.6

# recorte rente ao desenho
ys, xs = np.where(a > 0.10)
if len(xs) > 10:
    bgr = bgr[ys.min():ys.max()+1, xs.min():xs.max()+1]
    a   = a[ys.min():ys.max()+1, xs.min():xs.max()+1]

# encaixa em 300x300 SEM deformar; o resto fica transparente de verdade
S = 300
h, w = a.shape[:2]
s = min(S / w, S / h)
nw, nh = max(1, int(round(w*s))), max(1, int(round(h*s)))
it = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
bgr = cv2.resize(bgr, (nw, nh), interpolation=it)
a   = cv2.resize(a,   (nw, nh), interpolation=it)

saida = np.zeros((S, S, 4), np.float32)
ox, oy = (S-nw)//2, (S-nh)//2
cor = np.clip(bgr * 1.45 + 4, 0, 255)
al  = np.clip(a, 0, 1)
al[al < 0.03] = 0.0
saida[oy:oy+nh, ox:ox+nw, :3] = cor * (al > 0)[..., None]
saida[oy:oy+nh, ox:ox+nw,  3] = al * 255.0 * 0.90
cv2.imwrite(OUT, saida.astype(np.uint8))
print("MARCA OK:", OUT, nw, "x", nh)
