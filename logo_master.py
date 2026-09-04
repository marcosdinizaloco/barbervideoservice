#!/usr/bin/env python3
"""
logo_master.py <url_ou_arquivo> <pasta_saida> [nome_do_estabelecimento]

FONTE UNICA da identidade visual. Roda UMA vez por barbearia e produz a
LOGO MASTER, que e usada igual no APP, no VIDEO e na ARTE.

  1) baixa a imagem
  2) tira tarjas solidas das bordas (o 800x500 com faixa branca dos lados)
  3) VALIDA: e uma logo, ou e uma fotografia/fachada/banner?
     - fotografia = REJEITADA. Nunca entra no app, no video nem na arte.
  4) avalia a qualidade e, se estiver ruim, restaura (Real-ESRGAN + limpeza
     de cor e de contorno). Nao inventa elementos: so reconstroi o que existe.
  5) remove o fundo e devolve alpha DURO (sem halo, sem quadrado)
  6) recorta rente ao desenho e grava PNG RGBA com os pixels transparentes
     zerados de verdade

Saidas na pasta:
  logo_master.png    <- a unica fonte oficial (RGBA, fundo transparente)
  PREVIA_nao_usar.jpg<- previa sobre preto, so para olho humano; nada le
  logo_master.json   <- veredito e metricas
"""
import sys, os, json, time, urllib.request, urllib.error
import numpy as np, cv2

D               = os.path.dirname(os.path.abspath(__file__))
TOKEN_REPLICATE = os.environ.get('REPLICATE_TOKEN', '')
CHAVE_IA        = os.environ.get('GEMINI_KEY', '')
FONTE           = os.path.join(D, 'Oswald-600.ttf')
LADO_FINAL      = 1600        # lado maior da logo master
ESCALA_ESRGAN   = 4

ORIGEM = sys.argv[1]
OUT    = sys.argv[2]
NOME   = sys.argv[3] if len(sys.argv) > 3 else ''
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------- entrada
def http(url, dados=None, cab=None, timeout=120):
    req = urllib.request.Request(url, data=dados, headers=cab or {})
    return urllib.request.urlopen(req, timeout=timeout).read()

def baixar(src):
    s = str(src)
    if s.startswith('data:'):
        import base64
        return base64.b64decode(s.split(',', 1)[1])
    if s.startswith('http'):
        return http(s, cab={'User-Agent': 'Mozilla/5.0'}, timeout=45)
    return open(s, 'rb').read()

def decodifica(dados):
    im = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None: return None
    if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im

# ------------------------------------------- tarjas solidas (letterbox)
def tirar_tarjas(im):
    """Corta faixas solidas nas bordas (o 800x500 com tarja branca dos lados).
    So corta quando a faixa e MESMO uma tarja: uniforme de verdade E de uma cor
    claramente diferente do miolo. Regiao escura de fotografia nao e tarja."""
    if im is None: return im
    bgr = im[:, :, :3].astype(np.float32)
    h, w = bgr.shape[:2]
    if h < 40 or w < 40: return im

    miolo = bgr[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)].reshape(-1, 3)
    cor_miolo = np.median(miolo, 0)

    def chapada(linha): return float(linha.reshape(-1, 3).std(0).max())
    def perto(c1, c2, lim=20.0):
        return float(np.linalg.norm(np.asarray(c1) - np.asarray(c2))) < lim
    def distinta(c):
        return float(np.linalg.norm(np.asarray(c) - cor_miolo)) > 28.0

    lv, lh = int(h*0.40), int(w*0.40)

    def conta(pega, limite):
        cor = pega(0).reshape(-1,3).mean(0)
        if not distinta(cor): return 0
        n = 0
        while n < limite:
            linha = pega(n)
            if chapada(linha) >= 6.0: break
            if not perto(linha.reshape(-1,3).mean(0), cor): break
            n += 1
        return n

    topo = conta(lambda n: bgr[n],       lv)
    base = conta(lambda n: bgr[h-1-n],   lv)
    esq  = conta(lambda n: bgr[:, n],    lh)
    dir  = conta(lambda n: bgr[:, w-1-n], lh)

    if topo + base + esq + dir == 0: return im
    # sobra de seguranca: a beirada da tarja deixa 2-3 px de transicao que,
    # se ficarem, viram uma linha opaca de ponta a ponta na logo master
    SEG = 3
    if topo: topo += SEG
    if base: base += SEG
    if esq:  esq  += SEG
    if dir:  dir  += SEG
    y1, y2, x1, x2 = topo, h - base, esq, w - dir
    if (y2-y1) < h*0.35 or (x2-x1) < w*0.35: return im
    print('  tarjas removidas: topo %d base %d esq %d dir %d' % (topo, base, esq, dir))
    return np.ascontiguousarray(im[y1:y2, x1:x2])

