/**
 * mesclar.js
 * ────────────────────────────────────────────────────────────────
 * Junta o vídeo gravado (tela, sem áudio) com a narração fixa
 * (mesma pra todas as barbearias) e gera o .mp4 final.
 *
 * Requer o ffmpeg instalado no servidor:
 *   sudo apt-get install -y ffmpeg
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const AUDIO_FIXO = path.join(__dirname, '..', 'assets', 'narracao-fixa.mp3');

/**
 * @param {string} videoBrutoPath  caminho do .webm gerado pelo record.js
 * @param {string} slug            identificador da barbearia
 * @param {string} outDir          pasta de saída dos .mp4 finais
 * @returns {Promise<string>} caminho do .mp4 final
 */
function mesclarComAudio(videoBrutoPath, slug, outDir) {
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(AUDIO_FIXO)) {
      return reject(new Error(
        `Áudio fixo não encontrado em ${AUDIO_FIXO}. ` +
        `Coloque o arquivo de narração em assets/narracao-fixa.mp3`
      ));
    }
    fs.mkdirSync(outDir, { recursive: true });
    const saida = path.join(outDir, `${slug}_${Date.now()}.mp4`);

    // -shortest corta o resultado no menor dos dois (vídeo ou áudio) —
    // por isso é importante que DURACAO_TOTAL_SEGUNDOS no roteiro.js
    // bata com a duração real do áudio.
    const args = [
      '-y',
      '-i', videoBrutoPath,
      '-i', AUDIO_FIXO,
      '-c:v', 'libx264',
      '-preset', 'veryfast',
      '-crf', '23',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-shortest',
      saida,
    ];

    const ff = spawn('ffmpeg', args);
    let stderr = '';
    ff.stderr.on('data', d => { stderr += d.toString(); });
    ff.on('close', code => {
      if (code === 0) resolve(saida);
      else reject(new Error(`ffmpeg saiu com código ${code}:\n${stderr.slice(-800)}`));
    });
  });
}

module.exports = { mesclarComAudio };

if (require.main === module) {
  const [,, videoBruto, slug] = process.argv;
  if (!videoBruto || !slug) {
    console.error('Uso: node mesclar.js <video_bruto.webm> <slug>');
    process.exit(1);
  }
  mesclarComAudio(videoBruto, slug, path.join(__dirname, '..', 'output'))
    .then(p => console.log('Vídeo final:', p))
    .catch(err => { console.error('Erro:', err); process.exit(1); });
}
