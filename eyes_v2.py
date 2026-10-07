"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AIKO eyes_v2.py — процедурна анімація очей  v3.0                 ║
║           Стиль: neon cyan glow, чорний фон, мультяшний                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ЗМІНИ v3.0:                                                                ║
║  - Фікс чорних кутів glow → RGBA alpha_composite                           ║
║  - Очі -20%: EW=60, EH=68, ER=26                                           ║
║  - Єдина базова позиція для всіх емоцій (BASE_EY=148)                      ║
║  - Рот для ВСІХ емоцій, width=10, MW=90                                    ║
║  - angry: оскал із зубками                                                  ║
║  - thinking: smirk що зміщується + язик                                    ║
║  - surprised: відкритий овал                                                ║
║  - Рот синхронний з очима в transition_to                                  ║
║  - Випадковий порядок емоцій (не ланцюжок)                                 ║
║  - Перехід між емоціями: 0.5 сек                                            ║
║                                                                              ║
║  ⚠️  bgr=True на ILI9488: PIL (R,G,B) → екран (B,G,R)                     ║
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
C_BG           = (0,   0,   0  )   # чорний — однаковий
C_CYAN         = (255, 220, 0  )   # PIL→екран: cyan (0,220,255) ✓
C_CYAN_DIM     = (130, 120, 0  )   # тьмяний cyan для sad
C_GLOW_ANGRY   = (0,   80,  255)   # PIL→екран: помаранчевий (255,80,0) ✓
C_WHITE        = (255, 255, 255)   # білий — однаковий
C_SCLERA       = (255, 255, 255)   # білок нормальний
C_SCLERA_ANGRY = (200, 200, 255)   # PIL→екран: рожевий (255,200,200) ✓
C_IRIS         = (255, 140, 30 )   # PIL→екран: синя райдужка (30,140,255) ✓
C_PUPIL        = (0,   0,   0  )   # чорна зіниця
C_SHINE        = (255, 255, 255)   # відблиск білий
C_TEAR         = (255, 200, 0  )   # PIL→екран: cyan сльоза (0,200,255) ✓
C_BG_ANGRY     = (0,   0,   55 )   # PIL→екран: темно-червоний ✓
C_TONGUE       = (180, 60,  255)   # PIL→екран: рожевий язик (255,60,180) ✓
C_TEETH        = (255, 255, 255)   # зуби білі

# ── Геометрія очей ────────────────────────────────────────────────────────────
# Базова позиція — ЄДИНА для всіх емоцій
BASE_EL_X = 118   # X лівого ока
BASE_ER_X = 362   # X правого ока
BASE_EY   = 148   # Y центр очей

# Розмір ока -20% від попередньої версії
EW = 60    # напів-ширина  (було 75)
EH = 68    # напів-висота  (було 85)
ER = 26    # радіус заокруглення (було 32)

# Рот
MX = W // 2   # 240 — центр рота по X
MY = 272      # Y рота
MW = 90       # ширина рота (було 60)

# Брови (surprised)
BROW_H = 18

# ─────────────────────────────────────────────────────────────────────────────
# ДОПОМІЖНІ ФУНКЦІЇ
# ─────────────────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def ease_inout(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

