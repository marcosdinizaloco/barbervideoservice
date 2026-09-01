#!/usr/bin/env bash
# gerar_video.sh <url_do_app> <slug>
# Usa o video aprovado (base.mp4) e troca pela marca da barbearia:
#   - a logo dentro da tela do celular (abertura do app)
#   - o nome no titulo "BEM-VINDO A ..."
#   - a marca d'agua de baixo
# Fila automatica: um video de cada vez (VPS de 1 vCPU).
set -e
URL="$1"; SLUG="$2"
[ -z "$SLUG" ] && { echo "uso: bash gerar_video.sh <url_do_app> <slug>"; exit 1; }
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/base.mp4" ] || { echo "ERRO: falta base.mp4 no repo"; exit 1; }
W="$BASE/work/$SLUG"; mkdir -p "$W" "$BASE/saidas"

python3 -c "import PIL" 2>/dev/null || pip3 install --quiet pillow || pip3 install --quiet --break-system-packages pillow

exec 9>"$BASE/.fila.lock"
if ! flock -w 1500 9; then echo "ERRO: fila cheia, tente de novo"; exit 1; fi

echo "==> 1/5 abrindo o app do cliente..."
node "$BASE/logo_cliente.js" "$URL" "$W"
NOME="$(cat "$W/nome.txt" 2>/dev/null || true)"
echo "    nome: $NOME"
echo "==> 2/5 montando a marca d'agua..."
python3 "$BASE/marca.py" "$W/splash.png" "$W/marca.png"
echo "==> 3/5 recortando a logo para a tela..."
python3 "$BASE/logo_tela.py" "$W/splash.png" "$W/logo_tela.png"
echo "==> 4/5 aplicando no video (leva alguns minutos)..."
python3 "$BASE/render.py" "$BASE/base.mp4" "$BASE/marcas.json" \
  "$W/logo_tela.png" "$W/marca.png" "$NOME" "$BASE/saidas/$SLUG.mp4"
echo "==> 5/5 gerando a capa..."
ffmpeg -y -loglevel error -ss 84 -i "$BASE/saidas/$SLUG.mp4" -frames:v 1 -q:v 3 \
  "$BASE/saidas/${SLUG}_capa.jpg"
echo "=================================================="
echo "  VIDEO PRONTO: saidas/$SLUG.mp4  ($(du -m "$BASE/saidas/$SLUG.mp4" | cut -f1) MB)"
echo "  CAPA:         saidas/${SLUG}_capa.jpg"
echo "=================================================="
