#!/usr/bin/env bash
CHROME="$1"; REEL="$2"; OUT="$3"
[ -z "$OUT" ] && { echo "uso: bash encaixar.sh <chrome.mp4> <reel.mp4> <saida.mp4>"; exit 1; }
ffmpeg -y -loglevel error -i "$CHROME" -i "$REEL" -filter_complex \
"[1:v]tpad=start_duration=2.7:start_mode=add:color=black:stop_duration=4:stop_mode=clone,\
scale=408:985:force_original_aspect_ratio=decrease,pad=408:985:(ow-iw)/2:(oh-ih)/2:black,setsar=1[app];\
color=c=black:s=1080x1920:r=30[bg];\
[bg][app]overlay=326:372:shortest=1[b1];\
[0:v]colorkey=0x00FF00:0.35:0.12[ck];\
[b1][ck]overlay=shortest=1[v]" \
-map "[v]" -map 0:a -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
echo "PRONTO: $OUT"
