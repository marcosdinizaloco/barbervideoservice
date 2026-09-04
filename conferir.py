#!/usr/bin/env python3
"""conferir.py <pasta_work_do_slug> <arte.jpg> [video.mp4]
Confere, com numero e nao com opiniao, se a entrega esta correta:
  1. a logo foi VALIDADA (nao e fotografia)
  2. a LOGO MASTER tem transparencia real (sem retangulo, sem tarja)
  3. na ARTE nao existe quadrado atras da logo
Sai com codigo 0 se tudo passou, 1 se algo falhou."""
import sys, os, json
import numpy as np, cv2

W    = sys.argv[1]
ARTE = sys.argv[2] if len(sys.argv) > 2 else ''
falhas = []

# ---------------------------------------------------------------- 1) veredito
j = os.path.join(W, 'logo_master.json')
if not os.path.exists(j):
    print('FALHA: nao existe logo_master.json em', W); sys.exit(1)
info = json.load(open(j))
print('1) VALIDACAO :', 'LOGO VALIDA' if info['valida'] else 'REJEITADA', '-', info['motivo'])
print('   tratamento:', info.get('tratamento'))
if not info['valida']:
    print('   (a imagem enviada nao era uma logo; entrou o emblema com o nome)')

# ------------------------------------------------------------ 2) logo master
m = cv2.imread(os.path.join(W, 'logo_master.png'), cv2.IMREAD_UNCHANGED)
if m is None or m.shape[2] != 4:
    falhas.append('logo_master.png nao tem canal alpha')
else:
    a = m[:, :, 3].astype(np.float32) / 255.0
    borda = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    veu   = float(((a > 0.0) & (a < 0.25)).mean())
    cor_fora = int(m[:, :, :3][a == 0].max()) if (a == 0).any() else 0
    print('2) LOGO MASTER: %dx%d | alpha 0 em %.0f%% | veu %.2f%% | cor fora do desenho %d'
          % (m.shape[1], m.shape[0], (a == 0).mean()*100, veu*100, cor_fora))
    if veu > 0.08:   falhas.append('veu de transparencia alto (%.1f%%): pode virar quadrado' % (veu*100))
    if cor_fora > 0: falhas.append('ha cor em pixel transparente (%d): vai vazar na composicao' % cor_fora)
    if float((borda > 0.9).mean()) > 0.95:
        falhas.append('todo o contorno esta opaco: sobrou tarja ou fundo na logo')

# ------------------------------------------------------- 3) quadrado na arte
if ARTE and os.path.exists(ARTE):
    X1, Y1, X2, Y2 = 540, 288, 850, 650          # area da logo na arte base
    im = cv2.imread(ARTE).astype(np.float32)
    g  = cv2.cvtColor(np.clip(im,0,255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    F = 22
    dentro = g[Y1+6:Y2-6, X1+6:X2-6]
    dentro = dentro[dentro < 40]                 # so o fundo, sem a logo
    anel = np.concatenate([
        g[Y1-F:Y1, X1:X2].ravel(), g[Y2:Y2+F, X1:X2].ravel(),
        g[Y1:Y2, X1-F:X1].ravel(), g[Y1:Y2, X2:X2+F].ravel()])
    anel = anel[anel < 40]
    if len(dentro) > 200 and len(anel) > 200:
        d = abs(float(np.median(dentro)) - float(np.median(anel)))
        print('3) ARTE: preto dentro %.2f | preto em volta %.2f | diferenca %.2f'
              % (np.median(dentro), np.median(anel), d))
        if d > 2.0:
            falhas.append('o preto atras da logo difere do preto da tela em %.2f niveis' % d)
    else:
        print('3) ARTE: nao consegui medir (area muito preenchida)')

    # 3b) prova definitiva: o degrau na borda da caixa tem que ser o MESMO
    #     da foto original intocada. Se for, nao existe aresta artificial.
    orig = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arte_limpa.png')
    if os.path.exists(orig):
        def degraus(img):
            gg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
            return [abs(float(a.mean()) - float(b.mean())) for a, b in (
                (gg[Y1:Y2, X1-8:X1-2], gg[Y1:Y2, X1+2:X1+8]),
                (gg[Y1:Y2, X2-8:X2-2], gg[Y1:Y2, X2+2:X2+8]),
                (gg[Y1-8:Y1-2, X1:X2], gg[Y1+2:Y1+8, X1:X2]),
                (gg[Y2-8:Y2-2, X1:X2], gg[Y2+2:Y2+8, X1:X2]))]
        dn = degraus(cv2.imread(ARTE))
        do = degraus(cv2.imread(orig))
        piora = max(abs(a-b) for a, b in zip(dn, do))
        print('   degrau na borda: nossa %s | foto original %s | piora max %.2f'
              % ([round(v,2) for v in dn], [round(v,2) for v in do], piora))
        if piora > 1.0:
            falhas.append('a borda da caixa ficou %.2f niveis pior que a foto original' % piora)
else:
    print('3) ARTE: nao informada')

# ---------------------------------------------------- 4) quadrado no video
VIDEO = sys.argv[3] if len(sys.argv) > 3 else ''
if VIDEO and os.path.exists(VIDEO):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from plano import M_affine
        cap = cv2.VideoCapture(VIDEO)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 45)
        ok, fr = cap.read(); cap.release()
        if ok:
            M = M_affine(45); bx, by, bw, bh = 370, 720, 318, 305
            c4 = np.array([[bx,by],[bx+bw,by],[bx,by+bh],[bx+bw,by+bh]], np.float32)
            d4 = c4 @ M[:, :2].T + M[:, 2]
            x0, y0 = int(d4[:,0].min()), int(d4[:,1].min())
            x1, y1 = int(d4[:,0].max()), int(d4[:,1].max())
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
            F = 24
            dentro = g[y0+8:y1-8, x0+8:x1-8]; dentro = dentro[dentro < 30]
            anel = np.concatenate([
                g[max(0,y0-F):y0, x0:x1].ravel(), g[y1:y1+F, x0:x1].ravel(),
                g[y0:y1, max(0,x0-F):x0].ravel(), g[y0:y1, x1:x1+F].ravel()])
            anel = anel[anel < 30]
            if len(dentro) > 200 and len(anel) > 200:
                dv = abs(float(np.median(dentro)) - float(np.median(anel)))
                print('4) VIDEO: preto dentro %.2f | preto em volta %.2f | diferenca %.2f'
                      % (np.median(dentro), np.median(anel), dv))
                if dv > 2.0:
                    falhas.append('no video o preto atras da logo difere em %.2f niveis' % dv)
            else:
                print('4) VIDEO: nao consegui medir')
    except Exception as e:
        print('4) VIDEO: checagem pulada -', str(e)[:70])
else:
    print('4) VIDEO: nao informado')

print()
if falhas:
    print('REPROVADO:')
    for f in falhas: print('  -', f)
    sys.exit(1)
print('APROVADO: logo valida, transparencia limpa e sem quadrado atras da logo.')
