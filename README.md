# Barber Video Service

Serviço que grava automaticamente um walkthrough em vídeo de cada
painel de barbearia gerado pelo Barber OS, junta com uma narração
fixa (a mesma pra todas), e devolve o link do `.mp4` pronto pro n8n
mandar pelo WhatsApp via Z-API.

---

## 1. O que você precisa antes de instalar

- Um servidor (VPS) Linux (Ubuntu 22.04 ou 24.04 recomendado).
  - Planos pequenos servem pra começar: 2 vCPU / 4GB RAM já grava
    tranquilo. Se for gerar muitos vídeos ao mesmo tempo, considere
    mais CPU (a gravação e o ffmpeg consomem processamento).
- O arquivo de narração fixa em MP3 (a mesma locução pra todo mundo).
- Acesso SSH ao servidor.

---

## 2. Instalação no servidor (rodar uma vez)

```bash
# atualizar o sistema
sudo apt-get update && sudo apt-get upgrade -y

# instalar Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# instalar ffmpeg
sudo apt-get install -y ffmpeg

# instalar pm2 (mantém o serviço rodando sempre)
sudo npm install -g pm2

# ir para a pasta do projeto (depois de enviar os arquivos pro servidor)
cd barber-video-service

# instalar dependências
npm install

# instalar o Chromium do Playwright + libs necessárias do sistema
npx playwright install --with-deps chromium
```

## 3. Colocar a narração fixa

```bash
mkdir -p assets
# copie seu arquivo de áudio pra cá, com esse nome exato:
# assets/narracao-fixa.mp3
```

> Depois de colocar o áudio real, me avise a duração exata dele
> (em segundos) que eu ajusto o `steps/roteiro.js` pra bater
> certinho com a fala.

## 4. Configurar e subir o serviço

```bash
# variáveis de ambiente (ajuste os valores)
export PORT=3300
export PUBLIC_BASE_URL="https://videos.seudominio.com"
export TOKEN="uma-senha-forte-aleatoria"

# subir com pm2 (mantém rodando e reinicia sozinho se cair)
pm2 start server.js --name barber-video-service \
  --env production \
  -- --port $PORT

pm2 save
pm2 startup   # segue as instruções que aparecerem na tela
```

Deixe a porta 3300 (ou a que você usar) acessível publicamente
(direto ou atrás de um Nginx com HTTPS — recomendado usar HTTPS
porque o Z-API precisa buscar o vídeo por uma URL pública).

### Exemplo de proxy Nginx com HTTPS (recomendado)

```nginx
server {
    listen 80;
    server_name videos.seudominio.com;
    location / {
        proxy_pass http://localhost:3300;
    }
}
```
Depois rode `sudo certbot --nginx -d videos.seudominio.com` pra
gerar o certificado HTTPS gratuito (Let's Encrypt).

## 5. Testar manualmente antes de plugar no n8n

```bash
curl -X POST https://videos.seudominio.com/gerar-video \
  -H "Content-Type: application/json" \
  -H "x-token: uma-senha-forte-aleatoria" \
  -d '{
    "url": "https://seuapp.com/painel/barbearia-teste",
    "slug": "barbearia-teste",
    "senha": "senha-do-painel-se-tiver"
  }'
```

Resposta esperada:
```json
{ "ok": true, "videoUrl": "https://videos.seudominio.com/videos/barbearia-teste_1234567890.mp4" }
```

## 6. Plugar no n8n

1. Importe `n8n-workflow-video.json` no seu n8n (Workflows → Import from File/JSON).
2. Ligue a saída do seu fluxo atual (o que já publica o app e gera
   os links) na entrada do node **"2. Gerar vídeo"**.
3. Ajuste a URL do node HTTP Request pra apontar pro seu domínio
   (`https://videos.seudominio.com/gerar-video`).
4. Configure a variável de ambiente `VIDEO_SERVICE_TOKEN` no n8n
   (Settings → Variables) com o mesmo valor do `TOKEN` do servidor.
5. Ajuste os dois nodes de Z-API (texto e vídeo) com sua instância/token reais.

## 7. Fila e escala

O servidor já processa **um vídeo por vez** (fila interna), pra não
sobrecarregar o servidor gravando várias telas + rodando ffmpeg ao
mesmo tempo. Se o volume crescer bastante, dá pra:
- Aumentar os recursos do VPS, ou
- Rodar 2 instâncias do serviço em servidores diferentes e
  balancear no n8n (ex: round-robin simples).

## 8. Arquivos do projeto

```
barber-video-service/
├── server.js              → servidor HTTP (endpoint /gerar-video)
├── scripts/
│   ├── record.js          → grava a tela com Playwright
│   └── mesclar.js         → junta vídeo + áudio fixo (ffmpeg)
├── steps/
│   └── roteiro.js         → timeline de navegação (AJUSTAR com o áudio real)
├── assets/
│   └── narracao-fixa.mp3  → (você adiciona) narração fixa
├── output/                → vídeos finais prontos (.mp4)
├── tmp/                   → gravações brutas temporárias
└── n8n-workflow-video.json → workflow pronto pra importar
```