# ------------------------------------------------------- e uma logo mesmo?
def tem_rosto(bgr):
    try:
        c = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return len(c.detectMultiScale(g, 1.15, 5, minSize=(40, 40))) > 0
    except Exception:
        return False

def metricas(bgr):
    """Numeros que separam arte grafica de fotografia."""
    q = cv2.resize(bgr, (256, 256), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32)
    m  = cv2.blur(g, (5,5)); m2 = cv2.blur(g*g, (5,5))
    planos = float((np.clip(m2 - m*m, 0, None) < 6.0).mean())   # area chapada

    p = cv2.resize(bgr, (160, 160), interpolation=cv2.INTER_AREA)
    k = (p // 32).astype(np.int32)
    chave = k[:,:,0]*64 + k[:,:,1]*8 + k[:,:,2]
    _, c = np.unique(chave, return_counts=True)
    conc = float(np.sort(c)[::-1][:6].sum() / chave.size)        # 6 cores dominam?

    p2 = cv2.resize(bgr, (200, 200), interpolation=cv2.INTER_AREA)
    k2 = (p2 // 24).astype(np.int32)
    cores  = int(len(np.unique(k2[:,:,0]*100 + k2[:,:,1]*10 + k2[:,:,2])))
    bordas = float((cv2.Canny(p2, 60, 160) > 0).mean())

    # tons: arte grafica usa POUCOS tons, repetidos em area grande.
    # fotografia (mesmo escura) espalha o brilho em um degrade continuo.
    gq = cv2.cvtColor(cv2.resize(bgr, (240,240), interpolation=cv2.INTER_AREA),
                      cv2.COLOR_BGR2GRAY)
    hi = np.bincount(gq.ravel(), minlength=256).astype(np.float32); hi /= hi.sum()
    tons = float(np.sort(hi)[::-1][:12].sum())

    return {'planos': round(planos,3), 'concentracao': round(conc,3),
            'cores': cores, 'bordas': round(bordas,3), 'tons': round(tons,3)}

def ia_valida(dados_img, nome):
    """Gemini decide. Retorna True/False, ou None quando nao da para consultar."""
    if not CHAVE_IA: return None
    try:
        import base64
        b64 = base64.b64encode(dados_img).decode()
        pergunta = (
            'Esta imagem e a LOGOMARCA (marca grafica) de "' + (nome or 'um estabelecimento') + '"?\n'
            'Responda SIM apenas se for arte grafica: simbolo, brasao, emblema, monograma '
            'ou nome estilizado desenhado.\n'
            'Responda NAO se for fotografia de qualquer tipo: fachada, vitrine, interior, '
            'ambiente, cadeira, pessoa, corte de cabelo, produto, banner promocional, '
            'cartaz com varias informacoes, print de tela, mapa ou imagem confusa.\n'
            'Na duvida, responda NAO. Responda somente SIM ou NAO.')
        corpo = {"contents": [{"parts": [
                    {"text": pergunta},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
                 "generationConfig": {"temperature": 0, "maxOutputTokens": 5}}
        modelos = ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
        r = None
        for mod in modelos:
            try:
                r = json.loads(http(
                    'https://generativelanguage.googleapis.com/v1beta/models/' + mod +
                    ':generateContent?key=' + CHAVE_IA,
                    json.dumps(corpo).encode(), {'Content-Type': 'application/json'}, timeout=45))
                break
            except urllib.error.HTTPError as e:
                if e.code == 404: continue
                raise
        if r is None:
            print('  IA: nenhum modelo disponivel'); return None
        t = (((r.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0].get('text','')
        t = t.strip().upper()
        if t.startswith('SIM'): return True
        if t.startswith('NAO') or t.startswith('NÃO'): return False
    except Exception as e:
        print('  IA indisponivel:', str(e)[:80])
    return None

def validar(im, dados_originais, nome):
    """(serve, motivo, metricas). Fotografia NUNCA passa."""
    bgr = im[:, :, :3]
    mt  = metricas(bgr)
    rosto = tem_rosto(bgr)
    mt['rosto'] = bool(rosto)

    if not CHAVE_IA:
        print('  ATENCAO: GEMINI_KEY nao configurada. A checagem visual por IA'
              ' esta desligada e a validacao fica so nos sinais graficos.')
    veredito = ia_valida(dados_originais, nome)
    if veredito is True:
        if rosto:
            return False, 'IA aprovou mas ha rosto humano na imagem', mt
        return True, 'aprovada pela IA', mt
    if veredito is False:
        return False, 'a IA classificou como fotografia/material que nao e logo', mt

    # sem IA: decide pelo conjunto de sinais.
    # calibrado com logos reais (Dom Richard: planos .56 conc .85 cores 88 bordas .13)
    # contra fotografia (fachada/interior: planos < .35, conc < .70, cores > 200).
    nota = 0
    nota += 2 if mt['planos'] >= 0.50 else (1 if mt['planos'] >= 0.38 else 0)
    nota += 2 if mt['concentracao'] >= 0.82 else (1 if mt['concentracao'] >= 0.70 else 0)
    nota += 2 if mt['cores'] <= 130 else (1 if mt['cores'] <= 180 else 0)
    nota += 2 if mt['tons'] >= 0.82 else (1 if mt['tons'] >= 0.72 else 0)
    nota += 1 if mt['bordas'] <= 0.15 else 0
    if rosto:             nota -= 4
    if mt['cores'] > 200: nota -= 4
    mt['nota'] = nota
    # porta dura: qualquer um destes reprova sozinho
    if rosto:                     return False, 'ha rosto humano na imagem', mt
    if mt['cores'] > 200:         return False, 'textura de fotografia (%d cores distintas)' % mt['cores'], mt
    if mt['planos'] < 0.38:       return False, 'quase nao ha area chapada (%.2f) - e fotografia' % mt['planos'], mt
    if mt['concentracao'] < 0.70: return False, 'sem cores dominantes (%.2f) - e fotografia' % mt['concentracao'], mt
    if mt['tons'] < 0.72:         return False, 'brilho em degrade continuo (%.2f) - e fotografia' % mt['tons'], mt
    if nota >= 7:
        return True, 'aprovada pelos sinais graficos (nota %d/9)' % nota, mt
    return False, 'sinais insuficientes para garantir que e logo (nota %d/9)' % nota, mt

# --------------------------------------------------------------- qualidade
def qualidade(bgr):
    h, w = bgr.shape[:2]
    lado = min(h, w)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    nit = float(cv2.Laplacian(g, cv2.CV_32F).var())
    # blocagem tipica de JPG: energia nas fronteiras de 8 px
    dv = np.abs(np.diff(g, axis=1))
    bloco = float(dv[:, 7::8].mean() / (dv.mean() + 1e-6))
    ruim = (lado < 420) or (nit < 90) or (bloco > 1.35)
    return {'lado': int(lado), 'nitidez': round(nit,1), 'blocagem': round(bloco,2),
            'ruim': bool(ruim)}

def real_esrgan(url):
    if not TOKEN_REPLICATE or not str(url).startswith('http'): return None
    cab = {'Authorization': 'Bearer ' + TOKEN_REPLICATE,
           'Content-Type': 'application/json', 'Prefer': 'wait'}
    corpo = json.dumps({'input': {'image': url, 'scale': ESCALA_ESRGAN, 'face_enhance': False}}).encode()
    try:
        r = json.loads(http('https://api.replicate.com/v1/models/nightmareai/real-esrgan/predictions',
                            corpo, cab, timeout=180))
    except Exception as e:
        print('  Replicate:', str(e)[:90]); return None
    for _ in range(40):
        if r.get('status') == 'succeeded': break
        if r.get('status') in ('failed', 'canceled'): return None
        time.sleep(3)
        try: r = json.loads(http(r['urls']['get'],
                                 cab={'Authorization': 'Bearer ' + TOKEN_REPLICATE}, timeout=60))
        except Exception: return None
    s = r.get('output')
    if isinstance(s, list): s = s[0] if s else None
    if not s: return None
    try: return decodifica(baixar(s))
    except Exception: return None

def ampliar(bgr, lado=LADO_FINAL):
    h, w = bgr.shape[:2]
    s = lado / max(h, w)
    nw, nh = max(1, int(round(w*s))), max(1, int(round(h*s)))
    if s > 1:
        meio = cv2.resize(bgr, (max(1,int(w*(1+s)/2)), max(1,int(h*(1+s)/2))),
                          interpolation=cv2.INTER_CUBIC)
        out = cv2.resize(meio, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    else:
        out = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    return np.clip(out, 0, 255).astype(np.uint8)

def reconstruir(bgr):
    """Limpa ruido de compressao e refaz os contornos SEM inventar elementos:
       reduz a imagem as suas cores reais e redesenha cada forma com borda limpa."""
    sv = cv2.bilateralFilter(bgr, 9, 60, 60)
    amostra = sv.reshape(-1, 3).astype(np.float32)
    if amostra.shape[0] > 60000:
        idx = np.random.RandomState(7).choice(amostra.shape[0], 60000, replace=False)
        amostra = amostra[idx]
    melhor, K = None, 0
    for k in (3, 4, 5, 6, 8):
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
        erro, _, centros = cv2.kmeans(amostra, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        erro = erro / amostra.shape[0]
        melhor, K = centros, k
        if erro < 90: break
    plano = sv.reshape(-1, 3).astype(np.float32)
    d = ((plano[:, None, :] - melhor[None, :, :])**2).sum(2)
    rot = d.argmin(1).reshape(sv.shape[:2])

    saida = np.zeros_like(sv, np.float32)
    peso  = np.zeros(sv.shape[:2], np.float32)
    nucleo = np.ones((3,3), np.uint8)
    for i in range(K):
        m = (rot == i).astype(np.uint8)*255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  nucleo)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, nucleo)
        mf = cv2.GaussianBlur(m.astype(np.float32)/255.0, (0,0), 0.8)
        mf = np.clip((mf - 0.5)*3.2 + 0.5, 0, 1)          # borda curta e limpa
        saida += mf[..., None] * melhor[i][None, None, :]
        peso  += mf
    peso = np.maximum(peso, 1e-6)
    return np.clip(saida / peso[..., None], 0, 255).astype(np.uint8)

# ------------------------------------------------------- fundo -> alpha duro
def alpha_do_fundo(im):
    """Devolve (bgr, alpha 0..1). Alpha DURO: o que e fundo vira 0 exato."""
    if im.shape[2] == 4 and im[:, :, 3].min() < 250:
        return im[:, :, :3].astype(np.float32), im[:, :, 3].astype(np.float32)/255.0
    bgr = im[:, :, :3].astype(np.float32)
    b = np.concatenate([bgr[:4].reshape(-1,3), bgr[-4:].reshape(-1,3),
                        bgr[:, :4].reshape(-1,3), bgr[:, -4:].reshape(-1,3)])
    cor = np.median(b, 0)
    uniforme = float(np.mean(np.linalg.norm(b - cor, axis=1)))
    if uniforme < 26:                       # borda toda da mesma cor = fundo
        d = np.linalg.norm(bgr - cor, axis=2)
        a = np.clip((d - 22) / 40.0, 0, 1)
    else:                                   # fundo escuro: alpha por luminancia
        g = cv2.cvtColor(np.clip(bgr,0,255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
        a = np.clip((g - 14) / 55.0, 0, 1.0) ** 0.6
    return bgr, a

def limpar_alpha(a):
    """Tira o veu que forma o 'quadrado' atras da logo:
       piso duro, remove manchas soltas e fecha buracos minusculos."""
    a = cv2.GaussianBlur(a.astype(np.float32), (0,0), 0.6)
    PISO = 0.12
    a = np.clip((a - PISO) / (1.0 - PISO), 0, 1)      # tudo abaixo do piso -> 0 exato
    solido = (a > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(solido, 8)
    if n > 1:
        maior = max(st[i, cv2.CC_STAT_AREA] for i in range(1, n))
        limite = max(24, int(maior * 0.0006))
        manter = np.zeros(a.shape, np.uint8)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] >= limite: manter[lab == i] = 1
        manter = cv2.dilate(manter, np.ones((3,3), np.uint8), iterations=2)
        a = a * manter.astype(np.float32)
    a[a < 0.02] = 0.0                                  # zero de verdade
    return a

# ------------------------------------------- emblema quando nao ha logo boa
def logo_texto(nome):
    from PIL import Image, ImageDraw, ImageFont
    nome = (nome or 'BARBEARIA').strip().upper()
    for lixo in ('BARBEARIA', 'BARBER SHOP', 'BARBERSHOP', 'BARBER'):
        if nome != lixo and nome.endswith(' ' + lixo):
            nome = nome[: -len(lixo) - 1].strip()
    palavras = nome.split()
    if len(palavras) > 2:
        meio = (len(palavras)+1)//2
        linhas = [' '.join(palavras[:meio]), ' '.join(palavras[meio:])]
    elif len(palavras) == 2: linhas = palavras
    else: linhas = [nome]

    S = 1024
    img = Image.new('RGBA', (S, S), (0,0,0,0))
    d = ImageDraw.Draw(img)
    BRANCO, OURO = (238,236,232,255), (201,162,92,255)
    cx = cy = S//2
    r1 = int(S*0.455); r2 = int(S*0.415)
    d.ellipse([cx-r1, cy-r1, cx+r1, cy+r1], outline=BRANCO, width=7)
    d.ellipse([cx-r2, cy-r2, cx+r2, cy+r2], outline=OURO,   width=2)

    def fonte(t):
        try: return ImageFont.truetype(FONTE, t)
        except Exception: return ImageFont.load_default()
    tam = 150 if len(linhas) == 1 else 120
    while tam > 30:
        f = fonte(tam)
        if max(d.textbbox((0,0), l, font=f)[2] for l in linhas) < S*0.66: break
        tam -= 4
    f = fonte(tam)
    alt = [d.textbbox((0,0), l, font=f)[3] for l in linhas]
    total = sum(alt) + (18 if len(linhas) > 1 else 0)
    y = cy - total//2 - int(S*0.03)
    for i, l in enumerate(linhas):
        bb = d.textbbox((0,0), l, font=f)
        d.text((cx - (bb[2]-bb[0])//2 - bb[0], y - bb[1]), l, font=f, fill=BRANCO)
        y += alt[i] + 18
    d.line([cx-int(S*0.20), y+8, cx+int(S*0.20), y+8], fill=OURO, width=3)
    fp = fonte(max(20, int(tam*0.30)))
    t = 'B A R B E A R I A'
    bb = d.textbbox((0,0), t, font=fp)
    d.text((cx-(bb[2]-bb[0])//2-bb[0], y+26-bb[1]), t, font=fp, fill=OURO)
    for k, dx in enumerate((-int(S*0.075), 0, int(S*0.075))):
        e = int(S*0.012)
        d.ellipse([cx+dx-e, cy-int(S*0.30)-e, cx+dx+e, cy-int(S*0.30)+e], fill=OURO)
    return np.dstack([np.array(img)[:, :, 2::-1], np.array(img)[:, :, 3]]).astype(np.uint8)

# ================================================================= execucao
info = {'origem': str(ORIGEM)[:200], 'nome': NOME}
try:
    dados = baixar(ORIGEM)
except Exception as e:
    dados = None
    print('nao consegui baixar:', str(e)[:100])

im = decodifica(dados) if dados else None
serve, motivo, mt = False, 'imagem nao pode ser lida', {}

if im is not None:
    im = tirar_tarjas(im)
    serve, motivo, mt = validar(im, dados, NOME)

info['metricas'] = mt
info['valida']   = bool(serve)
info['motivo']   = motivo
print('VALIDACAO:', 'LOGO' if serve else 'REJEITADA', '-', motivo)
print('  metricas:', mt)

if not serve:
    rgba = logo_texto(NOME)
    info['tratamento'] = 'emblema gerado com o nome (a imagem enviada nao e uma logo)'
else:
    q = qualidade(im[:, :, :3])
    info['qualidade'] = q
    print('  qualidade:', q)
    alfa_orig = im[:, :, 3] if im.shape[2] == 4 else None
    base = im[:, :, :3]
    if q['ruim']:
        melhor = real_esrgan(ORIGEM)
        if melhor is not None:
            print('  Real-ESRGAN ok')
            melhor = tirar_tarjas(melhor)
            alfa_orig = melhor[:, :, 3] if melhor.shape[2] == 4 else None
            base = melhor[:, :, :3]
        base = ampliar(base)
        base = reconstruir(base)
        info['tratamento'] = 'logo restaurada (baixa qualidade na origem)'
    else:
        base = ampliar(base)
        info['tratamento'] = 'logo original preservada'
    if alfa_orig is not None:
        alfa_orig = cv2.resize(alfa_orig, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_AREA)
        entrada = np.dstack([base, alfa_orig])
    else:
        entrada = base
    bgr, a = alpha_do_fundo(entrada)
    a = limpar_alpha(a)
    rgba = np.dstack([np.clip(bgr,0,255), a*255.0]).astype(np.uint8)

# recorte rente ao desenho
al = rgba[:, :, 3].astype(np.float32)/255.0
ys, xs = np.where(al > 0.10)
if len(xs) > 20:
    rgba = rgba[ys.min():ys.max()+1, xs.min():xs.max()+1]

# tamanho final + pixels transparentes zerados (nao sobra cor no fundo)
h, w = rgba.shape[:2]
s = LADO_FINAL / max(h, w)
it = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
rgba = cv2.resize(rgba, (max(1,int(round(w*s))), max(1,int(round(h*s)))), interpolation=it)
a = rgba[:, :, 3].astype(np.float32)/255.0
a[a < 0.02] = 0.0
rgba = np.dstack([(rgba[:, :, :3].astype(np.float32) * (a > 0)[..., None]), a*255.0]).astype(np.uint8)

# A LOGO MASTER e SEMPRE PNG com canal alpha. Nunca JPG, nunca sobre fundo.
cv2.imwrite(os.path.join(OUT, 'logo_master.png'), rgba,
            [cv2.IMWRITE_PNG_COMPRESSION, 6])
assert cv2.imread(os.path.join(OUT, 'logo_master.png'),
                  cv2.IMREAD_UNCHANGED).shape[2] == 4, 'logo_master.png saiu sem alpha'
# Previa SO para olho humano. Nenhuma etapa do sistema le este arquivo.
prev = (rgba[:, :, :3].astype(np.float32) * (rgba[:, :, 3:4].astype(np.float32)/255.0))
cv2.imwrite(os.path.join(OUT, 'PREVIA_nao_usar.jpg'), prev.astype(np.uint8),
            [cv2.IMWRITE_JPEG_QUALITY, 92])
info['saida'] = {'arquivo': 'logo_master.png', 'largura': int(rgba.shape[1]), 'altura': int(rgba.shape[0])}
json.dump(info, open(os.path.join(OUT, 'logo_master.json'), 'w'), ensure_ascii=False, indent=2)

print('LOGO MASTER:', rgba.shape[1], 'x', rgba.shape[0], '|', info['tratamento'])
