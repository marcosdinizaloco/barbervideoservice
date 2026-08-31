#!/usr/bin/env python3
"""
Barber Video Service — Compositor (template cinematográfico v2)
===============================================================
Gera o comercial final de um novo aplicativo a partir do template com
tela verde EM MOVIMENTO (cortes de câmera, escala e rotação variáveis).

Uso:
    python3 compose_video.py TEMPLATE.mp4 REEL.mp4 NARRACAO.mp3 LOGO SAIDA.mp4

- TEMPLATE.mp4 . template_verde.mp4 (101.5s, tela verde, trilha+SFX no áudio)
- REEL.mp4 ..... reel do app do cliente (montar_reel.js; sem áudio)
- NARRACAO.mp3 . narração (narracao_nova.mp3 — a mesma para todas)
- LOGO ......... caminho de um PNG da logo do cliente, OU "auto" para
                 extrair automaticamente a logo do reel (splash do app)
- SAIDA.mp4 .... vídeo final

O verde é detectado FRAME A FRAME (a tela se move); o conteúdo é encaixado
na área exata do display — nunca ultrapassa a moldura. A logo do cliente
vira marca d'água na posição fixa reservada (300x300 @ centro, y=1440).
Áudio: narração em primeiro plano + trilha do template com ducking.

Requisitos: python3 + `pip3 install opencv-python-headless numpy` + ffmpeg.
"""
import cv2, numpy as np, subprocess, sys, os, tempfile

def extrair_logo_auto(reel_path):
    """Extrai a logo do splash do app (mesma posição relativa do layout ALOCO)."""
    cap = cv2.VideoCapture(reel_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(12.0 * fps))  # logo carregada (~12s)
    ok, fr = cap.read(); cap.release()
    if not ok: return None
    h, w = fr.shape[:2]
    # posição relativa da logo no header do app (layout padrão ALOCO)
    cx, cy, r = int(w * 0.4853), int(h * 0.0859), max(20, int(w * 0.1174 / 2))
    y1, y2 = max(0, cy - r), min(h, cy + r)
    x1, x2 = max(0, cx - r), min(w, cx + r)
    crop = fr[y1:y2, x1:x2]
    if crop.size == 0: return None
    return crop

