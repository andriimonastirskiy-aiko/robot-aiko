"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AIKO eyes_v2.py — процедурна анімація очей                       ║
║           Стиль: neon cyan glow, чорний фон, мультяшний                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  РЕФЕРЕНС ДИЗАЙНУ (з PNG фото смайликів):                                  ║
║  Детальний опис → EYES_REFERENCE.md                                        ║
║                                                                              ║
║  ФОРМА ОКА: rounded rectangle (НЕ еліпс!), radius~32px                     ║
║  GLOW: cyan (0,220,255) по контуру, angry = помаранч (255,80,0)            ║
║                                                                              ║
║  ⚠️  bgr=True на ILI9488: RGB в PIL = BGR на екрані!                       ║
║      Червоний фон → PIL (0,0,55), cyan glow → PIL (255,220,0) ← ні,       ║
║      cyan = (0,220,255) бо G і B не міняються місцями попарно,             ║
║      міняється лише канал R↔B: (R,G,B)→(B,G,R) на екрані.                ║
║      Тобто PIL (0,0,55) → екран (55,0,0) = темно-червоний ✓               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw
import time
import math
import random

# ── Дисплей ───────────────────────────────────────────────────────────────────
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=32000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)

W, H = 480, 320
FPS  = 30
DT   = 1.0 / FPS

# ── Кольори (PIL RGB, але дисплей bgr=True → R↔B міняються) ─────────────────
# Правило: якщо хочеш на екрані (R,G,B) → пиши в PIL (B,G,R)
C_BG           = (0,   0,   0)       # чорний — однаковий
C_CYAN         = (255, 220, 0)       # PIL→екран: cyan (0,220,255) ✓
C_CYAN_DIM     = (180, 140, 0)       # тьмяний cyan для sad
C_GLOW_ANGRY   = (0,   80,  255)     # PIL→екран: помаранчевий (255,80,0) ✓
C_WHITE        = (255, 255, 255)     # білий — однаковий
C_SCLERA       = (255, 255, 255)     # білок нормальний
C_SCLERA_ANGRY = (200, 200, 255)     # PIL→екран: рожевий (255,200,200) ✓
C_IRIS         = (255, 140, 30)      # PIL→екран: синя райдужка (30,140,255) ✓
C_PUPIL        = (0,   0,   0)       # чорна зіниця
C_SHINE        = (255, 255, 255)     # відблиск білий
C_TEAR         = (255, 200, 0)       # PIL→екран: cyan сльоза (0,200,255) ✓
C_BG_ANGRY     = (55,  0,   0)       # PIL→екран: темно-червоний (0,0,55)→(55,0,0) ✓

# ── Геометрія очей ────────────────────────────────────────────────────────────
# Центри очей — розсунуті далі, щоб не перекривались
EL_X, ER_X = 118, 362   # X лівого і правого (відстань 244px)
EY          = 148        # Y центр

# Розмір rounded rect ока (МЕНШИЙ ніж раніше)
EW = 75    # напів-ширина  (було 100)
EH = 85    # напів-висота  (було 110)
ER = 32    # радіус заокруглення (було 44)

# Перевірка: ліве oko займає 118-75=43 до 118+75=193
#            праве oko займає 362-75=287 до 362+75=437
#            між очима вільно: 287-193 = 94px ✓

# Рот
MX = W // 2  # 240
MY = 272
MW = 60

# Брови (surprised) — висота над оком
BROW_H = 18

# ─────────────────────────────────────────────────────────────────────────────
# ДОПОМІЖНІ ФУНКЦІЇ
# ─────────────────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def ease_inout(t):
    return t * t * (3 - 2 * t)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def swap_rb(color):
    """Міняє R↔B у кольорі (для bgr=True дисплея)"""
    return (color[2], color[1], color[0])

# ── Малювання rounded rectangle ───────────────────────────────────────────────
def draw_rrect(draw, cx, cy, hw, hh, r, fill=None, outline=None, width=3):
    x0, y0 = cx - hw, cy - hh
    x1, y1 = cx + hw, cy + hh
    draw.rounded_rectangle((x0, y0, x1, y1), radius=r,
                            fill=fill, outline=outline, width=width)

