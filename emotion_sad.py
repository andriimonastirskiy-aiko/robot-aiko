"""
😢 AIKO — emotion_sad.py
Тестовий файл емоції SAD (нескінченний цикл, Ctrl+C для виходу)
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
C_BG      = (0,   0,   0  )
C_CYAN    = (255, 220, 0  )
C_CYAN_DIM= (130, 120, 0  )
C_SCLERA  = (255, 255, 255)
C_IRIS    = (255, 140, 30 )
C_PUPIL   = (0,   0,   0  )
C_SHINE   = (255, 255, 255)
C_WHITE   = (255, 255, 255)
C_TEAR    = (255, 200, 0  )

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

LID_FRAC_SAD = 0.6    # 60% висоти ока
LID_SKEW_PX  = 16      # скос: зовнішній край нижче внутрішнього

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

# ── Повіка SAD — суцільний polygon (верх по дузі ER, низ зі скосом) ──────────
def draw_lid_sad(draw, cx, cy, hw, hh, lid_frac, sway_px,
                 bg_color, glow_color, mirror=False):
    if lid_frac <= 0.0:
        return

    lid_px = int(hh * lid_frac)
    top_y  = cy - hh
    bot_y  = cy - hh + lid_px
    rr     = ER

    # Верхня дуга — точки по заокругленим кутам (імітує rounded_rectangle зверху)
    arc_pts = []

    # Лівий верхній кут: чверть кола 180°→270°
    for deg in range(180, 271, 5):
        rad = math.radians(deg)
        x = (cx - hw + rr) + rr * math.cos(rad)
        y = (top_y + rr)   + rr * math.sin(rad)
        arc_pts.append((x, y))

    # Правий верхній кут: чверть кола 270°→360°
    for deg in range(270, 361, 5):
        rad = math.radians(deg)
        x = (cx + hw - rr) + rr * math.cos(rad)
        y = (top_y + rr)   + rr * math.sin(rad)
        arc_pts.append((x, y))

    # Низ зі скосом — SAD: зовнішній край нижче, внутрішній вище
    # Ліве oko (mirror=False): лівий (зовнішній) нижче, правий (внутрішній) вище
    # Праве oko (mirror=True):  правий (зовнішній) нижче, лівий (внутрішній) вище
    if not mirror:
        left_y  = int(bot_y + LID_SKEW_PX + sway_px)  # зовнішній — нижче
        right_y = int(bot_y + sway_px)                 # внутрішній — вище
    else:
        left_y  = int(bot_y + sway_px)                 # внутрішній — вище
        right_y = int(bot_y + LID_SKEW_PX + sway_px)  # зовнішній — нижче

    # Суцільний polygon: верхня дуга + право-низ + ліво-низ
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
             glow_color=C_CYAN_DIM, bg_color=C_BG,
             mirror=False):

    draw_glow(draw, cx, cy, hw, hh, ER, glow_color)

    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=ER, fill=C_SCLERA
    )

    # Зіниця
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

    # Повіка SAD
    if lid_frac > 0.01:
        draw_lid_sad(draw, cx, cy, hw, hh,
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

# ── Сльози ────────────────────────────────────────────────────────────────────
def draw_tears(draw, elapsed):
    for base_x, offset in [(BASE_EL_X - 14, 0.0),
                            (BASE_ER_X + 14, 0.55)]:
        drop_y = BASE_EY + EH + int((elapsed * 55 + offset * 90) % 110)
        draw.ellipse((base_x - 7, drop_y - 13,
                      base_x + 7, drop_y + 7), fill=C_TEAR)
        draw.ellipse((base_x - 3, drop_y - 9,
                      base_x + 1, drop_y - 4),
                     fill=(200, 240, 255))

# ── Рот SAD — дуга вниз ───────────────────────────────────────────────────────
def draw_mouth_sad(draw, morph=1.0):
    alpha = clamp(morph, 0.0, 1.0)
    arc_h = int(22 * alpha)
    arc_w = int(MW * alpha)
    if arc_w < 4 or arc_h < 4:
        return
    gc = tuple(max(0, c // 5) for c in C_CYAN_DIM)
    draw.arc((MX - arc_w - 5, MY - arc_h - 5,
              MX + arc_w + 5, MY + arc_h + 5),
             start=190, end=350, fill=gc, width=14)
    draw.arc((MX - arc_w, MY - arc_h,
              MX + arc_w, MY + arc_h),
             start=190, end=350, fill=C_CYAN_DIM, width=10)

# ── Рендер кадру ──────────────────────────────────────────────────────────────
def render(lid_frac=LID_FRAC_SAD, sway_px=0,
           gaze_y=0.32, mouth_morph=1.0,
           tears=False, tears_elapsed=0.0, bg=C_BG):
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Ліве oko — mirror=False: лівий (зовнішній) край нижче = сумний ╭────
    draw_eye(draw, BASE_EL_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_y=gaze_y, bg_color=bg,
             mirror=False)

    # Праве oko — mirror=True: правий (зовнішній) край нижче = сумний ────╮
    draw_eye(draw, BASE_ER_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_y=gaze_y, bg_color=bg,
             mirror=True)

    draw_mouth_sad(draw, morph=mouth_morph)

    if tears:
        draw_tears(draw, tears_elapsed)

    device.display(img)

# ── Моргання ──────────────────────────────────────────────────────────────────
def _blink(sway_px=0, tears_elapsed=0.0):
    steps = 7
    for i in range(steps):
        t = ease_inout(i / steps)
        render(lid_frac=clamp(LID_FRAC_SAD + t * (1.0 - LID_FRAC_SAD), 0.0, 1.0),
               sway_px=sway_px,
               tears=True, tears_elapsed=tears_elapsed)
        time.sleep(0.013)
    render(lid_frac=1.0, sway_px=sway_px,
           tears=True, tears_elapsed=tears_elapsed)
    time.sleep(0.05)
    for i in range(steps):
        t = ease_inout(1.0 - i / steps)
        render(lid_frac=clamp(LID_FRAC_SAD + t * (1.0 - LID_FRAC_SAD), 0.0, 1.0),
               sway_px=sway_px,
               tears=True, tears_elapsed=tears_elapsed)
        time.sleep(0.013)

# ── Анімація SAD ──────────────────────────────────────────────────────────────
def anim_sad():
    print("😢 Sad — Ctrl+C для виходу")

    t       = 0.0
    blink_t = time.time() + random.uniform(3.5, 6.0)

    while True:
        t += DT

        # Легкий sway — повіки злегка коливаються
        sway_px = int(2 * math.sin(t * 0.5))

        render(lid_frac=LID_FRAC_SAD,
               sway_px=sway_px,
               gaze_y=0.32,
               tears=True,
               tears_elapsed=t,
               bg=C_BG)

        if time.time() >= blink_t:
            _blink(sway_px=sway_px, tears_elapsed=t)
            blink_t = time.time() + random.uniform(3.5, 6.0)

        time.sleep(DT)

# ── Старт ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        anim_sad()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
