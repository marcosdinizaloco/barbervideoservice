# logo_tela.py <splash.png> <saida_rgba.png>
# Recorta a logo do cliente da tela de abertura do app dele e devolve
# um PNG com fundo transparente, para entrar no lugar da logo antiga.
import cv2, numpy as np, sys
src, out = sys.argv[1], sys.argv[2]
im = cv2.imread(src)
if im is None: raise SystemExit("splash nao encontrada: " + src)
H, W = im.shape[:2]
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
band = g[int(H*0.12):int(H*0.80), :]
box = None
for thr in (50, 38, 28, 20):
    _, th = cv2.threshold(band, thr, 255, cv2.THRESH_BINARY)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((31,31), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(th)
    b = [st[i] for i in range(1,n) if st[i, cv2.CC_STAT_AREA] > 800]
    if b:
        x1 = min(int(s[0]) for s in b); y1 = min(int(s[1]) for s in b)
        x2 = max(int(s[0]+s[2]) for s in b); y2 = max(int(s[1]+s[3]) for s in b)
        box = (x1, y1 + int(H*0.12), x2, y2 + int(H*0.12)); break
if box is None: raise SystemExit("logo nao encontrada na splash")
x1,y1,x2,y2 = box
m = int(max(x2-x1, y2-y1) * 0.04)
x1=max(0,x1-m); y1=max(0,y1-m); x2=min(W,x2+m); y2=min(H,y2+m)
crop = im[y1:y2, x1:x2]
# alpha por luminancia (fundo preto vira transparente)
gg = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
a = np.clip((gg - 10.0) / 60.0, 0, 1.0) ** 0.55
a = cv2.GaussianBlur(a, (3,3), 0)
bgr = np.clip(crop.astype(np.float32) * 1.05, 0, 255)
cv2.imwrite(out, np.dstack([bgr, a*255.0]).astype(np.uint8))
print("LOGO TELA:", out, crop.shape[1], "x", crop.shape[0])
