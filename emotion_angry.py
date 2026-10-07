"""
😠 AIKO — emotion_angry.py
Тестовий файл емоції ANGRY (нескінченний цикл, Ctrl+C для виходу)
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
C_GLOW     = (30,  30,  255)
C_GLOW_DIM = (20,  20,  160)
C_SCLERA   = (255, 255, 255)
C_IRIS     = (255, 140, 30 )
C_PUPIL    = (0,   0,   0  )
C_SHINE    = (255, 255, 255)
C_TOOTH    = (240, 240, 240)

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

LID_FRAC_ANGRY = 0.50
LID_SKEW_PX    = 16

# ── Утиліти ───────────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))

# ── Glow ──────────────────────────────────────────────────────────────────────
def draw_glow(draw, cx, cy, hw, hh, r, color):
    widths  = [12, 8]
    expands = [4,  10]
    brights = [220, 120]
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

# ── Повіка ANGRY ──────────────────────────────────────────────────────────────
def draw_lid_angry(draw, cx, cy, hw, hh, lid_frac, sway_px,
                   bg_color, glow_color, mirror=False):
    if lid_frac <= 0.0:
        return

    lid_px = int(hh * lid_frac)
    top_y  = cy - hh
    bot_y  = cy - hh + lid_px
    rr     = ER

    arc_pts = []
    for deg in range(180, 271, 5):
        rad = math.radians(deg)
        x = (cx - hw + rr) + rr * math.cos(rad)
        y = (top_y + rr)   + rr * math.sin(rad)
        arc_pts.append((x, y))
    for deg in range(270, 361, 5):
        rad = math.radians(deg)
        x = (cx + hw - rr) + rr * math.cos(rad)
        y = (top_y + rr)   + rr * math.sin(rad)
        arc_pts.append((x, y))

    if not mirror:
        left_y  = int(bot_y + sway_px)
        right_y = int(bot_y + LID_SKEW_PX + sway_px)
    else:
        left_y  = int(bot_y + LID_SKEW_PX + sway_px)
        right_y = int(bot_y + sway_px)

    poly = arc_pts + [
        (cx + hw, right_y),
        (cx - hw, left_y),
    ]
    draw.polygon(poly, fill=bg_color)
    draw.line(
        [(cx - hw + 4, left_y), (cx + hw - 4, right_y)],
        fill=glow_color, width=3
    )

# ── Одне oko ──────────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             lid_frac=0.0, sway_px=0,
             gaze_x=0.0, gaze_y=0.0,
             snap_px=0,
             glow_color=C_GLOW_DIM, bg_color=(0, 0, 120),
             mirror=False):

    draw_glow(draw, cx, cy, hw, hh, ER, glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, fill=C_SCLERA
    )

    iris_hw = int(hw * 0.50)
    iris_hh = int(hh * 0.50)
    max_gx  = max(1, hw - iris_hw - 4)
    max_gy  = max(1, hh - iris_hh - 4)

    off_x = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
    off_y = int(clamp(gaze_y * max_gy, -max_gy, max_gy))

    # snap_px: ліве око рухається вправо (до центру), праве — вліво
    if not mirror:
        off_x += snap_px
    else:
        off_x -= snap_px

    off_x = int(clamp(off_x, -max_gx, max_gx))

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
        draw_lid_angry(draw, cx, cy, hw, hh,
                       lid_frac=lid_frac,
                       sway_px=sway_px,
                       bg_color=bg_color,
                       glow_color=glow_color,
                       mirror=mirror)

    gc_outline = tuple(min(255, c + 40) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, outline=gc_outline, width=3
    )

# ── Рот ANGRY ─────────────────────────────────────────────────────────────────
def draw_mouth_angry(draw, morph=1.0):
    alpha = clamp(morph, 0.0, 1.0)
    m_w   = int(MW * alpha)
    m_h   = int(32 * alpha)
    m_r   = 8

    if m_w < 8 or m_h < 8:
        return

    x0 = MX - m_w
    y0 = MY - m_h // 2
    x1 = MX + m_w
    y1 = MY + m_h // 2

    draw.rounded_rectangle((x0, y0, x1, y1),
                            radius=m_r,
                            fill=(0, 0, 60),
                            outline=C_GLOW_DIM,
                            width=3)

    n_teeth = 6
    tooth_w = int((m_w * 2 - 16) / n_teeth) - 2
    tooth_h = max(4, int(m_h * 0.55))
    tooth_r = 3
    gap     = 2
    total_w = n_teeth * tooth_w + (n_teeth - 1) * gap
    start_x = MX - total_w // 2

    for i in range(n_teeth):
        tx0 = start_x + i * (tooth_w + gap)
        tx1 = tx0 + tooth_w
        ty0 = y0 + 3
        ty1 = ty0 + tooth_h
        draw.rounded_rectangle((tx0, ty0, tx1, ty1),
                                radius=tooth_r,
                                fill=C_TOOTH)

# ── Рендер кадру ──────────────────────────────────────────────────────────────
def render(lid_frac=LID_FRAC_ANGRY, sway_px=0,
           mouth_morph=1.0, bg=(0, 0, 120),
           snap_px=0):
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    draw_eye(draw, BASE_EL_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=0.15, gaze_y=0.20,
             snap_px=snap_px,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=False)

    draw_eye(draw, BASE_ER_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=-0.15, gaze_y=0.20,
             snap_px=snap_px,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=True)

    draw_mouth_angry(draw, morph=mouth_morph)
    device.display(img)

# ── Анімація ANGRY ────────────────────────────────────────────────────────────
def anim_angry():
    print("😠 Angry — Ctrl+C для виходу")

    t = 0.0

    # Машина станів ривку:
    # IDLE      → чекаємо next_jerk_t
    # JERK1     → snap_px = 10, чекаємо 0.5с
    # JERK2     → snap_px = 20, чекаємо 0.5с
    # HOLD      → snap_px = 20, чекаємо 0.5с
    # RETURN    → snap_px = 0,  чекаємо 0.5с → IDLE
    STATE_IDLE   = 0
    STATE_JERK1  = 1
    STATE_JERK2  = 2
    STATE_HOLD   = 3
    STATE_RETURN = 4

    state      = STATE_IDLE
    snap_px    = 0
    next_t     = time.time() + random.uniform(1.5, 3.0)

    while True:
        now = time.time()
        t  += DT

        # Пульсуючий червоний фон
        bg_val = int(80 + 50 * (0.5 + 0.5 * math.sin(t * 2.5)))
        bg = (0, 0, bg_val)

        # Легке тремтіння повік
        sway_px = int(1.5 * math.sin(t * 1.8))

        # Машина станів
        if state == STATE_IDLE:
            snap_px = 0
            if now >= next_t:
                snap_px = 10
                state   = STATE_JERK1
                next_t  = now + 0.5

        elif state == STATE_JERK1:
            snap_px = 10
            if now >= next_t:
                snap_px = 20
                state   = STATE_JERK2
                next_t  = now + 0.5

        elif state == STATE_JERK2:
            snap_px = 20
            if now >= next_t:
                state  = STATE_HOLD
                next_t = now + 0.5

        elif state == STATE_HOLD:
            snap_px = 20
            if now >= next_t:
                snap_px = 0
                state   = STATE_RETURN
                next_t  = now + 0.5

        elif state == STATE_RETURN:
            snap_px = 0
            if now >= next_t:
                state  = STATE_IDLE
                next_t = now + random.uniform(1.5, 3.5)

        render(lid_frac=LID_FRAC_ANGRY,
               sway_px=sway_px,
               bg=bg,
               snap_px=snap_px)

        time.sleep(DT)

# ── Старт ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        anim_angry()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
