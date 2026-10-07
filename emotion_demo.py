"""
🎭 AIKO — emotion_demo.py
Демо: плавний перехід між HAPPY → ANGRY → SAD (нескінченний цикл)
"""

from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw, ImageFont
import time, math, random

# ── Дисплей ───────────────────────────────────────────────────────────────────
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=32000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)

W, H = 480, 320
FPS  = 15
DT   = 1.0 / FPS

# ── Утиліти ───────────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def lerp(a, b, t):    return a + (b - a) * clamp(t, 0.0, 1.0)
def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def cubic_ease(t):
    t = clamp(t, 0.0, 1.0)
    if t < 0.5: return 4*t*t*t
    p = 2*t - 2
    return 0.5*p*p*p + 1.0

# ── Параметри емоцій (BGR!) ───────────────────────────────────────────────────
EMOTIONS = {
    "happy": {
        "bg":         (20, 40, 20),
        "glow":       (20, 140, 20),
        "iris":       (30, 200, 255),
        "mouth":      "smile",
        "blink_rate": 3.5,
    },
    "angry": {
        "bg":         (10, 20, 120),
        "glow":       (20, 20, 160),
        "iris":       (30, 140, 255),
        "mouth":      "angry",
        "blink_rate": 8.0,
    },
    "sad": {
        "bg":         (60, 30, 10),
        "glow":       (160, 80, 20),
        "iris":       (200, 120, 60),
        "mouth":      "sad",
        "blink_rate": 5.0,
    },
}

EMOTION_ORDER = ["happy", "angry", "sad"]
HOLD_TIME  = 5.0
TRANS_TIME = 1.5

ER = 26
EW, EH = 60, 68
BASE_EL_X, BASE_ER_X, BASE_EY = 118, 362, 148
MX, MY = W // 2, 272

# ── Малювання ока ─────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             gaze_x, gaze_y,
             iris_color, glow_color, bg_color,
             blink=False):

    eye_hh = max(2, int(hh * 0.08)) if blink else hh
    radius = 6 if blink else ER

    draw.rounded_rectangle(
        (cx - hw, cy - eye_hh, cx + hw, cy + eye_hh),
        radius=radius, fill=(255, 255, 255)
    )

    if not blink:
        iris_hw = int(hw * 0.50)
        iris_hh = int(hh * 0.50)
        max_gx  = max(1, hw - iris_hw - 4)
        max_gy  = max(1, hh - iris_hh - 4)
        off_x   = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
        off_y   = int(clamp(gaze_y * max_gy, -max_gy, max_gy))
        icx, icy = cx + off_x, cy + off_y

        dark = tuple(max(0, c - 60) for c in iris_color)
        draw.ellipse((icx-iris_hw, icy-iris_hh,
                      icx+iris_hw, icy+iris_hh), fill=dark)
        in_hw = int(iris_hw * 0.68)
        in_hh = int(iris_hh * 0.68)
        draw.ellipse((icx-in_hw, icy-in_hh,
                      icx+in_hw, icy+in_hh), fill=iris_color)
        p_hw = int(iris_hw * 0.46)
        p_hh = int(iris_hh * 0.46)
        draw.ellipse((icx-p_hw, icy-p_hh,
                      icx+p_hw, icy+p_hh), fill=(0, 0, 0))
        sh_x = icx - int(iris_hw * 0.30)
        sh_y = icy - int(iris_hh * 0.30)
        sh_r = max(3, int(iris_hw * 0.17))
        draw.ellipse((sh_x-sh_r, sh_y-sh_r,
                      sh_x+sh_r, sh_y+sh_r), fill=(255, 255, 255))

    outline_c = tuple(min(255, c + 40) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - eye_hh, cx + hw, cy + eye_hh),
        radius=radius, outline=outline_c, width=3
    )

