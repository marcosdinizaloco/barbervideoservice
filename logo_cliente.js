/* logo_cliente.js <url_do_app> <pasta_saida>
   Abre o app do cliente e guarda:
     - logo_url.txt : o ENDERECO ORIGINAL da logo usada na splash (fonte oficial)
     - nome.txt     : o nome do estabelecimento
     - splash.png   : print da abertura, so para conferencia/reserva
   A logo NAO e recortada do print: quem trata a imagem e o logo_master.py,
   sempre a partir do arquivo original, em resolucao cheia. */
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const URL_APP = process.argv[2], OUT = process.argv[3] || '.';
if (!URL_APP) { console.error('uso: node logo_cliente.js <url> <pasta>'); process.exit(1); }
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ headless: true,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--hide-scrollbars'] });
  const ctx = await b.newContext({ viewport:{width:390,height:844}, deviceScaleFactor:4, isMobile:true });
  const p = await ctx.newPage();
  try { await p.goto(URL_APP, { waitUntil:'domcontentloaded', timeout:30000 }); } catch(e){}
  await p.waitForTimeout(2500);
  await p.screenshot({ path: path.join(OUT, 'splash.png') });

  let nome = '', logo = '';
  try {
    const r = await p.evaluate(() => {
      const t = (document.title || '').trim();
      const m = (document.querySelector('meta[name="apple-mobile-web-app-title"]')||{}).content || '';
      const nome = (t || m || '').replace(/\s*[|\-–]\s*(ALOCO|Aloco|aloco).*$/,'').trim();
      // endereco da logo, na ordem em que o template a usa
      const alvos = ['.splash-logo', '#splash img', '.logo-circle img', '.cad-logo-circle img', '.sb img'];
      let src = '';
      for (const s of alvos) {
        const el = document.querySelector(s);
        if (el && el.currentSrc) { src = el.currentSrc; break; }
        if (el && el.src)        { src = el.src;        break; }
      }
      if (!src) {
        const og = document.querySelector('meta[property="og:image"]');
        if (og && og.content) src = og.content;
      }
      return { nome, src };
    });
    nome = r.nome || ''; logo = r.src || '';
  } catch(e){}

  fs.writeFileSync(path.join(OUT, 'nome.txt'), nome || '');
  fs.writeFileSync(path.join(OUT, 'logo_url.txt'), logo || '');
  await b.close();
  console.log('APP OK | NOME:', nome, '| LOGO:', logo ? logo.slice(0, 90) : '(nao achei no HTML)');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