def draw_glow(draw, cx, cy, hw, hh, r, color, layers=4):
    """Neon glow навколо rounded rect"""
    for i in range(layers, 0, -1):
        expand = i * 4
        dim    = layers - i + 1
        gc = tuple(max(0, c // dim) for c in color)
        draw.rounded_rectangle(
            (cx - hw - expand, cy - hh - expand,
             cx + hw + expand, cy + hh + expand),
            radius=r + expand // 2,
            outline=gc,
            width=2
        )

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ ОДНОГО ОКА
# ─────────────────────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             lid_top=0.0,
             lid_angle=0.0,
             gaze_x=0.0,
             gaze_y=0.0,
             iris_scale=1.0,
             glow_color=None,
             sclera_color=None,
             blink_line=False,
             bg_color=None):

    if glow_color   is None: glow_color   = C_CYAN
    if sclera_color is None: sclera_color = C_SCLERA
    if bg_color     is None: bg_color     = C_BG

    r = ER

    # 1. GLOW
    draw_glow(draw, cx, cy, hw, hh, r, glow_color)

    # 2. БІЛОК
    draw_rrect(draw, cx, cy, hw, hh, r, fill=sclera_color)

    # 3. РАЙДУЖКА + ЗІНИЦЯ
    if not blink_line:
        iris_hw = int(hw * 0.50 * iris_scale)
        iris_hh = int(hh * 0.50 * iris_scale)
        max_gx  = hw - iris_hw - 5
        max_gy  = hh - iris_hh - 5
        off_x   = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
        off_y   = int(clamp(gaze_y * max_gy, -max_gy, max_gy))
        icx, icy = cx + off_x, cy + off_y

        # Зовнішня темна райдужка
        dark = tuple(max(0, c - 60) for c in C_IRIS)
        draw.ellipse((icx - iris_hw, icy - iris_hh,
                      icx + iris_hw, icy + iris_hh), fill=dark)
        # Яскрава внутрішня
        in_hw = int(iris_hw * 0.68)
        in_hh = int(iris_hh * 0.68)
        draw.ellipse((icx - in_hw, icy - in_hh,
                      icx + in_hw, icy + in_hh), fill=C_IRIS)
        # Зіниця
        p_hw = int(iris_hw * 0.46)
        p_hh = int(iris_hh * 0.46)
        draw.ellipse((icx - p_hw, icy - p_hh,
                      icx + p_hw, icy + p_hh), fill=C_PUPIL)
        # Відблиск
        sh_x = icx - int(iris_hw * 0.30)
        sh_y = icy - int(iris_hh * 0.30)
        sh_r = max(3, int(iris_hw * 0.17))
        draw.ellipse((sh_x - sh_r, sh_y - sh_r,
                      sh_x + sh_r, sh_y + sh_r), fill=C_SHINE)
        # Маленький другий відблиск
        sh2_r = max(2, sh_r // 2)
        draw.ellipse((sh_x + sh_r, sh_y - sh2_r,
                      sh_x + sh_r + sh2_r * 2, sh_y + sh2_r),
                     fill=(200, 230, 255))

    # 4. ПОВІКА
    if lid_top > 0.01 or abs(lid_angle) > 0.5:
        lid_px = int(hh * 2 * lid_top)

        if abs(lid_angle) < 0.5:
            # Горизонтальна повіка
            draw.rectangle(
                (cx - hw - 2, cy - hh - 2,
                 cx + hw + 2, cy - hh + lid_px),
                fill=bg_color
            )
            if blink_line or lid_top > 0.85:
                line_y = cy - hh + lid_px
                draw.line([(cx - hw + 6, line_y),
                           (cx + hw - 6, line_y)],
                          fill=glow_color, width=4)
        else:
            # Кутова повіка (angry) — трапеція
            angle_rad  = math.radians(abs(lid_angle))
            half_tilt  = int(hw * math.tan(angle_rad))
            top_y      = cy - hh - 2
            left_bot_y  = cy - hh + lid_px - half_tilt
            right_bot_y = cy - hh + lid_px + half_tilt
            draw.polygon(
                [(cx - hw - 2, top_y),
                 (cx + hw + 2, top_y),
                 (cx + hw + 2, right_bot_y),
                 (cx - hw - 2, left_bot_y)],
                fill=bg_color
            )

    # 5. КОНТУР поверх всього
    gc_outline = tuple(min(255, c + 25) for c in glow_color)
    draw_rrect(draw, cx, cy, hw, hh, r, outline=gc_outline, width=3)

# ─────────────────────────────────────────────────────────────────────────────
# РОТ
# ─────────────────────────────────────────────────────────────────────────────
def draw_mouth(draw, style="none", open_factor=0.0, glow_color=None):
    if style == "none":
        return
    if glow_color is None:
        glow_color = C_CYAN

    if style == "open" or open_factor > 0.05:
        ow = int(MW * 0.7)
        oh = int(22 + 24 * open_factor)
        gc = tuple(max(0, c // 4) for c in glow_color)
        draw.ellipse((MX - ow - 3, MY - oh - 3,
                      MX + ow + 3, MY + oh + 3), fill=gc)
        draw.ellipse((MX - ow, MY - oh, MX + ow, MY + oh),
                     fill=(10, 10, 10))
        draw.ellipse((MX - ow, MY - oh, MX + ow, MY + oh),
                     outline=C_WHITE, width=3)

    elif style == "happy":
        arc_h = 20
        # Glow
        draw.arc((MX - MW - 4, MY - arc_h - 4,
                  MX + MW + 4, MY + arc_h + 4),
                 start=10, end=170, fill=(80, 80, 80), width=8)
        draw.arc((MX - MW, MY - arc_h, MX + MW, MY + arc_h),
                 start=10, end=170, fill=C_WHITE, width=5)

    elif style == "sad":
        arc_h = 16
        gc = tuple(max(0, c // 4) for c in C_CYAN)
        draw.arc((MX - MW - 4, MY - arc_h - 4,
                  MX + MW + 4, MY + arc_h + 4),
                 start=190, end=350, fill=gc, width=8)
        draw.arc((MX - MW, MY - arc_h, MX + MW, MY + arc_h),
                 start=190, end=350, fill=C_CYAN, width=4)

# ─────────────────────────────────────────────────────────────────────────────
# БРОВИ (surprised)
# ─────────────────────────────────────────────────────────────────────────────
def draw_brows_surprised(draw, lift=1.0):
    for cx in [EL_X, ER_X]:
        bw = 48
        bh = int(16 * lift)
        by = EY - EH - BROW_H - int(18 * lift)
        draw.arc((cx - bw - 3, by - bh - 3,
                  cx + bw + 3, by + bh + 3),
                 start=200, end=340, fill=(80, 80, 80), width=7)
        draw.arc((cx - bw, by - bh, cx + bw, by + bh),
                 start=200, end=340, fill=C_WHITE, width=4)

# ─────────────────────────────────────────────────────────────────────────────
# СЛЬОЗИ
# ─────────────────────────────────────────────────────────────────────────────
def draw_tears(draw, elapsed):
    for base_x, offset in [(EL_X - 14, 0.0), (ER_X + 14, 0.55)]:
        drop_y = EY + EH + int((elapsed * 55 + offset * 90) % 110)
        draw.ellipse((base_x - 7, drop_y - 13,
                      base_x + 7, drop_y + 7), fill=C_TEAR)
        draw.ellipse((base_x - 3, drop_y - 9,
                      base_x + 1, drop_y - 4),
                     fill=(200, 240, 255))

# ─────────────────────────────────────────────────────────────────────────────
# РЕНДЕР КАДРУ
# ─────────────────────────────────────────────────────────────────────────────
def render(
    l_lid=0.0, l_lid_angle=0.0, l_gaze_x=0.0, l_gaze_y=0.0,
    l_iris_scale=1.0, l_blink_line=False,
    r_lid=0.0, r_lid_angle=0.0, r_gaze_x=0.0, r_gaze_y=0.0,
    r_iris_scale=1.0, r_blink_line=False,
    hw=EW, hh=EH,
    glow_color=None, sclera_color=None,
    mouth="none", mouth_open=0.0,
    brows=False, brow_lift=1.0,
    bg=(0, 0, 0),
    tears=False, tears_elapsed=0.0,
    extra_fn=None
):
    if glow_color   is None: glow_color   = C_CYAN
    if sclera_color is None: sclera_color = C_SCLERA

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Ліве oko (кут повіки — дзеркальний)
    draw_eye(draw, EL_X, EY, hw, hh,
             lid_top=l_lid, lid_angle=-l_lid_angle,
             gaze_x=l_gaze_x, gaze_y=l_gaze_y,
             iris_scale=l_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=l_blink_line,
             bg_color=bg)

    # Праве oko
    draw_eye(draw, ER_X, EY, hw, hh,
             lid_top=r_lid, lid_angle=r_lid_angle,
             gaze_x=r_gaze_x, gaze_y=r_gaze_y,
             iris_scale=r_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=r_blink_line,
             bg_color=bg)

    if brows:
        draw_brows_surprised(draw, lift=brow_lift)

    draw_mouth(draw, style=mouth, open_factor=mouth_open,
               glow_color=glow_color)

    if tears:
        draw_tears(draw, tears_elapsed)

    if extra_fn:
        extra_fn(draw)

    device.display(img)

# ─────────────────────────────────────────────────────────────────────────────
# АНІМАЦІЇ
# ─────────────────────────────────────────────────────────────────────────────

def _blink(mouth="none", glow_color=None, bg=(0,0,0)):
    if glow_color is None: glow_color = C_CYAN
    steps = 7
    for i in range(steps):
        t = ease_inout(i / steps)
        render(l_lid=t, r_lid=t, mouth=mouth, glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.013)
    render(l_lid=1.0, r_lid=1.0, mouth=mouth, glow_color=glow_color, bg=bg,
           l_blink_line=True, r_blink_line=True)
    time.sleep(0.05)
    for i in range(steps):
        t = ease_inout(1.0 - i / steps)
        render(l_lid=t, r_lid=t, mouth=mouth, glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.013)

# ── 😊 HAPPY ─────────────────────────────────────────────────────────────────
def anim_happy(duration=6.0):
    t_start  = time.time()
    t        = 0.0
    blink_t  = time.time() + random.uniform(2.5, 4.5)
    gx, gy   = 0.0, 0.0
    tgx, tgy = 0.0, 0.0
    gaze_t   = time.time() + random.uniform(1.5, 3.0)

    while time.time() - t_start < duration:
        t += DT
        breathe = 0.010 * math.sin(t * 1.5)
        hw = int(EW * (1 + breathe))
        hh = int(EH * (1 + breathe))

        gx = lerp(gx, tgx, 0.07)
        gy = lerp(gy, tgy, 0.07)
        if time.time() >= gaze_t:
            tgx   = random.uniform(-0.5, 0.5)
            tgy   = random.uniform(-0.25, 0.25)
            gaze_t = time.time() + random.uniform(1.5, 3.0)

        render(hw=hw, hh=hh,
               l_gaze_x=gx, l_gaze_y=gy,
               r_gaze_x=gx, r_gaze_y=gy,
               mouth="happy", glow_color=C_CYAN)

        if time.time() >= blink_t:
            _blink(mouth="happy", glow_color=C_CYAN)
            blink_t = time.time() + random.uniform(2.5, 4.5)

        time.sleep(DT)

# ── 😲 SURPRISED ─────────────────────────────────────────────────────────────
def anim_surprised(duration=4.0):
    t_start    = time.time()
    t          = 0.0
    spring_dur = 0.5
    gx, gy     = 0.0, 0.0

    while time.time() - t_start < duration:
        elapsed = time.time() - t_start
        t += DT

        if elapsed < spring_dur:
            st        = elapsed / spring_dur
            overshoot = 1.0 + 0.12 * math.exp(-st * 4) * math.cos(st * 18)
            hw        = int(EW * overshoot)
            hh        = int(EH * overshoot)
            iris_sc   = max(0.55, 1.0 - 0.3 * st)
            brow_lift = st
        else:
            hw = EW; hh = EH
            iris_sc   = 0.70
            brow_lift = 1.0
            gx = 0.28 * math.sin(t * 1.3)
            gy = -0.18 * abs(math.sin(t * 0.85))

        render(hw=hw, hh=hh,
               l_gaze_x=gx, r_gaze_x=gx,
               l_gaze_y=gy, r_gaze_y=gy,
               l_iris_scale=iris_sc, r_iris_scale=iris_sc,
               brows=True, brow_lift=brow_lift,
               glow_color=C_CYAN, mouth="none")
        time.sleep(DT)

# ── 😢 SAD ────────────────────────────────────────────────────────────────────
def anim_sad(duration=6.0):
    t_start = time.time()
    t       = 0.0
    blink_t = time.time() + random.uniform(3.5, 6.0)
    LID     = 0.42

    while time.time() - t_start < duration:
        elapsed = time.time() - t_start
        t += DT
        sway = 0.05 * math.sin(t * 0.5)

        render(l_lid=LID + sway, r_lid=LID + sway,
               l_gaze_y=0.32, r_gaze_y=0.32,
               mouth="sad",
               glow_color=C_CYAN_DIM,
               tears=True, tears_elapsed=elapsed)

        if time.time() >= blink_t:
            _blink(mouth="sad", glow_color=C_CYAN_DIM)
            blink_t = time.time() + random.uniform(3.5, 6.0)

        time.sleep(DT)

# ── 😠 ANGRY ──────────────────────────────────────────────────────────────────
def anim_angry(duration=5.0):
    t_start = time.time()
    t       = 0.0
    frame_n = 0
    LID     = 0.38
    ANGLE   = 18.0

    def angry_extra(draw):
        if frame_n % 6 < 3:
            pulse = abs(math.sin(frame_n * 0.28))
            # PIL: помаранчевий = (0, int(160*pulse), 255) → екран (255,160p,0)
            col = (0, int(160 * pulse), 255)
            draw.text((W // 2 - 10, 8), "!!!", fill=col)

    while time.time() - t_start < duration:
        t += DT
        frame_n += 1
        elapsed = time.time() - t_start

        # Фон: PIL (r,0,0) → екран (0,0,r) = синій НЕ той
        # PIL (0,0,r) → екран (r,0,0) = червоний ✓
        bg_r = min(55, int(55 * min(1.0, elapsed / 0.8)))
        bg   = (0, 0, bg_r)   # ← виправлено! bgr=True: PIL B→екран R

        shake = int(7 * max(0, 1.0 - elapsed * 0.5))
        pulse = abs(math.sin(t * 3.8))
        lid_v = LID + 0.05 * pulse

        render(
            l_lid=lid_v, l_lid_angle=ANGLE,
            r_lid=lid_v, r_lid_angle=ANGLE,
            glow_color=C_GLOW_ANGRY,
            sclera_color=C_SCLERA_ANGRY,
            mouth="none",
            bg=bg,
            extra_fn=angry_extra
        )
        time.sleep(DT)

# ── 🤔 THINKING ───────────────────────────────────────────────────────────────
def anim_thinking(duration=6.0):
    t_start = time.time()
    t       = 0.0
    blink_t = time.time() + random.uniform(2.0, 3.5)
    L_LID   = 0.0
    R_LID   = 0.50

    FORMULAS = ["E=mc²", "π≈3.14", "42?", "∑n²", "∞", "AI>0", "f(x)?", "..."]
    f_text  = ""
    f_alpha = 0
    f_x, f_y = 300, 28
    f_t     = time.time() + 1.0

    def thinking_extra(draw):
        nonlocal f_text, f_alpha, f_x, f_y, f_t
        if time.time() >= f_t:
            f_text  = random.choice(FORMULAS)
            f_x     = random.randint(260, 400)
            f_y     = random.randint(12, 60)
            f_alpha = 200
            f_t     = time.time() + random.uniform(2.0, 3.5)
        if f_alpha > 0:
            # PIL cyan: (255, int(180*a/200), 0) → екран (0,180a,255)
            col = (255, int(180 * f_alpha / 200), 0)
            draw.text((f_x, f_y), f_text, fill=col)
            f_alpha = max(0, f_alpha - 12)

    while time.time() - t_start < duration:
        t += DT
        gx = 0.36 + 0.10 * math.sin(t * 0.7)
        gy = -0.22 + 0.07 * math.sin(t * 0.5)

        render(
            l_lid=L_LID, l_gaze_x=gx, l_gaze_y=gy,
            r_lid=R_LID, r_gaze_x=gx, r_gaze_y=gy + 0.13,
            glow_color=C_CYAN,
            mouth="none",
            extra_fn=thinking_extra
        )

        if time.time() >= blink_t:
            for i in range(6):
                tv = ease_inout(i / 6)
                render(l_lid=tv, r_lid=R_LID,
                       l_blink_line=(tv > 0.8), glow_color=C_CYAN)
                time.sleep(0.013)
            time.sleep(0.05)
            for i in range(6):
                tv = ease_inout(1.0 - i / 6)
                render(l_lid=tv, r_lid=R_LID,
                       l_blink_line=(tv > 0.8), glow_color=C_CYAN)
                time.sleep(0.013)
            blink_t = time.time() + random.uniform(2.0, 3.5)

        time.sleep(DT)

# ── Говоріння ────────────────────────────────────────────────────────────────
def anim_talking(duration=3.0):
    t_start = time.time()
    t       = 0.0
    while time.time() - t_start < duration:
        t += DT
        open_f = max(0.0, 0.6 * abs(math.sin(t * 9.0)))
        render(mouth="open", mouth_open=open_f, glow_color=C_CYAN)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# ПЛАВНИЙ ПЕРЕХІД
# ─────────────────────────────────────────────────────────────────────────────
def transition_to(from_state, to_state, duration=0.45):
    steps = max(4, int(duration / DT))
    for i in range(steps + 1):
        t       = ease_inout(i / steps)
        blended = {}
        for key in to_state:
            fv = from_state.get(key, to_state[key])
            tv = to_state[key]
            if isinstance(tv, (int, float)):
                blended[key] = lerp(fv, tv, t)
            elif isinstance(tv, tuple) and len(tv) == 3:
                blended[key] = tuple(int(lerp(fv[j], tv[j], t))
                                     for j in range(3))
            else:
                blended[key] = tv if t > 0.5 else fv
        render(**blended)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# СТАНИ
# ─────────────────────────────────────────────────────────────────────────────
STATE_HAPPY = dict(
    l_lid=0.0, r_lid=0.0, mouth="happy",
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)

STATE_SURPRISED = dict(
    l_lid=0.0, r_lid=0.0, l_iris_scale=0.70, r_iris_scale=0.70,
    brows=True, brow_lift=1.0, mouth="none",
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)

STATE_SAD = dict(
    l_lid=0.42, r_lid=0.42, l_gaze_y=0.32, r_gaze_y=0.32,
    mouth="sad", glow_color=C_CYAN_DIM,
    sclera_color=C_SCLERA, bg=C_BG)

STATE_ANGRY = dict(
    l_lid=0.38, r_lid=0.38, l_lid_angle=18.0, r_lid_angle=18.0,
    mouth="none", glow_color=C_GLOW_ANGRY,
    sclera_color=C_SCLERA_ANGRY,
    bg=(0, 0, 55))   # PIL→екран: темно-червоний ✓

STATE_THINKING = dict(
    l_lid=0.0, r_lid=0.50, mouth="none",
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)

# ─────────────────────────────────────────────────────────────────────────────
# ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("🤖 AIKO eyes_v2 запущено! Ctrl+C щоб зупинити")

    # Поява
    for i in range(10):
        t = ease_inout(1.0 - i / 10)
        render(l_lid=t, r_lid=t, mouth="happy",
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.04)

    prev = STATE_HAPPY

    while True:
        print("😊 Happy...")
        anim_happy(duration=6.0)

        print("→ 😲 Surprised!")
        transition_to(prev, STATE_SURPRISED, duration=0.4)
        prev = STATE_SURPRISED
        anim_surprised(duration=4.0)

        print("→ 😢 Sad...")
        transition_to(prev, STATE_SAD, duration=0.6)
        prev = STATE_SAD
        anim_sad(duration=6.0)

        print("→ 😠 Angry!")
        transition_to(prev, STATE_ANGRY, duration=0.35)
        prev = STATE_ANGRY
        anim_angry(duration=5.0)

        print("→ 🤔 Thinking...")
        transition_to(prev, STATE_THINKING, duration=0.5)
        prev = STATE_THINKING
        anim_thinking(duration=6.0)

        print("→ 😊 Happy знову!")
        transition_to(prev, STATE_HAPPY, duration=0.5)
        prev = STATE_HAPPY

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
