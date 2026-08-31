# Template cinematográfico v2 — o que mudou

## Arquivos novos
- `template_verde.mp4` — novo template (101,5s): mão segurando o phone o vídeo
  inteiro, 8 planos com cortes de câmera, fundo cinematográfico, tela verde
  em movimento, trilha + sound design no áudio (sem narração).
- `narracao_nova.mp3` — narração completa (101,5s), a mesma para todas.
- `compose_video.py` — compositor frame a frame: encaixa o reel na tela verde
  (que agora se move), extrai a logo do app do próprio reel e aplica como
  marca d'água, mixa narração + trilha com ducking automático.

## Arquivos alterados
- `encaixar.sh` — agora chama o compose_video.py (o overlay estático do ffmpeg
  não funciona com tela em movimento).
- `gerar_video.sh` — usa template_verde.mp4 no lugar de chrome.mp4.
- `montar_reel.js` — reel de ~101s (era ~42s) para cobrir a nova narração.
- `gravar_app.js` — dwell de 4,5s por tela (o reel novo extrai até 3,8s crus).
- `install.sh` — instala python3 + opencv (dependência do compositor).

## Na VPS (uma vez)
```bash
git pull
pip3 install opencv-python-headless numpy
```

## Fluxo (inalterado para o n8n / Z-API)
POST /api/gerar {url} continua igual — o server.js não mudou.
A geração agora leva ~6-8 min (era ~3) por causa do template maior;
aumente o timeout do nó HTTP do n8n para 600000 ms.
`chrome.mp4` e `narracao_1.mp3` podem ser removidos depois de validar.
