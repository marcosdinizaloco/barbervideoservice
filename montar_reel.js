/* ============================================================================
   montar_reel.js  — corta a gravação do app (app.webm) nos pedaços que o
   template cinematográfico espera e monta o "reel.mp4" (384x848, 30fps, ~101s, template cinematografico v2).
   Usa os tempos de cada tela (marks.json) que o gravar_app.js salvou.

   Uso:
     node montar_reel.js work/<slug>
   Saída:
     work/<slug>/reel.mp4
   ============================================================================ */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const DIR = process.argv[2];
if (!DIR) { console.error('uso: node montar_reel.js work/<slug>'); process.exit(1); }
const APP  = path.join(DIR, 'app.webm');
const MK   = path.join(DIR, 'marks.json');
const OUT  = path.join(DIR, 'reel.mp4');
if (!fs.existsSync(APP)) { console.error('nao achei', APP); process.exit(1); }
const marks = JSON.parse(fs.readFileSync(MK, 'utf8'));

// plano do reel (casa com as legendas do template). [nome, chave_do_mark, duracao_s]
const PLANO = [
  ['splash',   '00_splash',           4],
  ['home',     '01_inicio',          16],
  ['reservar', '02_inicio_reservar', 12],
  ['home2',    '01_inicio',           9],
  ['agendar',  '03_agendar',         15],
  ['servico',  '04_servico',         12],
  ['fila',     '05_fila',            12],
  ['perfil',   '07_perfil',           8],
  ['homefim',  '08_inicio_fim',      13],
];
// EXTRACT agora e adaptativo por segmento (ate 3.8s crus por tela)

const W = 384, H = 848, FPS = 30;
const tmp = path.join(DIR, '_seg');
fs.mkdirSync(tmp, { recursive: true });

let list = [];
PLANO.forEach((p, i) => {
  const [nome, chave, dur] = p;
  let ms = marks[chave];
  if (ms == null) { console.log(`(aviso) sem mark "${chave}", usando 0`); ms = 0; }
  const start = Math.max(0, ms / 1000 + 0.25);
  const seg = path.join(tmp, `s${String(i).padStart(2,'0')}_${nome}.mp4`);
  // pega ate 3.8s crus da tela e ESTICA para "dur" s (setpts) -> cinematografico
  const EXTRACT = Math.min(3.8, Math.max(2.0, dur / 4));
  const factor = (dur / EXTRACT).toFixed(4);
  // drawbox no topo = tampa a barra de status do iPhone (ponto vermelho, relogio, etc)
  const vf = `scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},drawbox=x=0:y=0:w=${W}:h=56:color=black:t=fill,setpts=${factor}*PTS,fps=${FPS}`;
  const cmd = `ffmpeg -y -loglevel error -ss ${start.toFixed(2)} -t ${EXTRACT} -i "${APP}" -an -vf "${vf}" -t ${dur} -c:v libx264 -pix_fmt yuv420p "${seg}"`;
  execSync(cmd);
  list.push(seg);
  console.log(`ok seg ${i} "${nome}"  <- ${chave} @ ${start.toFixed(1)}s  (${dur}s)`);
});

// concatena
const listFile = path.join(tmp, 'list.txt');
fs.writeFileSync(listFile, list.map(f => `file '${path.resolve(f)}'`).join('\n'));
execSync(`ffmpeg -y -loglevel error -f concat -safe 0 -i "${listFile}" -c:v libx264 -pix_fmt yuv420p -r ${FPS} "${OUT}"`);
const dur = execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 "${OUT}"`).toString().trim();
console.log('REEL pronto:', OUT, '| duracao:', dur, 's');