# ─────────────────────────────────────────────────────────────────────────────
# GLOW — через RGBA шар (фікс чорних кутів!)
# ─────────────────────────────────────────────────────────────────────────────
def draw_glow_rgba(base_img, cx, cy, hw, hh, r, color, layers=5):
    """
    Малює glow через окремий RGBA шар і накладає через alpha_composite.
    Це усуває чорний фон між шарами rounded_rectangle.
    """
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)

    for i in range(layers, 0, -1):
        expand  = i * 5
        alpha   = int(200 * (1 - i / (layers + 1)))
        gc      = (color[0], color[1], color[2], alpha)
        gd.rounded_rectangle(
            (cx - hw - expand, cy - hh - expand,
             cx + hw + expand, cy + hh + expand),
            radius=r + expand // 2,
            outline=gc,
            width=3
        )

    # Накладаємо на base_img (він має бути RGBA)
    base_img.alpha_composite(glow_layer)

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ ОДНОГО ОКА
# ─────────────────────────────────────────────────────────────────────────────
def draw_eye(base_img, draw, cx, cy, hw, hh,
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

    # 1. GLOW через RGBA шар (без чорних кутів!)
    draw_glow_rgba(base_img, cx, cy, hw, hh, r, glow_color)

    # Оновлюємо draw після зміни base_img
    draw = ImageDraw.Draw(base_img)

    # 2. БІЛОК — заповнений rounded rect
    x0, y0 = cx - hw, cy - hh
    x1, y1 = cx + hw, cy + hh
    draw.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=sclera_color)

    # 3. РАЙДУЖКА + ЗІНИЦЯ
    if not blink_line and lid_top < 0.95:
        iris_hw = int(hw * 0.50 * iris_scale)
        iris_hh = int(hh * 0.50 * iris_scale)
        max_gx  = max(1, hw - iris_hw - 4)
        max_gy  = max(1, hh - iris_hh - 4)
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
        # Другий маленький відблиск
        sh2_r = max(2, sh_r // 2)
        draw.ellipse((sh_x + sh_r, sh_y - sh2_r,
                      sh_x + sh_r + sh2_r * 2, sh_y + sh2_r),
                     fill=(200, 230, 255))

    # 4. ПОВІКА — малюємо поверх, тим самим кольором що і фон
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
            angle_rad   = math.radians(abs(lid_angle))
            half_tilt   = int(hw * math.tan(angle_rad))
            top_y       = cy - hh - 2
            left_bot_y  = cy - hh + lid_px - half_tilt
            right_bot_y = cy - hh + lid_px + half_tilt
            draw.polygon(
                [(cx - hw - 2, top_y),
                 (cx + hw + 2, top_y),
                 (cx + hw + 2, right_bot_y),
                 (cx - hw - 2, left_bot_y)],
                fill=bg_color
            )

    # 5. КОНТУР — поверх всього, щоб glow і повіка не псували обводку
    gc_outline = tuple(min(255, c + 30) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=r,
        outline=gc_outline,
        width=3
    )


# ─────────────────────────────────────────────────────────────────────────────
# РОТ — всі стилі, width=10
# ─────────────────────────────────────────────────────────────────────────────
def draw_mouth(draw, style="none", open_factor=0.0,
               morph=1.0, offset_x=0, glow_color=None):
    """
    style: none | happy | sad | surprised | angry | thinking
    morph: 0.0→1.0 — плавна поява форми (для transition)
    offset_x: зміщення по X (для thinking smirk)
    """
    if style == "none":
        return
    if glow_color is None:
        glow_color = C_CYAN

    mx = MX + int(offset_x)
    alpha = clamp(morph, 0.0, 1.0)

    # ── HAPPY — усмішка-дуга ──────────────────────────────────────────────────
    if style == "happy":
        arc_h = int(26 * alpha)
        arc_w = int(MW * alpha)
        if arc_w < 4 or arc_h < 4:
            return
        # Glow
        gc = tuple(max(0, c // 5) for c in glow_color)
        draw.arc((mx - arc_w - 5, MY - arc_h - 5,
                  mx + arc_w + 5, MY + arc_h + 5),
                 start=10, end=170, fill=gc, width=14)
        # Основна лінія
        draw.arc((mx - arc_w, MY - arc_h,
                  mx + arc_w, MY + arc_h),
                 start=10, end=170, fill=C_WHITE, width=10)

    # ── SAD — перевернута дуга ────────────────────────────────────────────────
    elif style == "sad":
        arc_h = int(22 * alpha)
        arc_w = int(MW * alpha)
        if arc_w < 4 or arc_h < 4:
            return
        gc = tuple(max(0, c // 5) for c in C_CYAN_DIM)
        draw.arc((mx - arc_w - 5, MY - arc_h - 5,
                  mx + arc_w + 5, MY + arc_h + 5),
                 start=190, end=350, fill=gc, width=14)
        draw.arc((mx - arc_w, MY - arc_h,
                  mx + arc_w, MY + arc_h),
                 start=190, end=350, fill=C_CYAN_DIM, width=10)

    # ── SURPRISED — відкритий овал ────────────────────────────────────────────
    elif style == "surprised":
        ow = int(MW * 0.50 * alpha)
        oh = int(36 * alpha)
        if ow < 4 or oh < 4:
            return
        # Glow
        gc = tuple(max(0, c // 5) for c in glow_color)
        draw.ellipse((mx - ow - 6, MY - oh - 6,
                      mx + ow + 6, MY + oh + 6), fill=gc)
        # Темний фон рота
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     fill=(15, 15, 15))
        # Контур
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     outline=C_WHITE, width=10)

    # ── ANGRY — оскал із зубками ─────────────────────────────────────────────
    elif style == "angry":
        ow = int(MW * 0.65 * alpha)
        oh = int(22 * alpha)
        if ow < 4 or oh < 4:
            return
        # Glow
        gc = tuple(max(0, c // 5) for c in C_GLOW_ANGRY)
        draw.ellipse((mx - ow - 6, MY - oh - 6,
                      mx + ow + 6, MY + oh + 6), fill=gc)
        # Темний фон рота
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     fill=(10, 10, 10))
        # Контур рота
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     outline=C_GLOW_ANGRY, width=10)
        # Зубки — вертикальні лінії у верхній половині
        tooth_count = 5
        tooth_w     = (ow * 2) // (tooth_count + 1)
        for i in range(tooth_count):
            tx = mx - ow + tooth_w * (i + 1)
            # Малюємо тільки якщо tx в межах еліпса
            if abs(tx - mx) < ow - 6:
                draw.rectangle(
                    (tx - 4, MY - oh + 4,
                     tx + 4, MY + 4),
                    fill=C_TEETH
                )

    # ── THINKING — асиметрична smirk + язик ──────────────────────────────────
    elif style == "thinking":
        arc_w  = int(MW * 0.60 * alpha)
        # Рот зміщений вправо — управляється offset_x зовні
        # Ліво-право кути різні (smirk)
        # Малюємо як polybezier через points
        pts_count = 20
        pts = []
        for i in range(pts_count + 1):
            fx = i / pts_count  # 0..1
            px = mx - arc_w + int(arc_w * 2 * fx)
            # Ліва сторона нижче, права вище — асиметрія
            left_drop  = int(18 * alpha)
            right_rise = int(12 * alpha)
            py = MY + int(lerp(left_drop, -right_rise, ease_inout(fx)))
            pts.append((px, py))
        if len(pts) >= 2:
            # Glow
            gc = tuple(max(0, c // 5) for c in glow_color)
            draw.line(pts, fill=gc, width=18)
            draw.line(pts, fill=C_WHITE, width=10)

        # Язик — маленький рожевий на правому кутику рота
        if alpha > 0.5:
            tongue_alpha = (alpha - 0.5) * 2.0
            tx = mx + arc_w - 8
            ty = MY - int(10 * tongue_alpha)
            tr = int(10 * tongue_alpha)
            if tr > 2:
                draw.ellipse((tx - tr, ty - tr // 2,
                              tx + tr, ty + tr),
                             fill=C_TONGUE)


# ─────────────────────────────────────────────────────────────────────────────
# БРОВИ (surprised)
# ─────────────────────────────────────────────────────────────────────────────
def draw_brows_surprised(draw, lift=1.0):
    for cx in [BASE_EL_X, BASE_ER_X]:
        bw = int(44 * lift)
        bh = int(14 * lift)
        by = BASE_EY - EH - BROW_H - int(16 * lift)
        if bw < 4 or bh < 4:
            continue
        draw.arc((cx - bw - 3, by - bh - 3,
                  cx + bw + 3, by + bh + 3),
                 start=200, end=340, fill=(80, 80, 80), width=8)
        draw.arc((cx - bw, by - bh, cx + bw, by + bh),
                 start=200, end=340, fill=C_WHITE, width=5)


# ─────────────────────────────────────────────────────────────────────────────
# СЛЬОЗИ
# ─────────────────────────────────────────────────────────────────────────────
def draw_tears(draw, elapsed):
    for base_x, offset in [(BASE_EL_X - 14, 0.0),
                            (BASE_ER_X + 14, 0.55)]:
        drop_y = BASE_EY + EH + int((elapsed * 55 + offset * 90) % 110)
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
    hw=None, hh=None,
    glow_color=None, sclera_color=None,
    mouth="none", mouth_open=0.0, mouth_morph=1.0, mouth_offset_x=0,
    brows=False, brow_lift=1.0,
    bg=None,
    tears=False, tears_elapsed=0.0,
    extra_fn=None
):
    if glow_color   is None: glow_color   = C_CYAN
    if sclera_color is None: sclera_color = C_SCLERA
    if bg           is None: bg           = C_BG
    if hw           is None: hw           = EW
    if hh           is None: hh           = EH

    # Працюємо в RGBA для підтримки alpha_composite
    img  = Image.new("RGBA", (W, H), bg + (255,))
    draw = ImageDraw.Draw(img)

    # Ліве oko
    draw_eye(img, draw, BASE_EL_X, BASE_EY, hw, hh,
             lid_top=l_lid, lid_angle=-l_lid_angle,
             gaze_x=l_gaze_x, gaze_y=l_gaze_y,
             iris_scale=l_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=l_blink_line,
             bg_color=bg)

    # Праве oko
    draw_eye(img, draw, BASE_ER_X, BASE_EY, hw, hh,
             lid_top=r_lid, lid_angle=r_lid_angle,
             gaze_x=r_gaze_x, gaze_y=r_gaze_y,
             iris_scale=r_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=r_blink_line,
             bg_color=bg)

    # Оновлюємо draw після draw_eye (бо він міг перестворити)
    draw = ImageDraw.Draw(img)

    if brows:
        draw_brows_surprised(draw, lift=brow_lift)

    draw_mouth(draw, style=mouth,
               open_factor=mouth_open,
               morph=mouth_morph,
               offset_x=mouth_offset_x,
               glow_color=glow_color)

    if tears:
        draw_tears(draw, tears_elapsed)

    if extra_fn:
        extra_fn(draw)

    # Конвертуємо RGBA → RGB для відображення
    rgb_img = img.convert("RGB")
    device.display(rgb_img)


# ─────────────────────────────────────────────────────────────────────────────
# МОРГАННЯ (спільне для happy/sad/talking)
# ─────────────────────────────────────────────────────────────────────────────
def _blink(mouth="none", glow_color=None, bg=None,
           r_lid_fixed=None, extra_fn=None):
    """Одне моргання. r_lid_fixed — якщо праве oko не має моргати (thinking)"""
    if glow_color is None: glow_color = C_CYAN
    if bg         is None: bg         = C_BG

    steps = 7
    for i in range(steps):
        t     = ease_inout(i / steps)
        r_lid = r_lid_fixed if r_lid_fixed is not None else t
        render(l_lid=t, r_lid=r_lid,
               mouth=mouth, glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8),
               r_blink_line=(r_lid > 0.8) if r_lid_fixed is None else False,
               extra_fn=extra_fn)
        time.sleep(0.013)

    r_lid = r_lid_fixed if r_lid_fixed is not None else 1.0
    render(l_lid=1.0, r_lid=r_lid,
           mouth=mouth, glow_color=glow_color, bg=bg,
           l_blink_line=True,
           r_blink_line=False if r_lid_fixed is not None else True,
           extra_fn=extra_fn)
    time.sleep(0.05)

    for i in range(steps):
        t     = ease_inout(1.0 - i / steps)
        r_lid = r_lid_fixed if r_lid_fixed is not None else t
        render(l_lid=t, r_lid=r_lid,
               mouth=mouth, glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8),
               r_blink_line=False if r_lid_fixed is not None else (t > 0.8),
               extra_fn=extra_fn)
        time.sleep(0.013)


# ─────────────────────────────────────────────────────────────────────────────
# ПЛАВНИЙ ПЕРЕХІД МІЖ СТАНАМИ (очі + рот синхронно, 0.5 сек)
# ─────────────────────────────────────────────────────────────────────────────
# Числові ключі що інтерполюються
_NUMERIC_KEYS = {
    "l_lid", "r_lid", "l_lid_angle", "r_lid_angle",
    "l_gaze_x", "l_gaze_y", "r_gaze_x", "r_gaze_y",
    "l_iris_scale", "r_iris_scale",
    "hw", "hh",
    "mouth_morph", "mouth_offset_x",
    "brow_lift",
}
# Кольорові ключі (tuple of 3)
_COLOR_KEYS = {"glow_color", "sclera_color", "bg"}


def transition_to(from_state, to_state, duration=0.5):
    """
    Плавний перехід між двома словниками стану.
    Рот і очі синхронні: mouth_morph 1→0→1 між стилями.
    """
    steps = max(4, int(duration / DT))

    from_mouth = from_state.get("mouth", "none")
    to_mouth   = to_state.get("mouth",   "none")
    same_mouth = (from_mouth == to_mouth)

    for i in range(steps + 1):
        t = ease_inout(i / steps)
        frame = {}

        for key in set(list(from_state.keys()) + list(to_state.keys())):
            fv = from_state.get(key)
            tv = to_state.get(key)

            if fv is None and tv is None:
                continue
            if fv is None:
                fv = tv
            if tv is None:
                tv = fv

            if key in _NUMERIC_KEYS:
                frame[key] = lerp(fv, tv, t)
            elif key in _COLOR_KEYS:
                frame[key] = lerp_color(fv, tv, t)
            else:
                # Рядки / bool — перемикаємо в середині
                frame[key] = tv if t >= 0.5 else fv

        # Mouth morph: якщо стиль різний — спочатку зникає, потім з'являється
        if not same_mouth:
            if t < 0.5:
                frame["mouth"]       = from_mouth
                frame["mouth_morph"] = 1.0 - ease_inout(t * 2)
            else:
                frame["mouth"]       = to_mouth
                frame["mouth_morph"] = ease_inout((t - 0.5) * 2)
        else:
            frame["mouth"]       = from_mouth
            frame["mouth_morph"] = 1.0

        render(**frame)
        time.sleep(DT)


# ─────────────────────────────────────────────────────────────────────────────
# СТАНИ (базові словники для transition_to)
# ─────────────────────────────────────────────────────────────────────────────
STATE_HAPPY = dict(
    l_lid=0.0, r_lid=0.0,
    l_gaze_x=0.0, l_gaze_y=0.0,
    r_gaze_x=0.0, r_gaze_y=0.0,
    l_iris_scale=1.0, r_iris_scale=1.0,
    hw=EW, hh=EH,
    mouth="happy", mouth_morph=1.0, mouth_offset_x=0,
    brows=False, brow_lift=0.0,
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG
)

STATE_SURPRISED = dict(
    l_lid=0.0, r_lid=0.0,
    l_gaze_x=0.0, l_gaze_y=0.0,
    r_gaze_x=0.0, r_gaze_y=0.0,
    l_iris_scale=0.70, r_iris_scale=0.70,
    hw=EW, hh=EH,
    mouth="surprised", mouth_morph=1.0, mouth_offset_x=0,
    brows=True, brow_lift=1.0,
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG
)

STATE_SAD = dict(
    l_lid=0.42, r_lid=0.42,
    l_gaze_x=0.0, l_gaze_y=0.32,
    r_gaze_x=0.0, r_gaze_y=0.32,
    l_iris_scale=1.0, r_iris_scale=1.0,
    hw=EW, hh=EH,
    mouth="sad", mouth_morph=1.0, mouth_offset_x=0,
    brows=False, brow_lift=0.0,
    glow_color=C_CYAN_DIM, sclera_color=C_SCLERA, bg=C_BG
)

STATE_ANGRY = dict(
    l_lid=0.38, r_lid=0.38,
    l_lid_angle=18.0, r_lid_angle=18.0,
    l_gaze_x=0.0, l_gaze_y=0.0,
    r_gaze_x=0.0, r_gaze_y=0.0,
    l_iris_scale=1.0, r_iris_scale=1.0,
    hw=EW, hh=EH,
    mouth="angry", mouth_morph=1.0, mouth_offset_x=0,
    brows=False, brow_lift=0.0,
    glow_color=C_GLOW_ANGRY, sclera_color=C_SCLERA_ANGRY, bg=C_BG_ANGRY
)

STATE_THINKING = dict(
    l_lid=0.0, r_lid=0.50,
    l_gaze_x=0.36, l_gaze_y=-0.22,
    r_gaze_x=0.36, r_gaze_y=-0.09,
    l_iris_scale=1.0, r_iris_scale=1.0,
    hw=EW, hh=EH,
    mouth="thinking", mouth_morph=1.0, mouth_offset_x=24,
    brows=False, brow_lift=0.0,
    glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG
)

# Список всіх емоцій для випадкового вибору
ALL_EMOTIONS = [
    ("happy",     STATE_HAPPY),
    ("surprised", STATE_SURPRISED),
    ("sad",       STATE_SAD),
    ("angry",     STATE_ANGRY),
    ("thinking",  STATE_THINKING),
]

# Ваги (happy частіше, angry рідше)
EMOTION_WEIGHTS = [0.30, 0.20, 0.20, 0.15, 0.15]


# ─────────────────────────────────────────────────────────────────────────────
# АНІМАЦІЇ ЕМОЦІЙ
# ─────────────────────────────────────────────────────────────────────────────

# ── 😊 HAPPY ──────────────────────────────────────────────────────────────────
def anim_happy(duration=6.0):
    t_start  = time.time()
    t        = 0.0
    blink_t  = time.time() + random.uniform(2.5, 4.5)
    gx, gy   = 0.0, 0.0
    tgx, tgy = 0.0, 0.0
    gaze_t   = time.time() + random.uniform(1.5, 3.0)

    while time.time() - t_start < duration:
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

        render(hw=hw, hh=hh,
               l_gaze_x=gx, l_gaze_y=gy,
               r_gaze_x=gx, r_gaze_y=gy,
               mouth="happy", mouth_morph=1.0,
               glow_color=C_CYAN, bg=C_BG)

        if time.time() >= blink_t:
            _blink(mouth="happy", glow_color=C_CYAN, bg=C_BG)
            blink_t = time.time() + random.uniform(2.5, 4.5)

        time.sleep(DT)


# ── 😲 SURPRISED ──────────────────────────────────────────────────────────────
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
            overshoot = 1.0 + 0.10 * math.exp(-st * 4) * math.cos(st * 18)
            hw        = int(EW * overshoot)
            hh        = int(EH * overshoot)
            iris_sc   = max(0.55, 1.0 - 0.3 * st)
            brow_lift = st
        else:
            hw, hh  = EW, EH
            iris_sc   = 0.70
            brow_lift = 1.0
            gx = 0.25 * math.sin(t * 1.3)
            gy = -0.15 * abs(math.sin(t * 0.85))

        render(hw=hw, hh=hh,
               l_gaze_x=gx, r_gaze_x=gx,
               l_gaze_y=gy, r_gaze_y=gy,
               l_iris_scale=iris_sc, r_iris_scale=iris_sc,
               brows=True, brow_lift=brow_lift,
               mouth="surprised", mouth_morph=min(1.0, elapsed / spring_dur),
               glow_color=C_CYAN, bg=C_BG)
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
        sway = 0.04 * math.sin(t * 0.5)

        render(l_lid=LID + sway, r_lid=LID + sway,
               l_gaze_y=0.32, r_gaze_y=0.32,
               mouth="sad", mouth_morph=1.0,
               glow_color=C_CYAN_DIM, bg=C_BG,
               tears=True, tears_elapsed=elapsed)

        if time.time() >= blink_t:
            _blink(mouth="sad", glow_color=C_CYAN_DIM, bg=C_BG)
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
        pulse = abs(math.sin(frame_n * 0.28))
        if frame_n % 8 < 4:
            col = (0, int(140 * pulse), 255)   # PIL→екран: помаранч
            draw.text((W // 2 - 14, 8), "!!!", fill=col)

    while time.time() - t_start < duration:
        t += DT
        frame_n += 1
        elapsed = time.time() - t_start

        bg_r = min(55, int(55 * min(1.0, elapsed / 0.8)))
        bg   = (0, 0, bg_r)

        pulse = abs(math.sin(t * 3.8))
        lid_v = LID + 0.05 * pulse

        render(
            l_lid=lid_v, l_lid_angle=ANGLE,
            r_lid=lid_v, r_lid_angle=ANGLE,
            glow_color=C_GLOW_ANGRY,
            sclera_color=C_SCLERA_ANGRY,
            mouth="angry", mouth_morph=1.0,
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

    # Mouth offset анімація — smirk сунеться вправо і назад
    mouth_base_x  = 24
    mouth_target_x = 36
    mx_curr = float(mouth_base_x)

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
            col = (255, int(180 * f_alpha / 200), 0)   # PIL→екран: cyan
            draw.text((f_x, f_y), f_text, fill=col)
            f_alpha = max(0, f_alpha - 10)

    while time.time() - t_start < duration:
        t += DT
        elapsed = time.time() - t_start

        # Плавне зміщення рота вправо потім назад
        phase = (elapsed % 4.0) / 4.0
        if phase < 0.5:
            mx_curr = lerp(mouth_base_x, mouth_target_x, ease_inout(phase * 2))
        else:
            mx_curr = lerp(mouth_target_x, mouth_base_x, ease_inout((phase - 0.5) * 2))

        gx = 0.36 + 0.08 * math.sin(t * 0.7)
        gy = -0.22 + 0.06 * math.sin(t * 0.5)

        render(
            l_lid=L_LID, l_gaze_x=gx, l_gaze_y=gy,
            r_lid=R_LID, r_gaze_x=gx, r_gaze_y=gy + 0.13,
            mouth="thinking", mouth_morph=1.0,
            mouth_offset_x=int(mx_curr),
            glow_color=C_CYAN, bg=C_BG,
            extra_fn=thinking_extra
        )

        if time.time() >= blink_t:
            _blink(mouth="thinking", glow_color=C_CYAN,
                   bg=C_BG, r_lid_fixed=R_LID,
                   extra_fn=thinking_extra)
            blink_t = time.time() + random.uniform(2.0, 3.5)

        time.sleep(DT)


# ── 🗣️ TALKING ────────────────────────────────────────────────────────────────
def anim_talking(duration=3.0):
    t_start = time.time()
    t       = 0.0
    while time.time() - t_start < duration:
        t += DT
        open_f = max(0.0, 0.6 * abs(math.sin(t * 9.0)))
        render(mouth="surprised", mouth_open=open_f,
               mouth_morph=1.0, glow_color=C_CYAN, bg=C_BG)
        time.sleep(DT)


# ─────────────────────────────────────────────────────────────────────────────
# СЛОВНИК АНІМАЦІЙ ТА ТРИВАЛОСТЕЙ
# ─────────────────────────────────────────────────────────────────────────────
EMOTION_ANIMS = {
    "happy":     (anim_happy,     6.0),
    "surprised": (anim_surprised, 4.0),
    "sad":       (anim_sad,       6.0),
    "angry":     (anim_angry,     5.0),
    "thinking":  (anim_thinking,  6.0),
}


# ─────────────────────────────────────────────────────────────────────────────
# ГОЛОВНИЙ ЦИКЛ — випадковий порядок емоцій
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("🤖 AIKO eyes_v2 v3.0 запущено! Ctrl+C щоб зупинити")

    # Поява — розкриття очей
    for i in range(12):
        t = ease_inout(1.0 - i / 12)
        render(l_lid=t, r_lid=t, mouth="happy",
               mouth_morph=ease_inout(i / 12),
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.04)

    # Стартова емоція
    current_name  = "happy"
    current_state = STATE_HAPPY
    prev_state    = STATE_HAPPY

    while True:
        anim_fn, duration = EMOTION_ANIMS[current_name]
        print(f"🎭 Емоція: {current_name} ({duration:.1f}с)")
        anim_fn(duration=duration)

        # Вибираємо наступну — не ту саму що зараз
        candidates = [(n, s, w) for (n, s), w
                      in zip(ALL_EMOTIONS, EMOTION_WEIGHTS)
                      if n != current_name]
        names   = [c[0] for c in candidates]
        states  = [c[1] for c in candidates]
        weights = [c[2] for c in candidates]

        # Нормалізуємо ваги
        total = sum(weights)
        norm_weights = [w / total for w in weights]

        next_name  = random.choices(names, weights=norm_weights, k=1)[0]
        next_state = states[names.index(next_name)]

        print(f"   → перехід до: {next_name}")
        transition_to(current_state, next_state, duration=0.5)

        prev_state    = current_state
        current_name  = next_name
        current_state = next_state


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
