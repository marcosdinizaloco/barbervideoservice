/* ============================================================================
   montar_reel.js  — corta a gravação do app (app.webm) nos pedaços que o
   template cinematográfico espera e monta o "reel.mp4" (384x848, 30fps, ~42s).
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
  ['splash',   '00_splash',           2],
  ['home',     '01_inicio',           7],
  ['reservar', '02_inicio_reservar',  5],
  ['home2',    '01_inicio',           4],
  ['agendar',  '03_agendar',          6],
  ['servico',  '04_servico',          5],
  ['fila',     '05_fila',             5],
  ['perfil',   '07_perfil',           3],
  ['homefim',  '08_inicio_fim',       5],
];
const EXTRACT = 2.2; // segundos "crus" pegos de cada tela (depois esticados p/ a duracao)

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
  // pega EXTRACT s da tela e ESTICA para "dur" s (setpts) -> vira cinematografico/estavel
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
