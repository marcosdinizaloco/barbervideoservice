# logo_prospec.py <url_ou_arquivo_da_logo> <pasta_saida> [nome_da_barbearia]
# 1) baixa e aumenta a resolucao da logo (Real-ESRGAN se houver token)
# 2) tira o fundo solido, quando existir
# 3) se a imagem nao servir como logo (foto, cena, rosto), desenha uma
#    logo tipografica com o nome da barbearia — sempre entrega algo bom
import sys, os, json, time, math, urllib.request, urllib.error
import numpy as np, cv2

D = os.path.dirname(os.path.abspath(__file__))
TOKEN_REPLICATE = os.environ.get('REPLICATE_TOKEN', '')
CHAVE_IA        = os.environ.get('GEMINI_KEY', '')
FONTE           = os.path.join(D, 'Oswald-600.ttf')
LADO            = 1024
ESCALA          = 4

LOGO = sys.argv[1]
OUT  = sys.argv[2]
NOME = sys.argv[3] if len(sys.argv) > 3 else ''
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- utilidades
def http(url, dados=None, cab=None, timeout=120):
    req = urllib.request.Request(url, data=dados, headers=cab or {})
    return urllib.request.urlopen(req, timeout=timeout).read()

def baixar(src):
    if str(src).startswith('http'):
        return http(src, cab={'User-Agent': 'Mozilla/5.0'}, timeout=45)
    return open(src, 'rb').read()

def decodifica(dados):
    im = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None: return None
    if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im

# ------------------------------------------------- vale como logo, ou nao?
def tem_rosto(bgr):
    try:
        c = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return len(c.detectMultiScale(g, 1.15, 5, minSize=(40, 40))) > 0
    except Exception:
        return False

def parece_foto(bgr):
    p = cv2.resize(bgr, (200, 200), interpolation=cv2.INTER_AREA)
    q = (p // 24).astype(np.int32)
    cores = len(np.unique(q[:, :, 0]*100 + q[:, :, 1]*10 + q[:, :, 2]))
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV)
    sat = float(hsv[:, :, 1].mean())
    bordas = float((cv2.Canny(p, 60, 160) > 0).mean())
    # foto: muita cor distinta + saturacao media alta + textura por toda parte
    # medido: logo limpa fica perto de 100 cores; foto passa de 250
    return cores > 210 or (cores > 150 and bordas > 0.18)

