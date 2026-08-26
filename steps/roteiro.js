// ROTEIRO DO PASSEIO — APLICATIVO (mobile) — 70s, casa com a narracao
module.exports = [
  { t: 0,    action: { type: 'wait', ms: 6000 } },                        // splash (logo)
  { t: 6,    action: { type: 'wait', ms: 4000 } },                        // tela inicial
  { t: 10,   action: { type: 'scroll', selector: '.screen.active', y: 260 } },
  { t: 14,   action: { type: 'scroll', selector: '.screen.active', y: 480 } },
  { t: 18,   action: { type: 'scroll', selector: '.screen.active', y: 0 } },
  { t: 20,   action: { type: 'nav', screen: 'agenda' } },                 // agendar
  { t: 24,   action: { type: 'click', selector: '.svc' } },
  { t: 26,   action: { type: 'click', selector: '#ag-cta-0' } },
  { t: 30,   action: { type: 'click', selector: '.barber' } },
  { t: 32,   action: { type: 'click', selector: '#ag-cta-1' } },
  { t: 38,   action: { type: 'nav', screen: 'fila' } },                   // fila ao vivo
  { t: 50,   action: { type: 'nav', screen: 'pacotes' } },                // pacotes
  { t: 60,   action: { type: 'nav', screen: 'perfil' } },                 // perfil
];
module.exports.DURACAO_TOTAL_SEGUNDOS = 72;
