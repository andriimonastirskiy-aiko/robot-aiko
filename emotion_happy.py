"""
😊 AIKO — emotion_happy.py
Тестовий файл емоції HAPPY (нескінченний цикл, Ctrl+C для виходу)
"""

from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw
import time, math, random

# ── Дисплей ───────────────────────────────────────────────────────────────────
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=32000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)

W, H = 480, 320
FPS  = 30
DT   = 1.0 / FPS

# ── Кольори ───────────────────────────────────────────────────────────────────
C_BG     = (0,   0,   0  )
C_CYAN   = (255, 220, 0  )   # PIL→екран bgr: cyan
C_SCLERA = (255, 255, 255)
C_IRIS   = (255, 140, 30 )   # PIL→екран bgr: синій
C_PUPIL  = (0,   0,   0  )
C_SHINE  = (255, 255, 255)
C_WHITE  = (255, 255, 255)

# ── Геометрія ─────────────────────────────────────────────────────────────────
BASE_EL_X = 118
BASE_ER_X = 362
BASE_EY   = 148
EW = 60
EH = 68
ER = 26

MX = W // 2
MY = 272
MW = 90

# ── Утиліти ───────────────────────────────────────────────────────────────────
def lerp(a, b, t):    return a + (b - a) * t
def clamp(v, lo, hi): return max(lo, min(hi, v))
def ease_inout(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ── Glow — 2 чіткі товсті шари ───────────────────────────────────────────────
def draw_glow(draw, cx, cy, hw, hh, r, color):
    widths  = [12, 8]     # внутрішній товщий, зовнішній тонший
    expands = [4, 10]     # внутрішній ближче, зовнішній далі
    brights = [220, 120]  # внутрішній яскравіший, зовнішній тьмяніший
    for i in range(2):
        expand = expands[i]
        bright = brights[i]
        gc     = tuple(min(255, int(c * bright / 255)) for c in color)
        draw.rounded_rectangle(
            (cx - hw - expand, cy - hh - expand,
             cx + hw + expand, cy + hh + expand),
            radius=min(r + expand // 2, hw + expand),
            outline=gc,
            width=widths[i]
        )

# ── Повіка (пряма, зверху радіус, знизу прямо) ───────────────────────────────
def draw_lid_straight(draw, cx, cy, hw, hh, lid_frac, bg_color,
                      glow_color=C_CYAN, show_line=False):
    if lid_frac <= 0.0:
        return
    lid_px = int(hh * lid_frac)
    top_y  = cy - hh
    bot_y  = cy - hh + lid_px
    rr     = ER
    draw.rounded_rectangle(
        (cx - hw, top_y - 2, cx + hw, bot_y + rr),
        radius=rr, fill=bg_color
    )
    draw.rectangle(
        (cx - hw, bot_y, cx + hw, bot_y + rr + 1),
        fill=bg_color
    )
    if show_line:
        draw.line(
            [(cx - hw + 8, bot_y), (cx + hw - 8, bot_y)],
            fill=glow_color, width=4
        )

# ── Одне oko ──────────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             lid_frac=0.0, gaze_x=0.0, gaze_y=0.0,
             glow_color=C_CYAN, bg_color=C_BG,
             show_line=False):

    draw_glow(draw, cx, cy, hw, hh, ER, glow_color)

    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, fill=C_SCLERA
    )

    if lid_frac < 0.95:
        iris_hw = int(hw * 0.50)
        iris_hh = int(hh * 0.50)
        max_gx  = max(1, hw - iris_hw - 4)
        max_gy  = max(1, hh - iris_hh - 4)
        off_x   = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
        off_y   = int(clamp(gaze_y * max_gy, -max_gy, max_gy))
        icx, icy = cx + off_x, cy + off_y

        dark = tuple(max(0, c - 60) for c in C_IRIS)
        draw.ellipse((icx - iris_hw, icy - iris_hh,
                      icx + iris_hw, icy + iris_hh), fill=dark)
        in_hw = int(iris_hw * 0.68)
        in_hh = int(iris_hh * 0.68)
        draw.ellipse((icx - in_hw, icy - in_hh,
                      icx + in_hw, icy + in_hh), fill=C_IRIS)
        p_hw = int(iris_hw * 0.46)
        p_hh = int(iris_hh * 0.46)
        draw.ellipse((icx - p_hw, icy - p_hh,
                      icx + p_hw, icy + p_hh), fill=C_PUPIL)
        sh_x = icx - int(iris_hw * 0.30)
        sh_y = icy - int(iris_hh * 0.30)
        sh_r = max(3, int(iris_hw * 0.17))
        draw.ellipse((sh_x - sh_r, sh_y - sh_r,
                      sh_x + sh_r, sh_y + sh_r), fill=C_SHINE)
        sh2_r = max(2, sh_r // 2)
        draw.ellipse((sh_x + sh_r, sh_y - sh2_r,
                      sh_x + sh_r + sh2_r * 2, sh_y + sh2_r),
                     fill=(200, 230, 255))

    if lid_frac > 0.01:
        draw_lid_straight(draw, cx, cy, hw, hh, lid_frac,
                          bg_color=bg_color,
                          glow_color=glow_color,
                          show_line=show_line)

    gc_outline = tuple(min(255, c + 40) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, outline=gc_outline, width=3
    )

# ── Рот happy ─────────────────────────────────────────────────────────────────
def draw_mouth_happy(draw, morph=1.0):
    alpha = clamp(morph, 0.0, 1.0)
    arc_h = int(26 * alpha)
    arc_w = int(MW * alpha)
    if arc_w < 4 or arc_h < 4:
        return
    gc = tuple(max(0, c // 5) for c in C_CYAN)
    draw.arc((MX - arc_w - 5, MY - arc_h - 5,
              MX + arc_w + 5, MY + arc_h + 5),
             start=10, end=170, fill=gc, width=14)
    draw.arc((MX - arc_w, MY - arc_h,
              MX + arc_w, MY + arc_h),
             start=10, end=170, fill=C_WHITE, width=10)

# ── Рендер кадру ──────────────────────────────────────────────────────────────
def render(hw=EW, hh=EH, lid_frac=0.0, gaze_x=0.0, gaze_y=0.0,
           mouth_morph=1.0, show_line=False, bg=C_BG):
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    draw_eye(draw, BASE_EL_X, BASE_EY, hw, hh,
             lid_frac=lid_frac, gaze_x=gaze_x, gaze_y=gaze_y,
             bg_color=bg, show_line=show_line)
    draw_eye(draw, BASE_ER_X, BASE_EY, hw, hh,
             lid_frac=lid_frac, gaze_x=gaze_x, gaze_y=gaze_y,
             bg_color=bg, show_line=show_line)
    draw_mouth_happy(draw, morph=mouth_morph)
    device.display(img)

# ── Моргання — повне 100% закриття ───────────────────────────────────────────
def do_blink():
    steps = 7
    for i in range(steps):
        t = ease_inout(i / steps)
        render(lid_frac=t)          # 0.0 → 1.0 (повне закриття)
        time.sleep(0.013)
    render(lid_frac=1.0, show_line=True)   # повністю закрито
    time.sleep(0.05)
    for i in range(steps):
        t = ease_inout(1.0 - i / steps)
        render(lid_frac=t)          # 1.0 → 0.0 (відкриття)
        time.sleep(0.013)

# ── Анімація Happy ────────────────────────────────────────────────────────────
def anim_happy():
    print("😊 Happy — Ctrl+C для виходу")
    t       = 0.0
    blink_t = time.time() + random.uniform(2.5, 4.5)
    gx = gy = tgx = tgy = 0.0
    gaze_t  = time.time() + random.uniform(1.5, 3.0)

    while True:
        t += DT
        breathe = 0.008 * math.sin(t * 1.5)
        hw = int(EW * (1 + breathe))
        hh = int(EH * (1 + breathe))

        gx = lerp(gx, tgx, 0.07)
        gy = lerp(gy, tgy, 0.07)
        if time.time() >= gaze_t:
            tgx    = random.uniform(-0.45, 0.45)
            tgy    = random.uniform(-0.20, 0.20)
            gaze_t = time.time() + random.uniform(1.5, 3.0)

        render(hw=hw, hh=hh, gaze_x=gx, gaze_y=gy, mouth_morph=1.0)

        if time.time() >= blink_t:
            do_blink()
            blink_t = time.time() + random.uniform(2.5, 4.5)

        time.sleep(DT)

# ── Старт ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        anim_happy()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