def ia_aprova(dados_img, nome):
    if not CHAVE_IA: return None          # sem chave: decide pela heuristica
    try:
        b64 = __import__('base64').b64encode(dados_img).decode()
        corpo = {
            "contents": [{"parts": [
                {"text": 'Esta imagem serve como LOGOMARCA de "' + nome + '" para aparecer '
                         'na tela de um celular? Responda SIM apenas se for arte grafica '
                         '(simbolo, brasao ou nome estilizado). Responda NAO se for '
                         'fotografia, fachada, ambiente, pessoa, corte de cabelo, '
                         'print de tela ou imagem confusa. Responda so SIM ou NAO.'},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 5}
        }
        r = json.loads(http(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + CHAVE_IA,
            json.dumps(corpo).encode(), {'Content-Type': 'application/json'}, timeout=45))
        t = (((r.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0].get('text', '')
        t = t.strip().upper()
        if t.startswith('SIM'): return True
        if t.startswith('NAO') or t.startswith('NÃO'): return False
    except Exception as e:
        print('IA indisponivel:', str(e)[:80])
    return None

# ------------------------------------------------------------- Real-ESRGAN
def real_esrgan(url):
    if not TOKEN_REPLICATE or not str(url).startswith('http'): return None
    cab = {'Authorization': 'Bearer ' + TOKEN_REPLICATE,
           'Content-Type': 'application/json', 'Prefer': 'wait'}
    corpo = json.dumps({'input': {'image': url, 'scale': ESCALA, 'face_enhance': False}}).encode()
    try:
        r = json.loads(http('https://api.replicate.com/v1/models/nightmareai/real-esrgan/predictions',
                            corpo, cab, timeout=180))
    except Exception as e:
        print('Replicate:', str(e)[:80]); return None
    for _ in range(40):
        if r.get('status') == 'succeeded': break
        if r.get('status') in ('failed', 'canceled'): return None
        time.sleep(3)
        try: r = json.loads(http(r['urls']['get'], cab={'Authorization': 'Bearer ' + TOKEN_REPLICATE}, timeout=60))
        except Exception: return None
    s = r.get('output')
    if isinstance(s, list): s = s[0] if s else None
    if not s: return None
    try: return decodifica(baixar(s))
    except Exception: return None

def ampliar(im):
    alfa = im[:, :, 3] if (im.ndim == 3 and im.shape[2] == 4) else None
    im = im[:, :, :3]
    h, w = im.shape[:2]
    s = LADO / max(h, w)
    nw, nh = max(1, int(round(w*s))), max(1, int(round(h*s)))
    if s > 1:
        meio = cv2.resize(im, (max(1,int(w*(1+s)/2)), max(1,int(h*(1+s)/2))), interpolation=cv2.INTER_CUBIC)
        im = cv2.resize(meio, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    else:
        im = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA)
    f = im.astype(np.float32)
    suave = cv2.bilateralFilter(np.clip(f,0,255).astype(np.uint8), 5, 40, 40).astype(np.float32)
    out = np.clip(suave + (suave - cv2.GaussianBlur(suave,(0,0),1.1)) * 0.85, 0, 255).astype(np.uint8)
    if alfa is not None:
        alfa = cv2.resize(alfa, (out.shape[1], out.shape[0]), interpolation=cv2.INTER_AREA)
        out = np.dstack([out, alfa])
    return out

# ------------------------------------------------- fundo solido -> transparente
def recortar_fundo(im):
    if im.shape[2] == 4 and im[:, :, 3].min() < 250:
        return im[:, :, :3].astype(np.float32), im[:, :, 3].astype(np.float32)/255.0
    bgr = im[:, :, :3].astype(np.float32)
    h, w = bgr.shape[:2]
    b = np.concatenate([bgr[:4].reshape(-1,3), bgr[-4:].reshape(-1,3),
                        bgr[:, :4].reshape(-1,3), bgr[:, -4:].reshape(-1,3)])
    cor = np.median(b, 0)
    uniforme = float(np.mean(np.linalg.norm(b - cor, axis=1)))
    if uniforme < 26:                       # borda toda da mesma cor: e fundo
        d = np.linalg.norm(bgr - cor, axis=2)
        a = np.clip((d - 22) / 40.0, 0, 1)
        a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((5,5), np.float32))
        a = cv2.GaussianBlur(a, (0,0), 1.0)
        if a.mean() > 0.02: return bgr, a
    g = cv2.cvtColor(np.clip(bgr,0,255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    a = np.clip((g - 12) / 55.0, 0, 1.0) ** 0.6
    return bgr, cv2.GaussianBlur(a, (3,3), 0)

# ---------------------------------------------------- logo feita com o nome
def logo_texto(nome):
    """Emblema no mesmo espirito da logo da peca: anel duplo, nome no centro,
       estrelas e a palavra BARBEARIA embaixo. Fundo preto."""
    from PIL import Image, ImageDraw, ImageFont
    nome = (nome or 'BARBEARIA').strip().upper()
    for lixo in ('BARBEARIA', 'BARBER SHOP', 'BARBERSHOP', 'BARBER'):
        if nome != lixo and nome.endswith(' ' + lixo):
            nome = nome[: -len(lixo) - 1].strip()
    palavras = nome.split()
    if len(palavras) > 2:
        meio = (len(palavras) + 1) // 2
        linhas = [' '.join(palavras[:meio]), ' '.join(palavras[meio:])]
    elif len(palavras) == 2:
        linhas = palavras
    else:
        linhas = [nome]

    S = 1024
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    BRANCO = (238, 236, 232, 255)
    OURO   = (201, 162, 92, 255)
    cx = cy = S // 2

    # anel duplo
    r1 = int(S * 0.455)
    d.ellipse([cx-r1, cy-r1, cx+r1, cy+r1], outline=BRANCO, width=7)
    r2 = int(S * 0.415)
    d.ellipse([cx-r2, cy-r2, cx+r2, cy+r2], outline=OURO, width=2)

    # marcas nas laterais, lembrando os ramos do emblema original
    for lado in (-1, 1):
        for k in range(5):
            ang = math.radians(60 + k * 15)
            rr = r2 - 18
            x = cx + lado * int(math.sin(ang) * rr)
            y = cy - int(math.cos(ang) * rr) + 120
            d.ellipse([x-7, y-3, x+7, y+3], fill=OURO)

    # nome no centro
    largura_max = int(r2 * 1.42)
    tam = 170
    while tam > 26:
        f = ImageFont.truetype(FONTE, tam)
        if max(d.textlength(l, font=f) for l in linhas) <= largura_max: break
        tam -= 3
    f = ImageFont.truetype(FONTE, tam)
    alt = int(tam * 1.08)
    total = alt * len(linhas)
    y = cy - total // 2 - int(S * 0.035)
    for l in linhas:
        d.text((cx, y), l, font=f, fill=BRANCO, anchor='ma')
        y += alt

    # filete + palavra BARBEARIA
    yl = y + 14
    d.line([(cx - largura_max*0.30, yl), (cx + largura_max*0.30, yl)], fill=OURO, width=3)
    fp = ImageFont.truetype(FONTE, max(20, int(tam * 0.26)))
    d.text((cx, yl + 16), 'B A R B E A R I A', font=fp, fill=OURO, anchor='ma')

    # tres estrelas, como no emblema de referencia
    def estrela(px, py, raio):
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            rr = raio if i % 2 == 0 else raio * 0.42
            pts.append((px + math.cos(ang) * rr, py + math.sin(ang) * rr))
        d.polygon(pts, fill=BRANCO)
    ye = yl + 16 + int(tam * 0.26) + 42
    for dx in (-46, 0, 46):
        estrela(cx + dx, ye, 15 if dx == 0 else 12)

    a = np.array(img)
    return np.dstack([a[:, :, 2], a[:, :, 1], a[:, :, 0], a[:, :, 3]]).astype(np.uint8)

# ------------------------------------------------------------------- fluxo
origem = 'logo do cliente'
bruto = None
try: bruto = baixar(LOGO)
except Exception as e: print('nao baixei a logo:', str(e)[:80])

im = decodifica(bruto) if bruto else None
serve = False
if im is not None:
    veredito = ia_aprova(bruto, NOME)
    if veredito is None:
        serve = not (parece_foto(im[:, :, :3]) or tem_rosto(im[:, :, :3]))
    else:
        serve = veredito
    if not serve: print('logo recusada (foto/cena/rosto) — vou desenhar uma com o nome')

if serve:
    melhor = real_esrgan(LOGO)
    im = melhor if melhor is not None else im
    im = ampliar(im) if melhor is None else im
    if im.ndim == 3 and im.shape[2] == 3:
        bgr, a = recortar_fundo(im)
    else:
        bgr, a = recortar_fundo(im)
    rgba = np.dstack([np.clip(bgr,0,255), np.clip(a,0,1)*255.0]).astype(np.uint8)
else:
    rgba = logo_texto(NOME)
    origem = 'logo desenhada com o nome'

# recorta o vazio em volta
al = rgba[:, :, 3].astype(np.float32)/255.0
ys, xs = np.where(al > 0.12)
if len(xs) > 20:
    rgba = rgba[ys.min():ys.max()+1, xs.min():xs.max()+1]

h, w = rgba.shape[:2]
if max(h, w) > LADO:
    s = LADO / max(h, w)
    rgba = cv2.resize(rgba, (max(1,int(w*s)), max(1,int(h*s))), interpolation=cv2.INTER_AREA)

# o fundo criado e SEMPRE PRETO: onde nao ha arte, o pixel vira preto.
# isso casa com a tela do celular e elimina franja clara na borda da logo.
_a = rgba[:, :, 3].astype(np.float32) / 255.0
rgba[:, :, :3] = (rgba[:, :, :3].astype(np.float32) * _a[..., None]).astype(np.uint8)
cv2.imwrite(os.path.join(OUT, 'logo_tela.png'), rgba)
cv2.imwrite(os.path.join(OUT, 'logo_preview.jpg'),
            rgba[:, :, :3], [cv2.IMWRITE_JPEG_QUALITY, 92])

# marca d'agua de baixo
LM = 300
hh, ww = rgba.shape[:2]
sm = LM / max(hh, ww)
peq = cv2.resize(rgba, (max(1,int(ww*sm)), max(1,int(hh*sm))), interpolation=cv2.INTER_AREA)
tela = np.zeros((LM, LM, 4), np.uint8)
oy, ox = (LM - peq.shape[0])//2, (LM - peq.shape[1])//2
tela[oy:oy+peq.shape[0], ox:ox+peq.shape[1]] = peq
ap = tela[:, :, 3].astype(np.float32)/255.0
cinza = cv2.cvtColor(tela[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
am = np.clip((cinza - 16)/148, 0, 1.0) ** 0.60
am = cv2.GaussianBlur(am, (3,3), 0) * 0.90 * ap
marca = np.dstack([np.clip(tela[:, :, :3].astype(np.float32)*1.35 + 4, 0, 255), am*255.0])
cv2.imwrite(os.path.join(OUT, 'marca.png'), marca.astype(np.uint8))

print('LOGO PRONTA:', rgba.shape[1], 'x', rgba.shape[0], '| origem:', origem)
