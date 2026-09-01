/* logo_cliente.js <url_do_app> <pasta_saida>
   Abre o app do cliente, guarda um print da tela de abertura (splash.png)
   e o nome da barbearia (nome.txt). E o unico passo que depende do app. */
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
  let nome = '';
  try {
    nome = await p.evaluate(() => {
      const t = (document.title || '').trim();
      const m = (document.querySelector('meta[name="apple-mobile-web-app-title"]')||{}).content || '';
      return (t || m || '').replace(/\s*[|\-–]\s*(ALOCO|Aloco|aloco).*$/,'').trim();
    });
  } catch(e){}
  fs.writeFileSync(path.join(OUT, 'nome.txt'), nome || '');
  await b.close();
  console.log('SPLASH OK:', path.join(OUT,'splash.png'), '| NOME:', nome);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
