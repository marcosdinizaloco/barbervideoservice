# logo_prospec.py <url_ou_arquivo> <pasta_saida>
# Aumenta a resolucao da logo da barbearia, SEM mexer no fundo.
# Se houver token do Replicate, usa Real-ESRGAN; senao, amplia localmente.
import sys, os, json, time, urllib.request, urllib.error, numpy as np, cv2

# ==================== EDITE SO ISTO ====================
TOKEN_REPLICATE = os.environ.get('REPLICATE_TOKEN', 'COLE_AQUI_O_TOKEN')
ESCALA          = 4        # 2 ou 4
# =======================================================

ORIG, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
LADO = 1024

def http(url, dados=None, cab=None, timeout=120):
    req = urllib.request.Request(url, data=dados, headers=cab or {})
    return urllib.request.urlopen(req, timeout=timeout).read()

def baixar_bytes(src):
    return http(src, cab={'User-Agent': 'Mozilla/5.0'}, timeout=45)

def decodifica(dados):
    im = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None: raise SystemExit('imagem invalida')
    if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im

# ---------- Real-ESRGAN no Replicate --------------------------------------
def real_esrgan(url_imagem):
    if not TOKEN_REPLICATE or TOKEN_REPLICATE.startswith('COLE'): return None
    if not str(url_imagem).startswith('http'): return None
    cab = {'Authorization': 'Bearer ' + TOKEN_REPLICATE,
           'Content-Type': 'application/json',
           'Prefer': 'wait'}
    corpo = json.dumps({'input': {'image': url_imagem, 'scale': ESCALA, 'face_enhance': False}}).encode()
    try:
        r = json.loads(http('https://api.replicate.com/v1/models/nightmareai/real-esrgan/predictions',
                            corpo, cab, timeout=180))
    except urllib.error.HTTPError as e:
        print('Replicate recusou:', e.code, e.read()[:200].decode('utf-8', 'ignore'))
        return None
    except Exception as e:
        print('Replicate falhou:', e); return None

    # se ainda estiver processando, espera terminar
    for _ in range(40):
        if r.get('status') == 'succeeded': break
        if r.get('status') in ('failed', 'canceled'):
            print('Replicate:', r.get('error')); return None
        time.sleep(3)
        try:
            r = json.loads(http(r['urls']['get'], cab={'Authorization': 'Bearer ' + TOKEN_REPLICATE}, timeout=60))
        except Exception as e:
            print('Replicate: erro ao consultar', e); return None

    saida = r.get('output')
    if isinstance(saida, list): saida = saida[0] if saida else None
    if not saida: return None
    try:
        print('Real-ESRGAN ok')
        return decodifica(baixar_bytes(saida))
    except Exception as e:
        print('nao consegui baixar o resultado:', e); return None

# ---------- ampliacao local (reserva) -------------------------------------
def ampliar_local(im):
    tem_alpha = (im.shape[2] == 4)
    bgr   = im[:, :, :3].astype(np.float32)
    alpha = im[:, :, 3].astype(np.float32) if tem_alpha else None
    h, w = bgr.shape[:2]
    s = LADO / max(h, w)
    nw, nh = max(1, int(round(w*s))), max(1, int(round(h*s)))
    def esc(img):
        if s > 1:
            meio = cv2.resize(img, (max(1,int(w*(1+s)/2)), max(1,int(h*(1+s)/2))), interpolation=cv2.INTER_CUBIC)
            return cv2.resize(meio, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    bgr = esc(bgr)
    if alpha is not None: alpha = esc(alpha)
    suave   = cv2.bilateralFilter(np.clip(bgr,0,255).astype(np.uint8), 5, 40, 40).astype(np.float32)
    borrado = cv2.GaussianBlur(suave, (0,0), 1.1)
    bgr = np.clip(suave + (suave - borrado) * 0.85, 0, 255)
    return np.dstack([bgr, np.clip(alpha,0,255)]).astype(np.uint8) if alpha is not None else bgr.astype(np.uint8)

# ---------- fluxo ---------------------------------------------------------
im = real_esrgan(ORIG)
origem = 'real-esrgan'
if im is None:
    print('usando ampliacao local')
    origem = 'local'
    im = decodifica(baixar_bytes(ORIG) if str(ORIG).startswith('http') else open(ORIG,'rb').read())
    im = ampliar_local(im)
if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)

# limita o tamanho final, mantendo proporcao
h, w = im.shape[:2]
if max(h, w) > LADO:
    s = LADO / max(h, w)
    im = cv2.resize(im, (max(1,int(w*s)), max(1,int(h*s))), interpolation=cv2.INTER_AREA)

cv2.imwrite(os.path.join(OUT, 'logo_tela.png'), im)

# marca d'agua de baixo: 300px, transparencia pelo brilho
LADO_M = 300
bgr = im[:, :, :3]
hh, ww = bgr.shape[:2]
sm = LADO_M / max(hh, ww)
peq = cv2.resize(bgr, (max(1,int(ww*sm)), max(1,int(hh*sm))), interpolation=cv2.INTER_AREA)
tela = np.zeros((LADO_M, LADO_M, 3), np.uint8)
oy, ox = (LADO_M - peq.shape[0])//2, (LADO_M - peq.shape[1])//2
tela[oy:oy+peq.shape[0], ox:ox+peq.shape[1]] = peq
cinza = cv2.cvtColor(tela, cv2.COLOR_BGR2GRAY).astype(np.float32)
am = np.clip((cinza - 16)/148, 0, 1.0) ** 0.60
am = cv2.GaussianBlur(am, (3,3), 0) * 0.90
marca = np.dstack([np.clip(tela.astype(np.float32)*1.35 + 4, 0, 255), am*255.0])
cv2.imwrite(os.path.join(OUT, 'marca.png'), marca.astype(np.uint8))

print('LOGO PRONTA:', im.shape[1], 'x', im.shape[0], '| fonte:', origem)
