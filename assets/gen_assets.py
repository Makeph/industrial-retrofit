"""Génère les visuels du repo + le portfolio Malt + la vidéo TikTok verticale.

La vidéo dashboard est pilotée par les VRAIES sorties de ``RetrofitBridge`` (pas du
faux) : on collecte le flux du bridge puis on le rend image par image.

Sorties:
  <repo>/assets/cover.png
  portfolio_malt/images/  00_cover, 10_industrial_retrofit, 11_retrofit, 12_automatisation,
                          13_data_pipeline, 14_oee_supervision, 99_banner
  portfolio_malt/videos/  retrofit_dashboard_tiktok.mp4   (1080x1920, 9:16)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "src"))
from retrofit import LegacyMachine, RetrofitBridge  # noqa: E402

PORT = Path(r"C:\au2\Au2qwen\portfolio_malt")
IMG = PORT / "images"
VID = PORT / "videos"
for p in (HERE, IMG, VID):
    p.mkdir(parents=True, exist_ok=True)

# ---- palette : GitHub-dark + accents industriels ----
BG = (13, 17, 23)
PANEL = (22, 27, 34)
PANEL2 = (33, 38, 45)
BORDER = (48, 54, 61)
WHITE = (230, 237, 243)
GRAY = (139, 148, 158)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
BLUE = (88, 166, 255)
AMBER = (245, 191, 79)
CYAN = (57, 197, 207)

F = "C:/Windows/Fonts/"
def font(n, s): return ImageFont.truetype(F + n, s)
bold = lambda s: font("arialbd.ttf", s)
reg = lambda s: font("arial.ttf", s)
mono = lambda s: font("consola.ttf", s)
monob = lambda s: font("consolab.ttf", s)


def pill(d, x, y, text, fnt, fg, bg=PANEL, pad=16):
    w = d.textlength(text, font=fnt)
    h = fnt.size
    d.rounded_rectangle([x, y, x + w + pad * 2, y + h + pad], radius=(h + pad) // 2,
                        fill=bg, outline=BORDER, width=1)
    d.text((x + pad, y + pad // 2), text, font=fnt, fill=fg)
    return x + w + pad * 2 + 12


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# =====================================================================  IMAGES
CW, CH = 1200, 630


def _base(accent=GREEN):
    img = Image.new("RGB", (CW, CH), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8, CH], fill=accent)
    return img, d


def cover():
    img, d = _base(CYAN)
    # motif "registres -> données" en filigrane
    for i, x in enumerate(range(70, CW, 150)):
        col = lerp(BORDER, CYAN, i / 8)
        d.text((x, 470 + (i % 3) * 30), f"{0x40 + i*7 & 0xff:02X}{i*131 & 0xffff:04X}",
               font=mono(20), fill=col)
    d.text((64, 58), "$ python -m retrofit run", font=mono(26), fill=CYAN)
    d.text((62, 104), "Quant · Data · Automatisation", font=bold(60), fill=WHITE)
    d.text((62, 172), "Rétrofit industriel", font=bold(60), fill=CYAN)
    d.text((64, 262), "De la machine legacy à la donnée temps réel — testé, pas promis.",
           font=reg(28), fill=GRAY)
    px = 64
    for label in ("Python", "Modbus", "OEE", "MQTT", "maintenance prédictive", "pytest"):
        px = pill(d, px, 320, label, mono(22), BLUE)
    d.text((64, 560), "github.com/Makeph   ·   disponible en freelance",
           font=mono(24), fill=GRAY)
    img.save(IMG / "00_cover.png")
    img.save(HERE / "cover.png")
    print("wrote 00_cover.png + repo cover.png")


def card(filename, *, accent, tag, title, tsize, subtitle, stats, pills, footer):
    img, d = _base(accent)
    d.text((64, 58), tag, font=mono(24), fill=accent)
    d.text((62, 104), title, font=bold(tsize), fill=WHITE)
    y = 104 + tsize + 22
    for line in subtitle:
        d.text((64, y), line, font=reg(29), fill=GRAY)
        y += 39
    sx, sy = 64, 352
    for value, vcol, label in stats:
        d.text((sx, sy), value, font=bold(78), fill=vcol)
        vw = d.textlength(value, font=bold(78))
        d.text((sx + vw + 16, sy + 28), label, font=reg(26), fill=GRAY)
        sx += vw + 16 + d.textlength(label, font=reg(26)) + 56
    px = 64
    for label in pills:
        px = pill(d, px, 476, label, mono(22), BLUE)
    d.text((64, 560), footer, font=mono(25), fill=GRAY)
    img.save(IMG / filename)
    print("wrote", filename)


def cards():
    card("10_industrial_retrofit.png", accent=CYAN, tag="$ python -m retrofit run",
         title="industrial-retrofit", tsize=62,
         subtitle=["Registres Modbus bruts → télémétrie propre,",
                   "maintenance prédictive & OEE temps réel."],
         stats=[("8→1", CYAN, "registres → record JSON"), ("9", WHITE, "tests")],
         pills=("Python", "Modbus", "OEE", "anomaly-detection"),
         footer="github.com/Makeph/industrial-retrofit")

    card("11_retrofit.png", accent=AMBER, tag="// rétrofit machine",
         title="Rétrofit industriel", tsize=58,
         subtitle=["Brancher une machine ancienne sans la remplacer :",
                   "capteurs, automate, remontée de données."],
         stats=[("1996", AMBER, "machine → Industrie 4.0"), ("0", GREEN, "automate remplacé")],
         pills=("PLC", "capteurs", "edge gateway", "OPC-UA"),
         footer="instrumenter l'existant, prouver le gain")

    card("12_automatisation.png", accent=GREEN, tag="$ systemctl status",
         title="Automatisation", tsize=64,
         subtitle=["Pipelines, daemons et supervision qui tournent",
                   "seuls — watchdog, alertes, reprise sur incident."],
         stats=[("24/7", GREEN, "sans intervention"), ("1", WHITE, "commande de déploiement")],
         pills=("Python", "asyncio", "systemd", "MQTT"),
         footer="le travail répétitif, fait par la machine")

    card("13_data_pipeline.png", accent=BLUE, tag="$ stream → store → view",
         title="Data pipeline", tsize=64,
         subtitle=["Du signal brut au tableau de bord :",
                   "ingestion, nettoyage, séries temporelles, KPI."],
         stats=[("ms", BLUE, "latence ingestion"), ("100%", WHITE, "records validés")],
         pills=("pandas", "time-series", "InfluxDB", "Grafana"),
         footer="des données fiables, pas juste des chiffres")

    card("14_oee_supervision.png", accent=GREEN, tag="OEE = A × P × Q",
         title="Supervision & OEE", tsize=60,
         subtitle=["Disponibilité × Performance × Qualité,",
                   "calculé en direct sur le poste de production."],
         stats=[("OEE", GREEN, "temps réel"), ("3", WHITE, "KPI décomposés")],
         pills=("OEE", "dashboard", "alertes", "shift report"),
         footer="rendre la performance visible")


def banner():
    BW, BH = 1584, 396
    img = Image.new("RGB", (BW, BH), BG)
    d = ImageDraw.Draw(img)
    # courbe vibration en filigrane bas
    rng = np.random.default_rng(5)
    n = 120
    v = 0.6 + np.cumsum(rng.normal(0.01, 0.06, n)).clip(0)
    lo, hi = v.min(), v.max()
    top, bot = BH * 0.55, BH * 0.95
    pts = [(int(i / (n - 1) * BW), int(bot - (v[i] - lo) / (hi - lo + 1e-9) * (bot - top)))
           for i in range(n)]
    d.polygon(pts + [(BW, BH), (0, BH)], fill=(12, 30, 32))
    d.line(pts, fill=(30, 90, 95), width=3, joint="curve")
    d.rectangle([BW - 8, 0, BW, BH], fill=CYAN)
    tx = 472
    d.text((tx, 64), "$ python -m retrofit run", font=mono(22), fill=CYAN)
    d.text((tx - 2, 100), "Quant · Data · Automatisation", font=bold(46), fill=WHITE)
    d.text((tx - 2, 152), "Rétrofit industriel", font=bold(46), fill=CYAN)
    d.text((tx, 218), "De la machine legacy à la donnée temps réel — testé, pas promis.",
           font=reg(25), fill=GRAY)
    px = tx
    for label in ("Python", "Modbus", "OEE", "maintenance prédictive", "pytest"):
        px = pill(d, px, 270, label, mono(20), BLUE)
    url = "github.com/Makeph"
    d.text((BW - 40 - d.textlength(url, font=mono(22)), 36), url, font=mono(22), fill=GRAY)
    img.save(IMG / "99_banner.png")
    print("wrote 99_banner.png")


# =====================================================================  VIDÉO 9:16
VW, VH = 1080, 1920
FPS = 30
STEPS_PER_FRAME = 6          # accélération temporelle (sim réelle, time-compressed)
N_FRAMES = 384


def collect_stream(total_ticks: int):
    machine = LegacyMachine(seed=5)
    bridge = RetrofitBridge(client=machine, ideal_cycle_s=2.0, vib_alarm=2.4)
    recs = list(bridge.stream(ticks=total_ticks, machine=machine))
    return recs


def ring(d, cx, cy, r, frac, color, width=30):
    bbox = [cx - r, cy - r, cx + r, cy + r]
    d.arc(bbox, 0, 360, fill=PANEL2, width=width)
    if frac > 0:
        d.arc(bbox, -90, -90 + 360 * min(1.0, frac), fill=color, width=width)


def tile(d, x, y, w, h, label, value, unit, vcolor):
    d.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=PANEL, outline=BORDER, width=1)
    d.text((x + 22, y + 18), label, font=mono(26), fill=GRAY)
    d.text((x + 20, y + 52), value, font=bold(60), fill=vcolor)
    vw = d.textlength(value, font=bold(60))
    d.text((x + 24 + vw, y + 86), unit, font=reg(28), fill=GRAY)


def dashboard_video():
    recs = collect_stream(N_FRAMES * STEPS_PER_FRAME)
    # repère l'onset de l'alarme maintenance pour la narration
    onset = next((i for i, r in enumerate(recs) if r["maintenance_alarm"]), None)
    print("maintenance onset at tick", onset, "/", len(recs))

    import imageio.v2 as imageio
    w = imageio.get_writer(VID / "retrofit_dashboard_tiktok.mp4", fps=FPS,
                           codec="libx264", quality=8, macro_block_size=1,
                           ffmpeg_log_level="error")

    intro_end = 36           # phase "machine legacy / registres bruts"
    connect_end = 60         # phase "bridge connecté"
    win = 90                 # fenêtre du graphe vibration
    status_col = {"idle": GRAY, "running": GREEN, "fault": RED}

    f_title = bold(58); f_h = mono(30); f_big = bold(150)
    for f in range(N_FRAMES):
        idx = min(len(recs) - 1, f * STEPS_PER_FRAME)
        rec = recs[idx]
        img = Image.new("RGB", (VW, VH), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 10, VH], fill=CYAN)

        # ---- header ----
        d.text((44, 60), "$ python -m retrofit run", font=mono(28), fill=CYAN)
        d.text((42, 104), "RÉTROFIT", font=f_title, fill=WHITE)
        d.text((360, 118), "CNC-4 · 1996", font=mono(30), fill=GRAY)

        if f < intro_end:
            # phase intro : registres bruts, pas de dashboard
            d.text((44, 230), "Machine legacy — registres Modbus bruts :", font=reg(34), fill=GRAY)
            regs_demo = [0x0001, rec["spindle_rpm"], int(rec["temperature_c"] * 10),
                         int(rec["vibration_mm_s"] * 100), rec["cycle_count"] & 0xffff,
                         0, rec["good_parts"], rec["reject_parts"]]
            y = 320
            for a, val in enumerate(regs_demo):
                blink = GRAY if (f + a) % 6 < 4 else BORDER
                d.text((60, y), f"  HR[{a}] = 0x{val & 0xffff:04X}", font=mono(40), fill=blink)
                y += 64
            d.text((44, VH - 240), "Aucune unité. Aucun contexte.", font=reg(36), fill=RED)
            d.text((44, VH - 190), "Aucune remontée réseau.", font=reg(36), fill=RED)
            w.append_data(np.asarray(img)); continue

        if f < connect_end:
            t = (f - intro_end) / (connect_end - intro_end)
            d.text((44, 260), "bridge", font=bold(70), fill=WHITE)
            d.text((44, 350), "connecté", font=bold(70), fill=lerp(BORDER, GREEN, t))
            # barre de progression
            d.rounded_rectangle([44, 470, 44 + int((VW - 88) * t), 510], radius=20, fill=CYAN)
            d.rounded_rectangle([44, 470, VW - 44, 510], radius=20, outline=BORDER, width=2)
            d.text((44, 560), "décodage · unités SI · anomalie · OEE", font=mono(30), fill=GRAY)
            w.append_data(np.asarray(img)); continue

        # ---- statut ----
        sc = status_col[rec["status"]]
        pill(d, 760, 110, rec["status"].upper(), mono(28), sc,
             bg=lerp(BG, sc, 0.12))

        # ---- 3 tuiles ----
        ty = 210
        tw, th, gap = 320, 150, 20
        tile(d, 44, ty, tw, th, "BROCHE", f"{rec['spindle_rpm']}", "rpm", WHITE)
        tcol = AMBER if rec["temperature_c"] > 55 else WHITE
        tile(d, 44 + (tw + gap), ty, tw, th, "TEMP", f"{rec['temperature_c']:.0f}", "°C", tcol)
        vcol = RED if rec["maintenance_alarm"] else (AMBER if rec["vibration_mm_s"] > 1.8 else CYAN)
        tile(d, 44 + 2 * (tw + gap), ty, tw, th, "VIBRATION",
             f"{rec['vibration_mm_s']:.2f}", "mm/s", vcol)

        # ---- graphe vibration scrollant ----
        gx, gy, gw, gh = 44, 410, VW - 88, 430
        d.rounded_rectangle([gx, gy, gx + gw, gy + gh], radius=16, fill=PANEL,
                            outline=BORDER, width=1)
        d.text((gx + 20, gy + 14), "vibration mm/s — fenêtre glissante", font=mono(26), fill=GRAY)
        seg = recs[max(0, idx - win):idx + 1]
        vmax = 4.0
        pad = 50
        plot_top, plot_bot = gy + 60, gy + gh - 30
        # seuil d'alarme
        ay = plot_bot - (2.4 / vmax) * (plot_bot - plot_top)
        for xx in range(gx + pad, gx + gw - 20, 24):
            d.line([(xx, ay), (xx + 12, ay)], fill=AMBER, width=2)
        d.text((gx + gw - 150, ay - 34), "seuil", font=mono(24), fill=AMBER)
        if len(seg) > 1:
            def px(i): return gx + pad + i / (len(seg) - 1) * (gw - pad - 30)
            def py(val): return plot_bot - min(val, vmax) / vmax * (plot_bot - plot_top)
            raw = [(px(i), py(s["vibration_mm_s"])) for i, s in enumerate(seg)]
            ewm = [(px(i), py(s["vib_ewma"])) for i, s in enumerate(seg)]
            d.line(raw, fill=CYAN, width=3, joint="curve")
            d.line(ewm, fill=WHITE, width=3, joint="curve")
            for i, s in enumerate(seg):
                if s["anomaly"]:
                    x0, y0 = px(i), py(s["vibration_mm_s"])
                    d.ellipse([x0 - 7, y0 - 7, x0 + 7, y0 + 7], fill=RED)

        # bandeau maintenance
        if rec["maintenance_alarm"]:
            d.rounded_rectangle([gx, gy + gh - 70, gx + gw, gy + gh],
                                radius=12, fill=lerp(BG, RED, 0.18))
            blink = RED if (f // 4) % 2 == 0 else AMBER
            d.text((gx + 24, gy + gh - 58),
                   "[!] MAINTENANCE PRÉDICTIVE — usure roulement détectée",
                   font=bold(30), fill=blink)

        # ---- anneau OEE ----
        cx, cy, rr = VW // 2, 1180, 200
        oee = rec["oee"]
        oc = GREEN if oee >= 0.75 else (AMBER if oee >= 0.5 else RED)
        ring(d, cx, cy, rr, oee, oc, width=34)
        otext = f"{oee*100:.0f}%"
        ow = d.textlength(otext, font=f_big)
        d.text((cx - ow / 2, cy - 110), otext, font=f_big, fill=oc)
        d.text((cx - d.textlength("OEE", font=mono(38)) / 2, cy + 50), "OEE", font=mono(38), fill=GRAY)

        # A / P / Q barres
        by = 1430
        for j, (lab, val, col) in enumerate([
                ("Disponibilité", rec["availability"], BLUE),
                ("Performance", rec["performance"], CYAN),
                ("Qualité", rec["quality"], GREEN)]):
            yy = by + j * 70
            d.text((44, yy), lab, font=mono(28), fill=GRAY)
            bx = 400
            d.rounded_rectangle([bx, yy + 4, VW - 44, yy + 34], radius=15, fill=PANEL2)
            d.rounded_rectangle([bx, yy + 4, bx + int((VW - 44 - bx) * val), yy + 34],
                                radius=15, fill=col)
            d.text((VW - 150, yy), f"{val*100:.0f}%", font=monob(28), fill=WHITE)

        # ---- footer ----
        d.text((44, VH - 110), "industrial-retrofit", font=bold(36), fill=WHITE)
        d.text((44, VH - 64), "github.com/Makeph", font=mono(28), fill=GRAY)
        parts_txt = f"{rec['good_parts']} ok / {rec['reject_parts']} rej"
        d.text((VW - 44 - d.textlength(parts_txt, font=mono(28)), VH - 64),
               parts_txt, font=mono(28), fill=GRAY)

        w.append_data(np.asarray(img))
    w.close()
    print("wrote retrofit_dashboard_tiktok.mp4")


if __name__ == "__main__":
    cover()
    cards()
    banner()
    dashboard_video()
    print("DONE")
