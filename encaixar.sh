#!/usr/bin/env bash
# encaixar.sh <chrome.mp4> <reel.mp4> <saida.mp4>
# Encaixa o app no buraco verde + MOVIMENTO DE CAMERA suave (nivel comercial):
# - renderiza em 2x (supersampling) pra ficar liso, SEM tremido.
# - movimento continuo e lento: respiro (aproxima/afasta) + leve deslize p/ esquerda.
set -e
CHROME="$1"; REEL="$2"; OUT="$3"
[ -z "$OUT" ] && { echo "uso: bash encaixar.sh <chrome.mp4> <reel.mp4> <saida.mp4>"; exit 1; }
ffmpeg -y -loglevel error -i "$CHROME" -i "$REEL" -filter_complex \
"[1:v]tpad=start_duration=2.7:start_mode=add:color=black:stop_duration=4:stop_mode=clone,\
scale=408:985:force_original_aspect_ratio=decrease,pad=408:985:(ow-iw)/2:(oh-ih)/2:black,setsar=1[app];\
color=c=black:s=1080x1920:r=30[bg];\
[bg][app]overlay=326:372:shortest=1[b1];\
[0:v]colorkey=0x00FF00:0.35:0.12[ck];\
[b1][ck]overlay=shortest=1[comp];\
[comp]scale=2160:3840,\
zoompan=z='1.035+0.013*sin(2*PI*on/510)':x='iw/2-(iw/zoom/2)-16*sin(2*PI*on/620)':y='ih/2-(ih/zoom/2)+10*sin(2*PI*on/450)':d=1:s=2160x3840:fps=30,\
scale=1080:1920:flags=lanczos,\
eq=contrast=1.06:saturation=1.06:brightness=-0.006,colorbalance=bs=0.03:bm=0.015:rs=-0.015,setsar=1[v]" \
-map "[v]" -map 0:a -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
echo "PRONTO: $OUT"
