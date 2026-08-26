// ROTEIRO DO PASSEIO — APLICATIVO do cliente (mobile). Tempos casam com a narracao.
module.exports = [
  { t: 0,    action: { type: 'wait', ms: 5600 } },                       // splash (logo do cliente)
  { t: 5.6,  action: { type: 'wait', ms: 6000 } },                       // tela inicial (home)
  { t: 11.6, action: { type: 'scroll', selector: '.screen.active', y: 260 } },
  { t: 15.1, action: { type: 'scroll', selector: '.screen.active', y: 0 } },
  { t: 19.0, action: { type: 'nav', screen: 'agenda' } },                // agendar: servicos
  { t: 22.0, action: { type: 'click', selector: '.svc' } },
  { t: 23.5, action: { type: 'click', selector: '#ag-cta-0' } },
  { t: 25.3, action: { type: 'click', selector: '.barber' } },
  { t: 26.8, action: { type: 'click', selector: '#ag-cta-1' } },
  { t: 29.3, action: { type: 'nav', screen: 'fila' } },                  // fila ao vivo
  { t: 33.1, action: { type: 'nav', screen: 'pacotes' } },               // pacotes
  { t: 36.3, action: { type: 'nav', screen: 'perfil' } },                // perfil
];
// Duracao total — ajusto pra bater com a duracao real do seu audio.
module.exports.DURACAO_TOTAL_SEGUNDOS = 40;
