#!/usr/bin/env bash
# gerar_video.sh <url_do_app> <slug>
# Uma unica LOGO MASTER alimenta o video E a arte.
#   1. abre o app do cliente e pega o ENDERECO ORIGINAL da logo + o nome
#   2. logo_master.py: valida (rejeita fotografia), restaura e recorta o fundo
#   3. a MESMA logo_master.png vai para a marca d'agua, para a arte e para o video
set -e
URL="$1"; SLUG="$2"
[ -z "$SLUG" ] && { echo "uso: bash gerar_video.sh <url_do_app> <slug>"; exit 1; }
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/base.mp4" ] || { echo "ERRO: falta base.mp4 no repo"; exit 1; }
[ -f "$BASE/.env" ] && { set -a; . "$BASE/.env"; set +a; }
W="$BASE/work/$SLUG"; mkdir -p "$W" "$BASE/saidas"

python3 -c "import PIL" 2>/dev/null || pip3 install --quiet pillow || pip3 install --quiet --break-system-packages pillow

exec 9>"$BASE/.fila.lock"
if ! flock -w 1500 9; then echo "ERRO: fila cheia, tente de novo"; exit 1; fi

echo "==> 1/6 abrindo o app do cliente..."
node "$BASE/logo_cliente.js" "$URL" "$W"
NOME="$(cat "$W/nome.txt" 2>/dev/null || true)"
LOGO_SRC="$(cat "$W/logo_url.txt" 2>/dev/null || true)"
echo "    nome: $NOME"

if [ -z "$LOGO_SRC" ]; then
  echo "    (nao achei o endereco da logo no HTML; caio para o print da abertura)"
  python3 "$BASE/logo_tela.py" "$W/splash.png" "$W/logo_da_splash.png"
  LOGO_SRC="$W/logo_da_splash.png"
fi

echo "==> 2/6 LOGO MASTER (validacao + tratamento, fonte unica)..."
python3 "$BASE/logo_master.py" "$LOGO_SRC" "$W" "$NOME"

echo "==> 3/6 marca d'agua a partir da LOGO MASTER..."
python3 "$BASE/marca.py" "$W/logo_master.png" "$W/marca.png"

echo "==> 4/6 arte com a MESMA LOGO MASTER..."
python3 "$BASE/gerar_arte.py" "$W/logo_master.png" "$BASE/saidas/${SLUG}_arte.jpg" || echo "    (arte falhou, seguindo)"

echo "==> 5/6 video com a MESMA LOGO MASTER (leva alguns minutos)..."
python3 "$BASE/render.py" "$BASE/base.mp4" "$BASE/marcas.json" \
  "$W/logo_master.png" "$W/marca.png" "$NOME" "$BASE/saidas/$SLUG.mp4"

echo "==> 6/6 capa..."
ffmpeg -y -loglevel error -ss 84 -i "$BASE/saidas/$SLUG.mp4" -frames:v 1 -q:v 3 \
  "$BASE/saidas/${SLUG}_capa.jpg"

echo "=================================================="
echo "  LOGO:  $(python3 -c "import json,sys;d=json.load(open('$W/logo_master.json'));print(('VALIDA' if d['valida'] else 'REJEITADA')+' - '+d['motivo']+' | '+d['tratamento'])" 2>/dev/null || echo '?')"
echo "  VIDEO: saidas/$SLUG.mp4  ($(du -m "$BASE/saidas/$SLUG.mp4" | cut -f1) MB)"
echo "  ARTE:  saidas/${SLUG}_arte.jpg"
echo "=================================================="
