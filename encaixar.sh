#!/usr/bin/env bash
# encaixar.sh <template_verde.mp4> <reel.mp4> <saida.mp4>
# Template cinematografico v2: a tela verde SE MOVE (cortes de camera, escala,
# rotacao). O encaixe e feito frame a frame pelo compose_video.py, que tambem:
#  - aplica a logo do cliente como marca d'agua (extraida do splash do reel)
#  - mixa narracao (narracao_nova.mp3) + trilha do template com ducking
# Requisitos: python3 + `pip3 install opencv-python-headless numpy` + ffmpeg
set -e
TPL="$1"; REEL="$2"; OUT="$3"
[ -z "$OUT" ] && { echo "uso: bash encaixar.sh <template_verde.mp4> <reel.mp4> <saida.mp4>"; exit 1; }
BASE="$(cd "$(dirname "$0")" && pwd)"
python3 "$BASE/compose_video.py" "$TPL" "$REEL" "$BASE/narracao_nova.mp3" auto "$OUT"
echo "PRONTO: $OUT"
