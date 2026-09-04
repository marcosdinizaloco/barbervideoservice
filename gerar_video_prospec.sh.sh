#!/usr/bin/env bash
# gerar_video_prospec.sh <url_da_logo> <nome_da_barbearia> <slug>
# Caminho da prospeccao: a logo vem da planilha, nao do app.
# Mesmo principio: UMA logo master alimenta o video E a arte.
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

echo "==> 1/5 LOGO MASTER (validacao + tratamento, fonte unica)..."
python3 "$BASE/logo_master.py" "$URL_LOGO" "$W" "$NOME"

echo "==> 2/5 marca d'agua a partir da LOGO MASTER..."
python3 "$BASE/marca.py" "$W/logo_master.png" "$W/marca.png"

echo "==> 3/5 arte com a MESMA LOGO MASTER..."
python3 "$BASE/gerar_arte.py" "$W/logo_master.png" "$BASE/saidas/${SLUG}_arte.jpg" || echo "    (arte falhou, seguindo)"

echo "==> 4/5 video com a MESMA LOGO MASTER (alguns minutos)..."
python3 "$BASE/render.py" "$BASE/base.mp4" "$BASE/marcas.json" \
  "$W/logo_master.png" "$W/marca.png" "$NOME" "$BASE/saidas/$SLUG.mp4"

echo "==> 5/5 capa..."
ffmpeg -y -loglevel error -ss 84 -i "$BASE/saidas/$SLUG.mp4" -frames:v 1 -q:v 3 \
  "$BASE/saidas/${SLUG}_capa.jpg"

echo "=================================================="
echo "  LOGO:  $(python3 -c "import json;d=json.load(open('$W/logo_master.json'));print(('VALIDA' if d['valida'] else 'REJEITADA')+' - '+d['motivo']+' | '+d['tratamento'])" 2>/dev/null || echo '?')"
echo "  VIDEO: saidas/$SLUG.mp4  ($(du -m "$BASE/saidas/$SLUG.mp4" | cut -f1) MB)"
echo "  ARTE:  saidas/${SLUG}_arte.jpg"
echo "=================================================="
