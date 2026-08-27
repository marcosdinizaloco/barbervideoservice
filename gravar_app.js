/* ============================================================================
   BARBER VIDEO SERVICE — Robô de gravação do app (roda na VPS)
   ----------------------------------------------------------------------------
   O que faz:
     - abre a URL do app da barbearia
     - entra como "cliente de teste" (semeia dados no localStorage p/ pular login)
     - passa por: Splash/Logo -> Início -> Agendar -> (serviço) -> Fila -> Perfil -> Início
     - grava tudo em vídeo (app.webm) E tira um print de cada tela (screens/*.png)
     - salva marks.json com o tempo (em ms) em que cada tela apareceu

   Uso:
     node gravar_app.js "https://app.aloco.com.br/clientes/barbearia-da-erika/index.html" barbearia-da-erika

   Saída (dentro de ./work/<slug>/):
     app.webm            -> a gravação
     marks.json          -> tempos de cada tela
     screens/00_splash.png ... 06_inicio2.png -> um print por tela
     log é impresso no terminal (me mande ele + os prints)
   ============================================================================ */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const APP_URL = process.argv[2];
const SLUG    = process.argv[3] || 'barbearia';
if (!APP_URL) { console.error('ERRO: passe a URL do app como 1º argumento.'); process.exit(1); }

const OUT = path.resolve('work', SLUG);
const SHOTS = path.join(OUT, 'screens');
fs.mkdirSync(SHOTS, { recursive: true });

const VW = 390, VH = 844;                 // tamanho de um celular (retrato)
const marks = {};
let t0 = 0;
const now = () => Date.now() - t0;

// cliente de teste semeado no localStorage (pra cair direto na Home "OLÁ, ...").
// >>> Se o app usar outra chave, é SÓ AQUI que a gente ajusta depois do 1º teste. <<<
const CLIENTE = {
  nome: 'Marcos', sobrenome: 'Diniz', nomeCompleto: 'Marcos Diniz',
  telefone: '(79) 99999-0000', whatsapp: '(79) 99999-0000',
  dataNascimento: '1993-10-26', logado: true, id: 'demo-teste'
};
const SEED_KEYS = ['aloco_cliente','cliente','alocoCliente','aloco_user','usuario','user','aloco:cliente'];

async function log(msg){ console.log(`[${(now()/1000).toFixed(1)}s] ${msg}`); }

// clique robusto por texto (tenta várias grafias e vários tipos de elemento)
async function tap(page, labels, nome){
  for (const lb of labels){
    // 1) locator por texto exato/parcial, elemento clicável
    const cands = [
      page.getByRole('button', { name: lb, exact: false }),
      page.getByText(lb, { exact: false }),
      page.locator(`[onclick]:has-text("${lb}")`),
      page.locator(`a:has-text("${lb}"), button:has-text("${lb}"), li:has-text("${lb}"), div:has-text("${lb}")`)
    ];
    for (const c of cands){
      try{
        const n = await c.count();
        if (n>0){
          // pega o menor elemento que contém o texto (evita clicar no container gigante)
          const el = c.first();
          await el.scrollIntoViewIfNeeded({ timeout: 1500 }).catch(()=>{});
          await el.click({ timeout: 2500 });
          await log(`OK clicou "${lb}" (alvo: ${nome})`);
          return true;
        }
      }catch(e){}
    }
  }
  await log(`!! NÃO achei o botão de "${nome}" (tentei: ${labels.join(', ')})`);
  return false;
}

async function screen(page, nome, dwellMs){
  marks[nome] = now();
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS, `${nome}.png`) }).catch(()=>{});
  await log(`--- tela "${nome}" capturada`);
  if (dwellMs) await page.waitForTimeout(dwellMs);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
           '--hide-scrollbars','--autoplay-policy=no-user-gesture-required']
  });
  const ctx = await browser.newContext({
    viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    recordVideo: { dir: OUT, size: { width: VW, height: VH } }
  });
  // semeia o cliente ANTES de qualquer script da página rodar
  await ctx.addInitScript((seed) => {
    try { for (const k of seed.keys) localStorage.setItem(k, JSON.stringify(seed.cliente)); } catch(e){}
    try { localStorage.setItem('aloco_logado','1'); localStorage.setItem('logado','1'); } catch(e){}
  }, { keys: SEED_KEYS, cliente: CLIENTE });

  const page = await ctx.newPage();
  t0 = Date.now();
  await log(`abrindo: ${APP_URL}`);

  // 0) SPLASH / LOGO — captura o que aparece de primeira (logo da barbearia)
  try { await page.goto(APP_URL, { waitUntil: 'domcontentloaded', timeout: 30000 }); }
  catch(e){ await log(`ERRO ao abrir a página: ${e.message}`); }
  await page.waitForTimeout(1200);
  await screen(page, '00_splash', 1800);

  // garante que o app terminou de carregar
  await page.waitForLoadState('networkidle',{ timeout: 15000 }).catch(()=>{});

  // 1) INÍCIO (Home) — saudação + "Reservar meu horário" + fila
  await tap(page, ['Início','INÍCIO','Inicio','Home'], 'nav Início');
  await page.waitForTimeout(800);
  await screen(page, '01_inicio', 3600);
  // rola um pouco pra mostrar o botão de reservar / seção de fila
  await page.mouse.wheel(0, 260); await page.waitForTimeout(1200);
  await screen(page, '02_inicio_reservar', 2600);
  await page.mouse.wheel(0, -260); await page.waitForTimeout(400);

  // 2) AGENDAR — "SEU PRÓXIMO VISUAL", escolher serviço
  await tap(page, ['Agendar','AGENDAR','Agenda','Reservar meu horário','Reservar'], 'nav Agendar');
  await page.waitForTimeout(1000);
  await screen(page, '03_agendar', 3200);
  // tenta selecionar um serviço (Corte) só pra dar dinâmica
  await tap(page, ['Corte','Corte + Barba','Barba'], 'serviço');
  await page.waitForTimeout(900);
  await screen(page, '04_servico', 3000);

  // 3) FILA — "ENTRE NA FILA"
  await tap(page, ['Fila','FILA','Entrar na fila','Entre na fila'], 'nav Fila');
  await page.waitForTimeout(1000);
  await screen(page, '05_fila', 3200);

  // 4) PERFIL — dados do cliente
  await tap(page, ['Perfil','PERFIL','Conta','Meu perfil'], 'nav Perfil');
  await page.waitForTimeout(1000);
  await screen(page, '06_perfil', 2600);

  // 5) volta pro INÍCIO (fecho)
  await tap(page, ['Início','INÍCIO','Inicio','Home'], 'nav Início (volta)');
  await page.waitForTimeout(900);
  await screen(page, '07_inicio_fim', 2600);

  await log('gravação concluída, salvando...');
  const video = page.video();
  await page.close(); await ctx.close(); await browser.close();

  const vpath = await video.path().catch(()=>null);
  if (vpath){
    const dest = path.join(OUT, 'app.webm');
    try { fs.renameSync(vpath, dest); } catch(e){ fs.copyFileSync(vpath, dest); }
    console.log('VIDEO:', dest);
  }
  fs.writeFileSync(path.join(OUT,'marks.json'), JSON.stringify(marks, null, 2));
  console.log('MARKS:', JSON.stringify(marks));
  console.log('SCREENS em:', SHOTS);
  console.log('\n==> Me mande a pasta screens/ (os prints) + este log. Aí eu confirmo e encadeio o resto.');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
