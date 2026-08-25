/**
 * record.js
 * ────────────────────────────────────────────────────────────────
 * Abre o painel de uma barbearia específica num navegador headless,
 * executa o roteiro de navegação (steps/roteiro.js) no timing certo,
 * e grava tudo em vídeo (.webm) usando a gravação nativa do Playwright.
 *
 * USO DIRETO (teste manual):
 *   node scripts/record.js "https://seuapp.com/painel/barbearia-x" "barbearia-x" "senha123"
 *
 * USO VIA SERVIDOR:
 *   é chamado por server.js, que recebe a requisição do n8n.
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const roteiro = require('../steps/roteiro');

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/**
 * Grava o walkthrough de um painel.
 * @param {string} url    URL final do painel já publicado (com slug)
 * @param {string} slug   identificador da barbearia (usado no nome do arquivo)
 * @param {string} [senha] senha do painel, se o login estiver ativo
 * @param {string} outDir pasta onde salvar o .webm bruto
 * @returns {Promise<string>} caminho do arquivo .webm gerado
 */
async function gravarWalkthrough(url, slug, senha, outDir) {
  const videoDir = path.join(outDir, `raw_${slug}_${Date.now()}`);
  fs.mkdirSync(videoDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  const t0 = Date.now();
  const elapsed = () => (Date.now() - t0) / 1000;

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

    // Se o painel pedir senha (tela de login), preenche automaticamente
    if (senha) {
      const inputSenha = await page.$('#aloco-senha-inp');
      if (inputSenha) {
        await inputSenha.fill(senha);
        await page.click('#aloco-entrar');
        await page.waitForTimeout(1200);
      }
    }

    // Executa o roteiro respeitando o timing (t em segundos)
    for (const passo of roteiro) {
      const alvo = passo.t;
      const faltam = alvo - elapsed();
      if (faltam > 0) await sleep(faltam * 1000);

      const a = passo.action;
      try {
        if (a.type === 'click') {
          await page.click(a.selector, { timeout: 4000 }).catch(() => {});
        } else if (a.type === 'wait') {
          await sleep(a.ms);
        } else if (a.type === 'scroll') {
          await page.$eval(a.selector, (el, y) => { el.scrollTop = y; }, a.y).catch(() => {});
        } else if (a.type === 'hover') {
          await page.hover(a.selector, { timeout: 4000 }).catch(() => {});
        }
      } catch (e) {
        console.warn(`[record.js] passo t=${alvo}s falhou (seguindo mesmo assim):`, e.message);
      }
    }

    // Garante que o vídeo tenha pelo menos a duração total configurada
    const restante = roteiro.DURACAO_TOTAL_SEGUNDOS - elapsed();
    if (restante > 0) await sleep(restante * 1000);

  } finally {
    await context.close(); // finaliza a gravação do vídeo
    await browser.close();
  }

  // O Playwright salva o vídeo com um nome gerado por ele dentro de videoDir
  const arquivos = fs.readdirSync(videoDir).filter(f => f.endsWith('.webm'));
  if (!arquivos.length) throw new Error('Playwright não gerou o arquivo de vídeo.');
  return path.join(videoDir, arquivos[0]);
}

module.exports = { gravarWalkthrough };

// Permite rodar direto via linha de comando pra teste manual
if (require.main === module) {
  const [,, url, slug, senha] = process.argv;
  if (!url || !slug) {
    console.error('Uso: node record.js <url> <slug> [senha]');
    process.exit(1);
  }
  gravarWalkthrough(url, slug, senha, path.join(__dirname, '..', 'tmp'))
    .then(caminho => console.log('Vídeo bruto gerado em:', caminho))
    .catch(err => { console.error('Erro:', err); process.exit(1); });
}
