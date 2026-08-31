const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const APP_URL = process.argv[2];
const SLUG    = process.argv[3] || 'barbearia';
if (!APP_URL) { console.error('ERRO: passe a URL do app como 1o argumento.'); process.exit(1); }

const OUT = path.resolve('work', SLUG);
const SHOTS = path.join(OUT, 'screens');
fs.mkdirSync(SHOTS, { recursive: true });

const VW = 390, VH = 844;
const marks = {};
let t0 = 0;
const now = () => Date.now() - t0;

const CLIENTE = {
  nome: 'Marcos', sobrenome: 'Diniz', nomeCompleto: 'Marcos Diniz',
  telefone: '(79) 99999-0000', whatsapp: '(79) 99999-0000',
  dataNascimento: '1993-10-26', logado: true, id: 'demo-teste'
};
const SEED_KEYS = ['aloco_cliente','cliente','alocoCliente','aloco_user','usuario','user','aloco:cliente'];

async function log(msg){ console.log(`[${(now()/1000).toFixed(1)}s] ${msg}`); }

// clique rapido e robusto via JS (case-insensitive, pega o menor elemento clicavel)
async function tap(page, labels, nome){
  const res = await page.evaluate((labels)=>{
    const norm=s=>(s||'').replace(/\s+/g,' ').trim().toLowerCase();
    const want=labels.map(norm);
    const els=[...document.querySelectorAll('a,button,li,div,span,[role=button],[onclick]')];
    let best=null,blen=1e9;
    for(const el of els){ const t=norm(el.textContent);
      if(!t||t.length>24) continue;
      for(const w of want){ if(t===w||t.includes(w)){ if(t.length<blen){best=el;blen=t.length;} } }
    }
    if(best){ try{best.scrollIntoView({block:'center'});}catch(e){} best.click(); return (best.textContent||'').trim().slice(0,30); }
    return null;
  }, labels).catch(()=>null);
  if(res){ await log(`OK clicou "${res}" (alvo: ${nome})`); return true; }
  await log(`!! NAO achei "${nome}" (tentei: ${labels.join(', ')})`);
  return false;
}

// diagnostico: nomes reais do menu + se entrou logado ou no cadastro
async function diag(page){
  const info = await page.evaluate(()=>{
    const norm=s=>(s||'').replace(/\s+/g,' ').trim();
    const navs=[...document.querySelectorAll('nav, footer, [class*=nav], [class*=tab], [class*=bottom]')];
    let labels=[];
    for(const n of navs){ [...n.querySelectorAll('*')].forEach(e=>{const t=norm(e.textContent); if(t&&t.length<16) labels.push(t);}); }
    labels=[...new Set(labels)].slice(0,30);
    const body=norm(document.body.innerText);
    const logged=/ol[aá]|reservar meu|pr[oó]ximo hor/i.test(body);
    const cadastro=/bem-vindo|criar (minha )?conta|sem senha/i.test(body);
    return {labels, logged, cadastro, snip: body.slice(0,180)};
  }).catch(()=>({labels:[],logged:false,cadastro:false,snip:''}));
  await log('NAV LABELS: '+JSON.stringify(info.labels));
  await log('ESTADO: '+(info.logged?'HOME (logado)':(info.cadastro?'CADASTRO (nao logou)':'? indefinido')));
  await log('TEXTO: '+info.snip.replace(/\n/g,' '));
}

async function screen(page, nome, dwellMs){
  marks[nome]=now();
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS, `${nome}.png`) }).catch(()=>{});
  await log(`--- tela "${nome}" capturada`);
  if(dwellMs) await page.waitForTimeout(dwellMs);
}

(async () => {
  const browser = await chromium.launch({ headless:true,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--hide-scrollbars','--autoplay-policy=no-user-gesture-required'] });
  const ctx = await browser.newContext({ viewport:{width:VW,height:VH}, deviceScaleFactor:2, isMobile:true, hasTouch:true,
    recordVideo:{ dir:OUT, size:{width:VW,height:VH} } });
  await ctx.addInitScript((seed)=>{ try{ for(const k of seed.keys) localStorage.setItem(k, JSON.stringify(seed.cliente)); }catch(e){}
    try{ localStorage.setItem('aloco_logado','1'); localStorage.setItem('logado','1'); }catch(e){} }, { keys:SEED_KEYS, cliente:CLIENTE });

  const page = await ctx.newPage();
  t0 = Date.now();
  await log(`abrindo: ${APP_URL}`);
  try{ await page.goto(APP_URL,{waitUntil:'domcontentloaded',timeout:30000}); }
  catch(e){ await log(`ERRO ao abrir: ${e.message}`); }
  await page.waitForTimeout(1200);
  await screen(page,'00_splash',2600);
  await page.waitForLoadState('networkidle',{timeout:15000}).catch(()=>{});
  await diag(page);                       // << me diz os nomes do menu e se logou

  await tap(page, ['Inicio','Início','Home'], 'nav Inicio');
  await page.waitForTimeout(800);
  await screen(page,'01_inicio',4500);
  await page.mouse.wheel(0,260); await page.waitForTimeout(1000);
  await screen(page,'02_inicio_reservar',4500);
  await page.mouse.wheel(0,-260); await page.waitForTimeout(400);

  await tap(page, ['Agendar','Agenda','Reservar meu horario','Reservar'], 'nav Agendar');
  await page.waitForTimeout(1000);
  await screen(page,'03_agendar',4500);
  await tap(page, ['Corte','Corte + Barba','Barba'], 'servico');
  await page.waitForTimeout(900);
  await screen(page,'04_servico',4500);

  await tap(page, ['Fila','Entrar na fila','Entre na fila','Sem marcar','Espera'], 'nav Fila');
  await page.waitForTimeout(1000);
  await screen(page,'05_fila',4500);

  await tap(page, ['Pacotes','Pacote','Planos'], 'nav Pacotes');
  await page.waitForTimeout(1000);
  await screen(page,'06_pacotes',4500);

  await tap(page, ['Perfil','Conta','Meu perfil'], 'nav Perfil');
  await page.waitForTimeout(1000);
  await screen(page,'07_perfil',4500);

  await tap(page, ['Inicio','Início','Home'], 'nav Inicio (volta)');
  await page.waitForTimeout(900);
  await screen(page,'08_inicio_fim',4500);

  await log('gravacao concluida, salvando...');
  const video = page.video();
  await page.close(); await ctx.close(); await browser.close();
  const vpath = await video.path().catch(()=>null);
  if(vpath){ const dest=path.join(OUT,'app.webm'); try{fs.renameSync(vpath,dest);}catch(e){fs.copyFileSync(vpath,dest);} console.log('VIDEO:',dest); }
  fs.writeFileSync(path.join(OUT,'marks.json'), JSON.stringify(marks,null,2));
  console.log('MARKS:', JSON.stringify(marks));
  console.log('\n==> Me mande este LOG inteiro (o de cima ja me diz quase tudo). Prints: work/'+SLUG+'/screens/');
})().catch(e=>{ console.error('FATAL',e); process.exit(1); });
