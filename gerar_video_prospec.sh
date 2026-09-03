#!/usr/bin/env bash
# gerar_video_prospec.sh <url_da_logo> <nome_da_barbearia> <slug>
set -e
URL_LOGO="$1"; NOME="$2"; SLUG="$3"
[ -z "$SLUG" ] && { echo "uso: bash gerar_video_prospec.sh <url_logo> <nome> <slug>"; exit 1; }
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/base.mp4" ] || { echo "ERRO: falta base.mp4"; exit 1; }
[ -f "$BASE/.env" ] && { set -a; . "$BASE/.env"; set +a; }
W="$BASE/work/$SLUG"; mkdir -p "$W" "$BASE/saidas"

python3 -c "import PIL" 2>/dev/null || pip3 install --quiet pillow || pip3 install --quiet --break-system-packages pillow

exec 9>"$BASE/.fila.lock"
if ! flock -w 1500 9; then echo "ERRO: fila cheia"; exit 1; fi

echo "==> 1/4 tratando a logo..."
python3 "$BASE/logo_prospec.py" "$URL_LOGO" "$W"
echo "==> 2/4 gerando a arte..."
python3 "$BASE/gerar_arte.py" "$W/logo_tela.png" "$BASE/saidas/${SLUG}_arte.jpg" || echo "    (arte falhou, seguindo)"
echo "==> 3/4 montando o video (alguns minutos)..."
python3 "$BASE/render.py" "$BASE/base.mp4" "$BASE/marcas.json" \
  "$W/logo_tela.png" "$W/marca.png" "$NOME" "$BASE/saidas/$SLUG.mp4"
echo "==> 4/4 capa..."
ffmpeg -y -loglevel error -ss 84 -i "$BASE/saidas/$SLUG.mp4" -frames:v 1 -q:v 3 \
  "$BASE/saidas/${SLUG}_capa.jpg"
echo "=================================================="
echo "  VIDEO: saidas/$SLUG.mp4  ($(du -m "$BASE/saidas/$SLUG.mp4" | cut -f1) MB)"
echo "  ARTE:  saidas/${SLUG}_arte.jpg"
echo "=================================================="
