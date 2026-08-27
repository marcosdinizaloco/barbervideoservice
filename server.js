// ALOCO - Gerador de Video (mini app web + API pra n8n). Roda na VPS, porta 3300.
// - Interface manual:  http://143.95.163.162:3300  (cola o link e clica Gerar)
// - API pra n8n:       POST /api/gerar  {url}   -> gera e devolve {videoUrl} quando fica pronto
//                      GET  /api/status/:slug   -> {done, videoUrl}
const express = require('express');
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
const BASE = __dirname;
const PORT = 3300;
const HOST_PUBLICO = 'http://143.95.163.162:' + PORT; // usado nas URLs devolvidas pra n8n/Z-API

// Token simples pra proteger a API (a n8n manda no header "x-token").
// Troque por um segredo seu se quiser. Deixe igual aqui e na n8n.
const API_TOKEN = 'aloco-troque-isto';

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
fs.mkdirSync(path.join(BASE, 'saidas'), { recursive: true });
app.use('/saidas', express.static(path.join(BASE, 'saidas')));

function slugFromUrl(u) {
  const m = String(u || '').match(/clientes\/([^\/?#]+)/i);
  const s = m ? m[1] : 'video';
  return s.toLowerCase().replace(/[^a-z0-9-]/g, '');
}
const URL_OK = /^https:\/\/[a-z0-9.-]+\/clientes\/[a-z0-9._-]+\//i;

// guarda o estado de cada geracao (pra API de status conseguir reportar erro)
const jobs = {}; // slug -> {status:'gerando'|'pronto'|'erro', erro}

function rodarGeracao(url, slug, cb) {
  try { fs.unlinkSync(path.join(BASE, 'saidas', slug + '.mp4')); } catch (e) {}
  jobs[slug] = { status: 'gerando', quando: Date.now() };
  execFile('bash', ['gerar_video.sh', url, slug],
    { cwd: BASE, timeout: 8 * 60 * 1000, maxBuffer: 10 * 1024 * 1024 },
    (err, stdout, stderr) => {
      const done = fs.existsSync(path.join(BASE, 'saidas', slug + '.mp4'));
      if (err || !done) {
        jobs[slug] = { status: 'erro', erro: String((stderr || err || '')).slice(-600) };
      } else {
        jobs[slug] = { status: 'pronto' };
      }
      if (cb) cb(jobs[slug]);
    });
}

// ---------- INTERFACE MANUAL (mini app) ----------
const PAGE = (body, refresh) => `<!doctype html><html lang=pt-BR><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">${refresh ? '<meta http-equiv="refresh" content="6">' : ''}
<title>ALOCO - Gerar Video</title><style>
*{box-sizing:border-box}body{font-family:system-ui,Arial;background:#0b0f17;color:#fff;margin:0;padding:24px;display:flex;flex-direction:column;align-items:center}
.card{max-width:520px;width:100%;background:#141a26;border:1px solid #263042;border-radius:16px;padding:26px;margin-top:20px;text-align:center}
h1{font-size:22px;margin:0 0 6px}p{color:#9fb0c8;font-size:14px;line-height:1.5}
input{width:100%;padding:14px;border-radius:10px;border:1px solid #2b3648;background:#0e1420;color:#fff;font-size:15px;margin:14px 0}
button,a.btn{display:inline-block;width:100%;padding:15px;border:0;border-radius:10px;background:linear-gradient(135deg,#5aa2ff,#8b6cff);color:#fff;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none}
video{max-width:100%;border-radius:14px;margin-top:14px}.small{color:#7c8aa3;font-size:13px;margin-top:18px}a{color:#9fb0c8}
</style></head><body><div class="card">${body}</div></body></html>`;

app.get('/', (req, res) => {
  res.send(PAGE(`<h1>🎬 Gerar vídeo da barbearia</h1>
    <p>Cola o link do app da barbearia e clica em Gerar. Em ~2-3 min o vídeo fica pronto.</p>
    <form method="POST" action="/gerar">
      <input name="url" placeholder="https://app.aloco.com.br/clientes/.../index.html" required>
      <button type="submit">Gerar vídeo</button>
    </form>`));
});

app.post('/gerar', (req, res) => {
  const url = String(req.body.url || '').trim();
  if (!URL_OK.test(url)) {
    return res.send(PAGE(`<h1>⚠️ Link inválido</h1>
      <p>Cola um link tipo <br><b>https://app.aloco.com.br/clientes/nome/index.html</b></p>
      <a class="btn" href="/">Voltar</a>`));
  }
  const slug = slugFromUrl(url);
  rodarGeracao(url, slug); // roda em segundo plano
  res.redirect('/video/' + slug);
});

app.get('/video/:slug', (req, res) => {
  const slug = String(req.params.slug).replace(/[^a-z0-9-]/gi, '');
  const done = fs.existsSync(path.join(BASE, 'saidas', slug + '.mp4'));
  const body = done
    ? `<h1>✅ Vídeo pronto!</h1>
       <video src="/saidas/${slug}.mp4?v=${Date.now()}" controls playsinline></video>
       <a class="btn" href="/saidas/${slug}.mp4?v=${Date.now()}" download style="margin-top:14px">⬇️ Baixar vídeo</a>
       <div class="small"><a href="/">← Gerar outro</a></div>`
    : `<h1>⏳ Gerando o vídeo...</h1>
       <p>Leva uns 2-3 minutos. Pode deixar essa página aberta — ela atualiza sozinha.</p>
       <div class="small">Barbearia: <b>${slug}</b> · <a href="/">Cancelar</a></div>`;
  res.send(PAGE(body, !done));
});

// ---------- API PRA n8n ----------
function checarToken(req, res) {
  if (!API_TOKEN) return true; // sem token configurado = liberado
  if (req.get('x-token') === API_TOKEN) return true;
  res.status(401).json({ ok: false, erro: 'token invalido' });
  return false;
}

// POST /api/gerar {url}  -> SINCRONO: espera gerar e devolve {videoUrl}
// (a geracao leva ~2-3 min; deixe o timeout do HTTP node da n8n em 300000)
app.post('/api/gerar', (req, res) => {
  if (!checarToken(req, res)) return;
  const url = String((req.body && req.body.url) || '').trim();
  if (!URL_OK.test(url)) return res.status(400).json({ ok: false, erro: 'url invalida' });
  const slug = slugFromUrl(url);
  rodarGeracao(url, slug, (fim) => {
    if (fim.status === 'pronto') {
      res.json({ ok: true, slug, videoUrl: `${HOST_PUBLICO}/saidas/${slug}.mp4` });
    } else {
      res.status(500).json({ ok: false, slug, erro: fim.erro || 'falha na geracao' });
    }
  });
});

// POST /api/gerar-async {url} -> devolve na hora {slug, statusUrl}; use com polling se preferir
app.post('/api/gerar-async', (req, res) => {
  if (!checarToken(req, res)) return;
  const url = String((req.body && req.body.url) || '').trim();
  if (!URL_OK.test(url)) return res.status(400).json({ ok: false, erro: 'url invalida' });
  const slug = slugFromUrl(url);
  rodarGeracao(url, slug);
  res.json({ ok: true, slug, status: 'gerando',
    videoUrl: `${HOST_PUBLICO}/saidas/${slug}.mp4`,
    statusUrl: `${HOST_PUBLICO}/api/status/${slug}` });
});

// GET /api/status/:slug -> {done, status, videoUrl}
app.get('/api/status/:slug', (req, res) => {
  const slug = String(req.params.slug).replace(/[^a-z0-9-]/gi, '');
  const done = fs.existsSync(path.join(BASE, 'saidas', slug + '.mp4'));
  const job = jobs[slug] || {};
  let status = 'gerando';
  if (done) status = 'pronto';
  else if (job.status === 'erro') status = 'erro';
  res.json({ ok: true, slug, done, status, erro: job.erro || null,
    videoUrl: `${HOST_PUBLICO}/saidas/${slug}.mp4` });
});

app.get('/status', (req, res) => res.json({ ok: true }));

const server = app.listen(PORT, () => console.log('ALOCO video UI + API on port ' + PORT));
// nao derrubar requisicoes longas (a geracao sincrona segura a conexao ~3 min)
server.requestTimeout = 10 * 60 * 1000;
server.headersTimeout = 10 * 60 * 1000 + 5000;
server.timeout = 0;