def main():
    if len(sys.argv) != 6:
        print(__doc__); sys.exit(1)
    TPL, REEL, NARR, LOGO, OUT = sys.argv[1:6]

    cap_t = cv2.VideoCapture(TPL)
    fps = cap_t.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap_t.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap_t.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_t = int(cap_t.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = n_t / fps

    cap_a = cv2.VideoCapture(REEL)
    fps_a = cap_a.get(cv2.CAP_PROP_FPS) or 30.0
    aw = int(cap_a.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap_a.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # ── logo → marca d'água (luminance alpha, sem círculo adicional) ────────
    LOGO_SIZE, LOGO_X, LOGO_Y = 300, (W - 300) // 2, 1440
    if LOGO.lower() == "auto":
        lg_raw = extrair_logo_auto(REEL)
        if lg_raw is None:
            print("ERRO: não consegui extrair a logo do reel"); sys.exit(2)
        lg_img = cv2.resize(lg_raw, (LOGO_SIZE, LOGO_SIZE),
                            interpolation=cv2.INTER_LANCZOS4)
        has_alpha = False
    else:
        lg_img = cv2.imread(LOGO, cv2.IMREAD_UNCHANGED)
        if lg_img is None:
            print(f"ERRO: não consegui ler a logo {LOGO}"); sys.exit(2)
        lg_img = cv2.resize(lg_img, (LOGO_SIZE, LOGO_SIZE),
                            interpolation=cv2.INTER_LANCZOS4)
        has_alpha = lg_img.ndim == 3 and lg_img.shape[2] == 4

    if has_alpha:
        lg_bgr = lg_img[:, :, :3].astype(np.float32)
        lg_alpha = lg_img[:, :, 3].astype(np.float32) / 255.0
    else:
        lg_bgr = np.clip(lg_img[:, :, :3].astype(np.float32) * 1.60 + 6, 0, 255)
        gray = cv2.cvtColor(lg_bgr.astype(np.uint8), cv2.COLOR_BGR2GRAY)
        lg_alpha = np.clip((gray.astype(np.float32) - 16) / 148, 0, 1.0) ** 0.60
    lg_alpha = cv2.GaussianBlur(lg_alpha, (3, 3), 0) * 0.90
    lg_a3 = cv2.merge([lg_alpha.astype(np.float32)] * 3)

    tmp_v = os.path.join(tempfile.gettempdir(), "bvs_noaudio.mp4")
    pipe = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
        "-vcodec", "rawvideo", "-s", f"{W}x{H}", "-pix_fmt", "bgr24",
        "-r", str(fps), "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", tmp_v], stdin=subprocess.PIPE)

    LG = np.array([45, 110, 110]); UG = np.array([80, 255, 255])
    ri = 0
    a_frame = None

    for fi in range(n_t):
        ok_t, tf = cap_t.read()
        if not ok_t: break

        target_ri = int(fi * fps_a / fps)
        while ri <= target_ri:               # congela o último frame se acabar
            ok_a, fa = cap_a.read()
            if not ok_a: break
            a_frame = fa; ri += 1
        if a_frame is None:
            a_frame = np.zeros((ah, aw, 3), np.uint8)

        hsv = cv2.cvtColor(tf, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LG, UG)
        if cv2.countNonZero(mask) > 5000:
            nlab, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
            big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            mask = np.where(lab == big, 255, 0).astype(np.uint8)
            mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
            # despill: qualquer verde residual na borda vira cinza escuro neutro
            tff = tf.astype(np.float32)
            gex = np.clip(tff[:, :, 1] - np.maximum(tff[:, :, 0], tff[:, :, 2]), 0, None)
            tff[:, :, 1] -= gex * 0.9
            tf = np.clip(tff, 0, 255).astype(np.uint8)

            rect = cv2.minAreaRect(cv2.findNonZero(mask))
            (cx, cy), (rw, rh), ang = rect
            if rw > rh:                       # normaliza p/ retrato
                rw, rh = rh, rw; ang -= 90.0
            box = cv2.boxPoints(((cx, cy), (rw, rh), ang)).astype(np.float32)
            s = box.sum(1); d = np.diff(box, axis=1).ravel()
            quad = np.array([box[np.argmin(s)], box[np.argmin(d)],
                             box[np.argmax(s)], box[np.argmax(d)]], np.float32)

            scale = aw / rw                   # encaixa pela largura, centra vertical
            pad_v = max(0.0, (rh * scale - ah) / 2.0)
            src_quad = np.array([[0, -pad_v], [aw - 1, -pad_v],
                                 [aw - 1, ah - 1 + pad_v], [0, ah - 1 + pad_v]],
                                np.float32)
            Mq = cv2.getPerspectiveTransform(src_quad, quad)
            content = cv2.warpPerspective(a_frame, Mq, (W, H),
                                          flags=cv2.INTER_LINEAR,
                                          borderMode=cv2.BORDER_CONSTANT)
            mf = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (3, 3), 0.8)
            tf = (content.astype(np.float32) * mf[..., None]
                  + tf.astype(np.float32) * (1.0 - mf[..., None])).astype(np.uint8)

        roi = tf[LOGO_Y:LOGO_Y+LOGO_SIZE, LOGO_X:LOGO_X+LOGO_SIZE].astype(np.float32)
        tf[LOGO_Y:LOGO_Y+LOGO_SIZE, LOGO_X:LOGO_X+LOGO_SIZE] = np.clip(
            lg_bgr * lg_a3 + roi * (1.0 - lg_a3), 0, 255).astype(np.uint8)

        pipe.stdin.write(tf.tobytes())
        if (fi + 1) % 300 == 0:
            print(f"  {fi+1}/{n_t}", flush=True)

    cap_t.release(); cap_a.release()
    pipe.stdin.close(); pipe.wait()

    # ── áudio: narração em primeiro plano + trilha do template c/ ducking ──
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", tmp_v, "-i", NARR, "-i", TPL,
        "-filter_complex",
        "[1:a]aformat=sample_rates=44100,asplit=2[voice][vsc];"
        f"[2:a]atrim=0:{dur},asetpts=PTS-STARTPTS[m0];"
        "[m0][vsc]sidechaincompress=threshold=0.06:ratio=3.5:attack=180:"
        "release=900:makeup=1.4[mduck];"
        "[voice][mduck]amix=inputs=2:weights=1 0.62:normalize=0,"
        "alimiter=limit=0.95,aresample=44100[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
        "-movflags", "+faststart", "-t", str(dur), OUT
    ], check=True)
    os.remove(tmp_v)
    print(f"OK -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
