#!/usr/bin/env bash
URL="$1"; SLUG="$2"
[ -z "$SLUG" ] && { echo "uso: bash gerar_video.sh <url_do_app> <slug>"; exit 1; }
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/chrome.mp4" ] || { echo "ERRO: falta chrome.mp4 no repo"; exit 1; }
echo "==> 1/3 gravando o app..."; node "$BASE/gravar_app.js" "$URL" "$SLUG"
echo "==> 2/3 cortando o reel..."; node "$BASE/montar_reel.js" "work/$SLUG"
echo "==> 3/3 encaixando..."; mkdir -p "$BASE/saidas"
bash "$BASE/encaixar.sh" "$BASE/chrome.mp4" "work/$SLUG/reel.mp4" "$BASE/saidas/$SLUG.mp4"
echo "=================================================="
echo "  VIDEO PRONTO: saidas/$SLUG.mp4  (baixe no cPanel)"
echo "=================================================="
