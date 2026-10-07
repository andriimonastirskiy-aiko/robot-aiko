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
C_BG       = (0,   0,   120)   # яскраво-червоний фон (BGR)
C_GLOW     = (30,  30,  255)   # червоний glow яскравий (BGR)
C_GLOW_DIM = (20,  20,  160)   # червоний glow dim (BGR)
C_SCLERA   = (255, 255, 255)
C_IRIS     = (255, 140, 30 )
C_PUPIL    = (0,   0,   0  )
C_SHINE    = (255, 255, 255)
C_WHITE    = (255, 255, 255)
C_TOOTH    = (240, 240, 240)

# ── Геометрія ─────────────────────────────────────────────────────────────────
BASE_EL_X = 118
BASE_ER_X = 362
BASE_EY   = 148
EW = 60
EH = 68
ER = 26

# Рот — ТІ САМІ координати що і в SAD для плавного морфінгу
MX = W // 2   # 240
MY = 272
MW = 90

LID_FRAC_ANGRY = 0.50   # 50% висоти ока
LID_SKEW_PX    = 16     # скос: ANGRY — внутрішній край нижче (протилежно до SAD)

# ── Утиліти ───────────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def lerp(a, b, t):    return a + (b - a) * t
def ease_inout(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ── Glow — 2 шари [12, 8] (глобальний стандарт AIKO) ─────────────────────────
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

# ── Повіка ANGRY — скос протилежний до SAD ────────────────────────────────────
# SAD:   зовнішній край нижче → ╭────╮ (сумно)
# ANGRY: внутрішній край нижче → ────╮╭──── (злісно)
def draw_lid_angry(draw, cx, cy, hw, hh, lid_frac, sway_px,
                   bg_color, glow_color, mirror=False):
    if lid_frac <= 0.0:
        return

    lid_px = int(hh * lid_frac)
    top_y  = cy - hh
    bot_y  = cy - hh + lid_px
    rr     = ER

    # Верхня дуга (ідентична SAD)
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

    # Низ зі скосом — ANGRY: внутрішній край нижче (протилежно до SAD)
    # Ліве oko (mirror=False): правий (внутрішній) нижче, лівий (зовнішній) вище
    # Праве oko (mirror=True):  лівий  (внутрішній) нижче, правий (зовнішній) вище
    if not mirror:
        left_y  = int(bot_y + sway_px)                  # зовнішній — вище
        right_y = int(bot_y + LID_SKEW_PX + sway_px)    # внутрішній — нижче
    else:
        left_y  = int(bot_y + LID_SKEW_PX + sway_px)    # внутрішній — нижче
        right_y = int(bot_y + sway_px)                   # зовнішній — вище

    poly = arc_pts + [
        (cx + hw, right_y),
        (cx - hw, left_y),
    ]

    draw.polygon(poly, fill=bg_color)

    # Лінія-контур скосу
    draw.line(
        [(cx - hw + 4, left_y),
         (cx + hw - 4, right_y)],
        fill=glow_color, width=3
    )

# ── Одне oko ──────────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             lid_frac=0.0, sway_px=0,
             gaze_x=0.0, gaze_y=0.0,
             glow_color=C_GLOW_DIM, bg_color=C_BG,
             mirror=False):

    draw_glow(draw, cx, cy, hw, hh, ER, glow_color)

    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, fill=C_SCLERA
    )

    # Зіниця — трохи вниз + до центру (пильний злісний погляд)
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

    # Повіка ANGRY
    if lid_frac > 0.01:
        draw_lid_angry(draw, cx, cy, hw, hh,
                       lid_frac=lid_frac,
                       sway_px=sway_px,
                       bg_color=bg_color,
                       glow_color=glow_color,
                       mirror=mirror)

    # Контур
    gc_outline = tuple(min(255, c + 40) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, outline=gc_outline, width=3
    )

# ── Рот ANGRY — прямокутник з 6 зубами (завжди відкритий) ────────────────────
def draw_mouth_angry(draw, morph=1.0):
    alpha  = clamp(morph, 0.0, 1.0)
    m_w    = int(MW * alpha)          # ширина рота
    m_h    = int(32 * alpha)          # висота рота
    m_r    = 8                        # радіус заокруглення

    if m_w < 8 or m_h < 8:
        return

    x0 = MX - m_w
    y0 = MY - m_h // 2
    x1 = MX + m_w
    y1 = MY + m_h // 2

    # Тіло рота — темно-червоний (порожнина) (BGR)
    mouth_fill = (0, 0, 60)
    draw.rounded_rectangle((x0, y0, x1, y1),
                            radius=m_r,
                            fill=mouth_fill,
                            outline=C_GLOW_DIM,
                            width=3)

    # 6 зубів — рівномірно розподілені
    n_teeth  = 6
    tooth_w  = int((m_w * 2 - 16) / n_teeth) - 2
    tooth_h  = max(4, int(m_h * 0.55))
    tooth_r  = 3
    gap      = 2

    total_w  = n_teeth * tooth_w + (n_teeth - 1) * gap
    start_x  = MX - total_w // 2

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
           mouth_morph=1.0, bg=C_BG):
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Ліве oko — gaze до центру (gaze_x > 0 = вправо)
    draw_eye(draw, BASE_EL_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=0.15, gaze_y=0.20,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=False)

    # Праве oko — gaze до центру (gaze_x < 0 = вліво)
    draw_eye(draw, BASE_ER_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=-0.15, gaze_y=0.20,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=True)

    draw_mouth_angry(draw, morph=mouth_morph)

    device.display(img)

# ── Моргання (рот залишається відкритим) ─────────────────────────────────────
def _blink(sway_px=0):
    steps = 7
    for i in range(steps):
        t = ease_inout(i / steps)
        render(lid_frac=clamp(LID_FRAC_ANGRY + t * (1.0 - LID_FRAC_ANGRY), 0.0, 1.0),
               sway_px=sway_px)
        time.sleep(0.013)
    render(lid_frac=1.0, sway_px=sway_px)
    time.sleep(0.05)
    for i in range(steps):\
        t = ease_inout(1.0 - i / steps)
        render(lid_frac=clamp(LID_FRAC_ANGRY + t * (1.0 - LID_FRAC_ANGRY), 0.0, 1.0),
               sway_px=sway_px)
        time.sleep(0.013)

# ── Анімація ANGRY ────────────────────────────────────────────────────────────
def anim_angry():
    print("😠 Angry — Ctrl+C для виходу")

    t       = 0.0
    blink_t = time.time() + random.uniform(2.5, 5.0)

    while True:
        t += DT

        # Легке тремтіння повік — злісне напруження
        sway_px = int(1.5 * math.sin(t * 1.8))

        render(lid_frac=LID_FRAC_ANGRY,
               sway_px=sway_px)

        if time.time() >= blink_t:
            _blink(sway_px=sway_px)
            blink_t = time.time() + random.uniform(2.5, 5.0)

        time.sleep(DT)

# ── Старт ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        anim_angry()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
