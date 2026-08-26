#!/usr/bin/env bash
set -e

echo "===> [1/8] Node.js 20 + git"
dnf module reset -y nodejs 2>/dev/null || true
dnf module disable -y nodejs 2>/dev/null || true
dnf remove -y nodejs npm nsolid nodejs-full-i18n 2>/dev/null || true
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs git --allowerasing
node -v

echo "===> [2/8] ffmpeg (build estatico)"
if ! command -v ffmpeg >/dev/null 2>&1; then
  cd /tmp
  curl -L -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
  tar xf ffmpeg.tar.xz
  cp ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe /usr/local/bin/
  rm -rf ffmpeg.tar.xz ffmpeg-*-static
fi
ffmpeg -version | head -1

echo "===> [3/8] Bibliotecas do Chromium headless"
dnf install -y alsa-lib atk at-spi2-atk at-spi2-core cups-libs libdrm mesa-libgbm \
  libxkbcommon libX11 libXcomposite libXdamage libXext libXfixes libXrandr \
  libXrender libXtst nss nspr pango cairo gtk3 || true

echo "===> [4/8] Baixar o codigo"
cd ~
rm -rf barbervideoservice
git clone https://github.com/marcosdinizaloco/barbervideoservice.git
cd barbervideoservice

echo "===> [5/8] Dependencias Node + Chromium do Playwright"
npm install
npx playwright install chromium

echo "===> [6/8] Narracao placeholder (30s silencio)"
mkdir -p assets output tmp
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 30 -q:a 9 assets/narracao-fixa.mp3

echo "===> [7/8] Abrir porta 3300 no firewall"
firewall-cmd --add-port=3300/tcp --permanent 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

echo "===> [8/8] Subir o servico com pm2"
npm install -g pm2
IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
export PORT=3300
export TOKEN="TROQUE_POR_UMA_SENHA_FORTE"
export PUBLIC_BASE_URL="http://$IP:3300"
pm2 delete barber-video-service >/dev/null 2>&1 || true
pm2 start server.js --name barber-video-service --update-env
pm2 save
pm2 startup systemd -u root --hp /root >/dev/null 2>&1 || true

echo ""
echo "=================================================================="
echo "  PRONTO! Servico no ar em:  http://$IP:3300"
echo "  Teste:  curl http://$IP:3300/status"
echo "=================================================================="