# ── Малювання рота ────────────────────────────────────────────────────────────
def draw_mouth(draw, mouth_type, glow_color):
    mw = 90

    if mouth_type == "smile":
        draw.arc([MX-mw, MY-30, MX+mw, MY+30],
                 start=10, end=170, fill=glow_color, width=5)

    elif mouth_type == "angry":
        x0, x1 = MX-mw, MX+mw
        y0, y1 = MY-16, MY+16
        draw.rounded_rectangle((x0, y0, x1, y1), radius=8,
                                fill=(0, 0, 60),
                                outline=glow_color, width=3)
        n_teeth = 6
        tw = int((mw*2 - 16) / n_teeth) - 2
        th = max(4, int(32 * 0.55))
        total_w = n_teeth*tw + (n_teeth-1)*2
        sx = MX - total_w // 2
        for i in range(n_teeth):
            tx0 = sx + i*(tw+2)
            draw.rounded_rectangle((tx0, y0+3, tx0+tw, y0+3+th),
                                   radius=3, fill=(240, 240, 240))

    elif mouth_type == "sad":
        draw.arc([MX-mw, MY-20, MX+mw, MY+40],
                 start=190, end=350, fill=glow_color, width=5)
        tear_y = int((time.time() * 25) % 80)
        draw.ellipse((108, 200+tear_y,     118, 214+tear_y),
                     fill=(200, 180, 80))
        draw.ellipse((362, 200+tear_y+20,  372, 214+tear_y+20),
                     fill=(200, 180, 80))

# ── Морфований рот (зникає → з'являється) ─────────────────────────────────────
def draw_mouth_morphed(draw, from_type, to_type, t, glow_color):
    if t < 0.5:
        alpha = 1.0 - t * 2
        c = tuple(int(v * alpha) for v in glow_color)
        draw_mouth(draw, from_type, c)
    else:
        alpha = (t - 0.5) * 2
        c = tuple(int(v * alpha) for v in glow_color)
        draw_mouth(draw, to_type, c)

# ── Рендер кадру ─────────────────────────────────────────────────────────────
def render_frame(bg, glow, iris, mouth_type,
                 gaze_x=0.0, gaze_y=0.15,
                 blink=False,
                 from_mouth=None, morph_t=1.0):

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    draw_eye(draw, BASE_EL_X, BASE_EY, EW, EH,
             gaze_x,  gaze_y, iris, glow, bg, blink=blink)
    draw_eye(draw, BASE_ER_X, BASE_EY, EW, EH,
             -gaze_x, gaze_y, iris, glow, bg, blink=blink)

    if from_mouth and morph_t < 1.0:
        draw_mouth_morphed(draw, from_mouth, mouth_type, morph_t, glow)
    else:
        draw_mouth(draw, mouth_type, glow)

    device.display(img)

# ── Головний цикл ─────────────────────────────────────────────────────────────
def run():
    print("🎭 AIKO emotion_demo — Ctrl+C для виходу")
    idx         = 0
    gaze_x      = 0.0
    gaze_timer  = time.time() + random.uniform(2.0, 4.0)
    blink_timer = time.time() + random.uniform(2.0, 4.0)

    while True:
        name_a = EMOTION_ORDER[idx]
        name_b = EMOTION_ORDER[(idx + 1) % len(EMOTION_ORDER)]
        ea     = EMOTIONS[name_a]
        eb     = EMOTIONS[name_b]

        print(f"▶ {name_a.upper()} ({HOLD_TIME}s)...")

        # ── HOLD ──────────────────────────────────────────────────────────────
        t_hold = time.time()
        while time.time() - t_hold < HOLD_TIME:
            now = time.time()

            if now >= gaze_timer:
                gaze_x     = random.choice([-1, 0, 1]) * random.uniform(0.3, 0.8)
                gaze_timer = now + random.uniform(2.0, 5.0)

            do_blink = False
            if now >= blink_timer:
                do_blink    = True
                blink_timer = now + ea["blink_rate"] + random.uniform(-0.5, 1.0)

            render_frame(ea["bg"], ea["glow"], ea["iris"], ea["mouth"],
                         gaze_x=gaze_x, blink=do_blink)
            time.sleep(DT)

        # ── ПЕРЕХІД ───────────────────────────────────────────────────────────
        print(f"⟶ {name_a} → {name_b}...")
        steps = int(TRANS_TIME * FPS)

        for i in range(steps):
            t = cubic_ease(i / steps)
            render_frame(
                bg         = lerp_color(ea["bg"],   eb["bg"],   t),
                glow       = lerp_color(ea["glow"], eb["glow"], t),
                iris       = lerp_color(ea["iris"], eb["iris"], t),
                mouth_type = eb["mouth"],
                from_mouth = ea["mouth"],
                morph_t    = t,
                gaze_x     = gaze_x * (1.0 - t),
                gaze_y     = 0.15,
            )
            time.sleep(DT)

        idx = (idx + 1) % len(EMOTION_ORDER)
        blink_timer = time.time() + random.uniform(1.0, 2.5)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
