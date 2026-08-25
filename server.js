/**
 * server.js
 * ────────────────────────────────────────────────────────────────
 * Serviço HTTP simples. O n8n chama POST /gerar-video depois de
 * publicar o app da barbearia, e recebe de volta a URL do .mp4
 * pronto pra mandar no WhatsApp via Z-API.
 *
 * INSTALAR NO SERVIDOR:
 *   npm install
 *   npx playwright install --with-deps chromium
 *   sudo apt-get install -y ffmpeg
 *   node server.js        (ou via pm2, ver README.md)
 *
 * VARIÁVEIS DE AMBIENTE:
 *   PORT           porta do servidor (padrão 3300)
 *   PUBLIC_BASE_URL   URL pública onde os vídeos ficam acessíveis
 *                      (ex: https://videos.seudominio.com)
 *   TOKEN             token simples pra proteger o endpoint (opcional)
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
const { gravarWalkthrough } = require('./scripts/record');
const { mesclarComAudio } = require('./scripts/mesclar');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3300;
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL || `http://localhost:${PORT}`;
const TOKEN = process.env.TOKEN || null;

const TMP_DIR = path.join(__dirname, 'tmp');
const OUTPUT_DIR = path.join(__dirname, 'output');
fs.mkdirSync(TMP_DIR, { recursive: true });
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// serve os vídeos finais como arquivos estáticos
app.use('/videos', express.static(OUTPUT_DIR));

// fila simples pra não estourar CPU/memória gravando vários ao mesmo tempo
let processando = false;
const fila = [];

async function processarFila() {
  if (processando || fila.length === 0) return;
  processando = true;
  const job = fila.shift();
  try {
    const resultado = await executarJob(job.url, job.slug, job.senha);
    job.resolve(resultado);
  } catch (err) {
    job.reject(err);
  } finally {
    processando = false;
    processarFila();
  }
}

async function executarJob(url, slug, senha) {
  const videoBruto = await gravarWalkthrough(url, slug, senha, TMP_DIR);
  const videoFinal = await mesclarComAudio(videoBruto, slug, OUTPUT_DIR);
  // limpeza do bruto pra não acumular disco
  fs.rmSync(path.dirname(videoBruto), { recursive: true, force: true });
  const nomeArquivo = path.basename(videoFinal);
  return `${PUBLIC_BASE_URL}/videos/${nomeArquivo}`;
}

app.post('/gerar-video', (req, res) => {
  if (TOKEN && req.headers['x-token'] !== TOKEN) {
    return res.status(401).json({ ok: false, erro: 'token inválido' });
  }
  const { url, slug, senha } = req.body || {};
  if (!url || !slug) {
    return res.status(400).json({ ok: false, erro: 'informe url e slug' });
  }

  new Promise((resolve, reject) => {
    fila.push({ url, slug, senha, resolve, reject });
    processarFila();
  })
    .then(videoUrl => res.json({ ok: true, videoUrl }))
    .catch(err => res.status(500).json({ ok: false, erro: err.message }));
});

app.get('/status', (req, res) => {
  res.json({ ok: true, naFila: fila.length, processandoAgora: processando });
});

app.listen(PORT, () => {
  console.log(`[barber-video-service] rodando na porta ${PORT}`);
  console.log(`[barber-video-service] vídeos publicados em ${PUBLIC_BASE_URL}/videos/...`);
});
app.get/(request,response){response.send"barbervideoserviceonline"} 
