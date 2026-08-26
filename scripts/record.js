const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const roteiro = require('../steps/roteiro');

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function gravarWalkthrough(url, slug, senha, outDir) {
  const videoDir = path.join(outDir, `raw_${slug}_${Date.now()}`);
  fs.mkdirSync(videoDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },                 // tamanho de celular (o app e mobile)
    recordVideo: { dir: videoDir, size: { width: 390, height: 844 } },
  });
  // pula a tela de cadastro do app (deixa como se ja tivesse um cliente logado)
  await context.addInitScript(() => {
    try { localStorage.setItem('aloco_cliente', JSON.stringify({ nome: 'Cliente', sobrenome: '', telefone: '', desde: 'ago. 2026' })); } catch (e) {}
  });
  const page = await context.newPage();

  const t0 = Date.now();
  const elapsed = () => (Date.now() - t0) / 1000;

  try {
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });

    for (const passo of roteiro) {
      const faltam = passo.t - elapsed();
      if (faltam > 0) await sleep(faltam * 1000);
      const a = passo.action;
      try {
        if (a.type === 'click') {
          await page.click(a.selector, { timeout: 3000 }).catch(() => {});
        } else if (a.type === 'nav') {
          await page.evaluate(x => { try { navTo(x); } catch (e) {} }, a.screen);
        } else if (a.type === 'wait') {
          await sleep(a.ms);
        } else if (a.type === 'scroll') {
          await page.$eval(a.selector, (el, y) => { el.scrollTo({ top: y, behavior: 'smooth' }); }, a.y).catch(() => {});
        }
      } catch (e) {
        console.warn(`[record.js] passo t=${passo.t}s falhou (seguindo):`, e.message);
      }
    }

    const restante = roteiro.DURACAO_TOTAL_SEGUNDOS - elapsed();
    if (restante > 0) await sleep(restante * 1000);
  } finally {
    await context.close();
    await browser.close();
  }

  const arquivos = fs.readdirSync(videoDir).filter(f => f.endsWith('.webm'));
  if (!arquivos.length) throw new Error('Playwright nao gerou o arquivo de video.');
  return path.join(videoDir, arquivos[0]);
}

module.exports = { gravarWalkthrough };

if (require.main === module) {
  const [,, url, slug, senha] = process.argv;
  if (!url || !slug) { console.error('Uso: node record.js <url> <slug>'); process.exit(1); }
  gravarWalkthrough(url, slug, senha, path.join(__dirname, '..', 'tmp'))
    .then(c => console.log('Video bruto:', c))
    .catch(err => { console.error('Erro:', err); process.exit(1); });
}
