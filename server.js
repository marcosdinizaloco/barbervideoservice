const express = require('express');
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
const BASE = __dirname;
const PORT = 3300;
app.use(express.urlencoded({ extended: true }));
fs.mkdirSync(path.join(BASE, 'saidas'), { recursive: true });
app.use('/saidas', express.static(path.join(BASE, 'saidas')));

function slugFromUrl(u) {
  const m = String(u || '').match(/clientes\/([^\/?#]+)/i);
  const s = m ? m[1] : 'video';
  return s.toLowerCase().replace(/[^a-z0-9-]/g, '');
}
const URL_OK = /^https:\/\/[a-z0-9.-]+\/clientes\/[a-z0-9._-]+\//i;

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
  try { fs.unlinkSync(path.join(BASE, 'saidas', slug + '.mp4')); } catch (e) {}
  execFile('bash', ['gerar_video.sh', url, slug], { cwd: BASE }, () => {});
  res.redirect('/video/' + slug);
});

app.get('/video/:slug', (req, res) => {
  const slug = String(req.params.slug).replace(/[^a-z0-9-]/gi, '');
  const done = fs.existsSync(path.join(BASE, 'saidas', slug + '.mp4'));
  const body = done
    ? `<h1>✅ Vídeo pronto!</h1>
       <video src="/saidas/${slug}.mp4" controls playsinline></video>
       <a class="btn" href="/saidas/${slug}.mp4" download style="margin-top:14px">⬇️ Baixar vídeo</a>
       <div class="small"><a href="/">← Gerar outro</a></div>`
    : `<h1>⏳ Gerando o vídeo...</h1>
       <p>Leva uns 2-3 minutos. Pode deixar essa página aberta — ela atualiza sozinha.</p>
       <div class="small">Barbearia: <b>${slug}</b> · <a href="/">Cancelar</a></div>`;
  res.send(PAGE(body, !done));
});

app.get('/status', (req, res) => res.json({ ok: true }));
app.listen(PORT, () => console.log('ALOCO video UI on port ' + PORT));
