#!/usr/bin/env bash
echo "==> Gerando video de teste (aguarde ~1 minuto: ele grava a tela + junta o audio)..."
RESP=$(curl -sX POST http://127.0.0.1:3300/gerar-video \
  -H "Content-Type: application/json" \
  -H "x-token: TROQUE_POR_UMA_SENHA_FORTE" \
  -d '{"url":"https://app.aloco.com.br/painel/the-corte","slug":"teste-the-corte"}')
echo ""
echo "==> RESPOSTA DO SERVIDOR:"
echo "$RESP"
echo ""
echo "==> Se apareceu um videoUrl acima, ABRA ele no navegador pra assistir o video!"
