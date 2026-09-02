#!/usr/bin/env python3
"""marca.py <splash.png> <marca.png>
Recorta a logo da tela de abertura e gera a marca d'agua 300x300 com alpha,
com o mesmo tratamento do video aprovado (realce + alpha por luminancia)."""
import cv2, numpy as np, sys

SPLASH, OUT = sys.argv[1], sys.argv[2]
fr = cv2.imread(SPLASH)
if fr is None: print("ERRO: nao li", SPLASH); sys.exit(2)
h, w = fr.shape[:2]
gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)

y0, y1 = int(h*0.25), int(h*0.90)
x0, x1 = int(w*0.05), int(w*0.95)
band = gray[y0:y1, x0:x1]
boxes = []
for thr in (50, 38, 28):
    _, th = cv2.threshold(band, thr, 255, cv2.THRESH_BINARY)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25,25), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(th)
    boxes = [st[i] for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 300]
    if boxes: break

if boxes:
    bx1 = min(b[0] for b in boxes)+x0; by1 = min(b[1] for b in boxes)+y0
    bx2 = max(b[0]+b[2] for b in boxes)+x0; by2 = max(b[1]+b[3] for b in boxes)+y0
    cx, cy = (bx1+bx2)//2, (by1+by2)//2
    r = int(max(bx2-bx1, by2-by1) * 0.62)
else:
    cx, cy, r = w//2, int(h*0.58), int(w*0.35)

r = max(r, 40)
crop = fr[max(0,cy-r):min(h,cy+r), max(0,cx-r):min(w,cx+r)]
if crop.size == 0 or float(crop.mean()) < 6.0:
    print("ERRO: logo nao encontrada"); sys.exit(3)

S = 300
lg = cv2.resize(crop, (S, S), interpolation=cv2.INTER_LANCZOS4)
bgr = np.clip(lg.astype(np.float32)*1.60 + 6, 0, 255)
g = cv2.cvtColor(bgr.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
a = np.clip((g - 16)/148, 0, 1.0) ** 0.60
a = cv2.GaussianBlur(a, (3,3), 0) * 0.90
cv2.imwrite(OUT, np.dstack([bgr, a*255.0]).astype(np.uint8))
print("MARCA OK:", OUT)
