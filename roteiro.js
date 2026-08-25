/**
 * ROTEIRO DE NAVEGAÇÃO DO WALKTHROUGH
 * ────────────────────────────────────────────────────────────────
 * Cada item = uma etapa da narração fixa. `t` é o instante (em
 * segundos, a partir do início do vídeo) em que aquela ação deve
 * acontecer na tela — sincronizado com o que está sendo falado
 * no áudio naquele momento.
 *
 * ESTES TEMPOS SÃO ESTIMADOS. Assim que você me mandar o áudio
 * final (ou a transcrição com timestamps), eu ajusto os valores
 * de `t` aqui pra bater exatamente com a locução.
 *
 * `action` pode ser:
 *   - { type: 'click', selector: '#nb-agd' }       → clica num botão do menu
 *   - { type: 'wait',  ms: 1500 }                   → só espera (dá tempo de ver a tela)
 *   - { type: 'scroll', selector: '.ct', y: 400 }   → rola a página
 *   - { type: 'hover', selector: '.EQ-CARD' }       → passa o mouse (efeito visual)
 */

module.exports = [
  // 0s – abre no Centro de Controle (tela padrão já abre aqui via window.onload)
  { t: 0,    action: { type: 'wait', ms: 3000 } },                       // "Aqui está o painel da sua barbearia..."

  // 3s – Central de Controle: mostra KPIs e IA
  { t: 3,    action: { type: 'scroll', selector: '.ct', y: 250 } },
  { t: 5,    action: { type: 'wait', ms: 3000 } },                       // "...com receita, ocupação e oportunidades em tempo real"

  // 8s – Agenda
  { t: 8,    action: { type: 'click', selector: '#nb-agd' } },
  { t: 8.5,  action: { type: 'wait', ms: 3500 } },                       // "aqui você vê e organiza a agenda do dia"

  // 12s – Profissionais
  { t: 12,   action: { type: 'click', selector: '#nb-barb' } },
  { t: 12.5, action: { type: 'wait', ms: 3000 } },                       // "acompanha o desempenho de cada profissional"

  // 16s – Clientes 360
  { t: 16,   action: { type: 'click', selector: '#nb-cli' } },
  { t: 16.5, action: { type: 'wait', ms: 3000 } },                       // "e conhece sua base de clientes a fundo"

  // 20s – Financeiro
  { t: 20,   action: { type: 'click', selector: '#nb-fin' } },
  { t: 20.5, action: { type: 'wait', ms: 4000 } },                       // "todo o financeiro, sempre atualizado"

  // 25s – encerramento, volta pra Central de Controle
  { t: 25,   action: { type: 'click', selector: '#nb-home' } },
  { t: 25.5, action: { type: 'wait', ms: 3500 } },                       // "esse é o seu novo painel. bem-vindo!"
];

// Duração total do vídeo (em segundos) — deve bater com a duração
// real do arquivo de áudio da narração fixa.
module.exports.DURACAO_TOTAL_SEGUNDOS = 30;
