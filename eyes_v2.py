"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AIKO eyes_v2.py — процедурна анімація очей  v3.1                 ║
║           Стиль: neon cyan glow, чорний фон, мультяшний                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ЗМІНИ v3.1:                                                                ║
║  - Повіки: rounded_rectangle замість rectangle → нема чорних кутів         ║
║  - Surprised: без бров, без хвильки. Очі збільш → 1с → назад              ║
║  - Thinking: язик більший (r=22), яскравіший                               ║
║  - Thinking: формули великим шрифтом (size=32)                             ║
║  - Angry: рот rounded_rectangle з заокругленнями + зубки                  ║
║                                                                              ║
║  ⚠️  bgr=True на ILI9488: PIL (R,G,B) → екран (B,G,R)                     ║
║      Тобто PIL (0,0,55) → екран (55,0,0) = темно-червоний ✓               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw, ImageFont
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

# ── Шрифт для формул (thinking) ───────────────────────────────────────────────
try:
    FONT_FORMULA = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
except Exception:
    FONT_FORMULA = ImageFont.load_default(size=32)

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
BASE_EL_X = 118   # X лівого ока
BASE_ER_X = 362   # X правого ока
BASE_EY   = 148   # Y центр очей — ЄДИНА базова позиція для всіх емоцій

EW = 60    # напів-ширина
EH = 68    # напів-висота
ER = 26    # радіус заокруглення

# Рот
MX = W // 2   # 240
MY = 272
MW = 90

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
# GLOW — через RGBA шар (прозорий фон між шарами)
# ─────────────────────────────────────────────────────────────────────────────
def draw_glow_rgba(base_img, cx, cy, hw, hh, r, color, layers=5):
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for i in range(layers, 0, -1):
        expand = i * 5
        alpha  = int(200 * (1 - i / (layers + 1)))
        gc     = (color[0], color[1], color[2], alpha)
        gd.rounded_rectangle(
            (cx - hw - expand, cy - hh - expand,
             cx + hw + expand, cy + hh + expand),
            radius=r + expand // 2,
            outline=gc,
            width=3
        )
    base_img.alpha_composite(glow_layer)

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ ОДНОГО ОКА
# ─────────────────────────────────────────────────────────────────────────────
def draw_eye(base_img, cx, cy, hw, hh,
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
    draw_glow_rgba(base_img, cx, cy, hw, hh, r, glow_color)
    draw = ImageDraw.Draw(base_img)

    # 2. БІЛОК
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=r, fill=sclera_color
    )

    # 3. РАЙДУЖКА + ЗІНИЦЯ
    if not blink_line and lid_top < 0.95:
        iris_hw = int(hw * 0.50 * iris_scale)
        iris_hh = int(hh * 0.50 * iris_scale)
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

    # 4. ПОВІКА — rounded_rectangle щоб не було чорних кутів!
    if lid_top > 0.01 or abs(lid_angle) > 0.5:
        lid_px = int(hh * 2 * lid_top)

        if abs(lid_angle) < 0.5:
            # Горизонтальна повіка — заокруглений прямокутник зверху
            # Малюємо так: верхня частина з заокругленнями ока, низ рівний
            lid_y_top = cy - hh - 2
            lid_y_bot = cy - hh + lid_px
            # Rounded зверху — використовуємо rounded_rectangle з великим радіусом зверху
            draw.rounded_rectangle(
                (cx - hw - 2, lid_y_top,
                 cx + hw + 2, lid_y_bot + r),   # +r щоб низ перекривав без кута
                radius=r,
                fill=bg_color
            )
            if blink_line or lid_top > 0.85:
                line_y = lid_y_bot
                draw.line([(cx - hw + 6, line_y),
                           (cx + hw - 6, line_y)],
                          fill=glow_color, width=4)
        else:
            # Кутова повіка (angry) — трапеція з заокругленим верхом
            angle_rad   = math.radians(abs(lid_angle))
            half_tilt   = int(hw * math.tan(angle_rad))
            top_y       = cy - hh - 2
            left_bot_y  = cy - hh + lid_px - half_tilt
            right_bot_y = cy - hh + lid_px + half_tilt

            # Трапеція через polygon (кути повіки збігаються з контуром ока)
            draw.polygon(
                [(cx - hw - 2, top_y),
                 (cx + hw + 2, top_y),
                 (cx + hw + 2, right_bot_y + r),
                 (cx - hw - 2, left_bot_y + r)],
                fill=bg_color
            )

    # 5. КОНТУР поверх всього
    draw = ImageDraw.Draw(base_img)
    gc_outline = tuple(min(255, c + 30) for c in glow_color)
    draw.rounded_rectangle(
        (cx - hw, cy - hh, cx + hw, cy + hh),
        radius=r,
        outline=gc_outline,
        width=3
    )


# ─────────────────────────────────────────────────────────────────────────────
# РОТ
# ─────────────────────────────────────────────────────────────────────────────
def draw_mouth(draw, style="none", open_factor=0.0,
               morph=1.0, offset_x=0, glow_color=None):
    """
    style: none | happy | sad | surprised | angry | thinking
    morph: 0.0→1.0 — плавна поява (для transition)
    offset_x: зміщення X (для thinking smirk)
    """
    if style == "none":
        return
    if glow_color is None:
        glow_color = C_CYAN

    mx    = MX + int(offset_x)
    alpha = clamp(morph, 0.0, 1.0)

    # ── HAPPY ─────────────────────────────────────────────────────────────────
    if style == "happy":
        arc_h = int(26 * alpha)
        arc_w = int(MW * alpha)
        if arc_w < 4 or arc_h < 4:
            return
        gc = tuple(max(0, c // 5) for c in glow_color)
        draw.arc((mx - arc_w - 5, MY - arc_h - 5,
                  mx + arc_w + 5, MY + arc_h + 5),
                 start=10, end=170, fill=gc, width=14)
        draw.arc((mx - arc_w, MY - arc_h,
                  mx + arc_w, MY + arc_h),
                 start=10, end=170, fill=C_WHITE, width=10)

    # ── SAD ───────────────────────────────────────────────────────────────────
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
        gc = tuple(max(0, c // 5) for c in glow_color)
        draw.ellipse((mx - ow - 6, MY - oh - 6,
                      mx + ow + 6, MY + oh + 6), fill=gc)
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     fill=(15, 15, 15))
        draw.ellipse((mx - ow, MY - oh, mx + ow, MY + oh),
                     outline=C_WHITE, width=10)

    # ── ANGRY — rounded_rectangle + зубки ────────────────────────────────────
    elif style == "angry":
        rw = int(MW * 0.70 * alpha)   # напів-ширина прямокутника рота
        rh = int(28 * alpha)           # напів-висота
        rr = 10                        # радіус заокруглення кутів рота
        if rw < 6 or rh < 6:
            return

        # Glow навколо рота
        gc = tuple(max(0, c // 5) for c in C_GLOW_ANGRY)
        draw.rounded_rectangle(
            (mx - rw - 6, MY - rh - 6,
             mx + rw + 6, MY + rh + 6),
            radius=rr + 4,
            fill=gc
        )
        # Темний фон рота
        draw.rounded_rectangle(
            (mx - rw, MY - rh, mx + rw, MY + rh),
            radius=rr,
            fill=(10, 10, 10)
        )
        # Контур рота
        draw.rounded_rectangle(
            (mx - rw, MY - rh, mx + rw, MY + rh),
            radius=rr,
            outline=C_GLOW_ANGRY,
            width=10
        )
        # Зубки — верхній ряд прямокутників всередині рота
        tooth_count = 6
        tooth_w     = int((rw * 2 - 16) / tooth_count)
        tooth_h     = int(rh * 0.65)
        gap         = 3
        start_x     = mx - rw + 8
        for i in range(tooth_count):
            tx0 = start_x + i * tooth_w + gap
            tx1 = start_x + (i + 1) * tooth_w - gap
            ty0 = MY - rh + 5
            ty1 = MY - rh + 5 + tooth_h
            if tx1 > mx + rw - 8:
                break
            draw.rounded_rectangle(
                (tx0, ty0, tx1, ty1),
                radius=3,
                fill=C_TEETH
            )

    # ── THINKING — асиметрична smirk + язик ──────────────────────────────────
    elif style == "thinking":
        arc_w = int(MW * 0.60 * alpha)
        if arc_w < 4:
            return

        pts_count  = 24
        pts        = []
        left_drop  = int(20 * alpha)
        right_rise = int(14 * alpha)
        for i in range(pts_count + 1):
            fx = i / pts_count
            px = mx - arc_w + int(arc_w * 2 * fx)
            py = MY + int(lerp(left_drop, -right_rise, ease_inout(fx)))
            pts.append((px, py))

        if len(pts) >= 2:
            gc = tuple(max(0, c // 5) for c in glow_color)
            draw.line(pts, fill=gc, width=20)
            draw.line(pts, fill=C_WHITE, width=10)

        # Язик — більший, на правому кутику рота
        if alpha > 0.4:
            tongue_alpha = clamp((alpha - 0.4) / 0.6, 0.0, 1.0)
            tr = int(22 * tongue_alpha)    # великий радіус
            tx = mx + arc_w - 6
            ty = MY - int(8 * tongue_alpha)
            if tr > 4:
                # Основа язика
                draw.ellipse(
                    (tx - tr, ty - tr // 2,
                     tx + tr, ty + tr),
                    fill=C_TONGUE
                )
                # Роздвоєння зверху (два маленькі кола)
                split_r = tr // 2
                draw.ellipse(
                    (tx - split_r - 4, ty - tr // 2 - split_r // 2,
                     tx - split_r - 4 + split_r * 2, ty - tr // 2 + split_r),
                    fill=C_TONGUE
                )
                draw.ellipse(
                    (tx + 4, ty - tr // 2 - split_r // 2,
                     tx + 4 + split_r * 2, ty - tr // 2 + split_r),
                    fill=C_TONGUE
                )
                # Блик на язику
                draw.ellipse(
                    (tx - tr // 3, ty - tr // 4,
                     tx + tr // 3, ty + tr // 4),
                    fill=(220, 100, 255)
                )


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

    img = Image.new("RGBA", (W, H), bg + (255,))

    # Ліве oko
    draw_eye(img, BASE_EL_X, BASE_EY, hw, hh,
             lid_top=l_lid, lid_angle=-l_lid_angle,
             gaze_x=l_gaze_x, gaze_y=l_gaze_y,
             iris_scale=l_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=l_blink_line,
             bg_color=bg)

    # Праве oko
    draw_eye(img, BASE_ER_X, BASE_EY, hw, hh,
             lid_top=r_lid, lid_angle=r_lid_angle,
             gaze_x=r_gaze_x, gaze_y=r_gaze_y,
             iris_scale=r_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=r_blink_line,
             bg_color=bg)

    draw = ImageDraw.Draw(img)

    draw_mouth(draw, style=mouth,
               open_factor=mouth_open,
               morph=mouth_morph,
               offset_x=mouth_offset_x,
               glow_color=glow_color)

    if tears:
        draw_tears(draw, tears_elapsed)

    if extra_fn:
        extra_fn(draw)

    device.display(img.convert("RGB"))


# ─────────────────────────────────────────────────────────────────────────────
# МОРГАННЯ
# ─────────────────────────────────────────────────────────────────────────────
def _blink(mouth="none", glow_color=None, bg=None,
           r_lid_fixed=None, extra_fn=None,
           mouth_morph=1.0, mouth_offset_x=0):
    if glow_color is None: glow_color = C_CYAN
    if bg         is None: bg         = C_BG

    steps = 7
    for i in range(steps):
        t     = ease_inout(i / steps)
        r_lid = r_lid_fixed if r_lid_fixed is not None else t
        render(l_lid=t, r_lid=r_lid,
               mouth=mouth, mouth_morph=mouth_morph,
               mouth_offset_x=mouth_offset_x,
               glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8),
               r_blink_line=(r_lid > 0.8) if r_lid_fixed is None else False,
               extra_fn=extra_fn)
        time.sleep(0.013)

    r_lid = r_lid_fixed if r_lid_fixed is not None else 1.0
    render(l_lid=1.0, r_lid=r_lid,
           mouth=mouth, mouth_morph=mouth_morph,
           mouth_offset_x=mouth_offset_x,
           glow_color=glow_color, bg=bg,
           l_blink_line=True,
           r_blink_line=False if r_lid_fixed is not None else True,
           extra_fn=extra_fn)
    time.sleep(0.05)

    for i in range(steps):
        t     = ease_inout(1.0 - i / steps)
        r_lid = r_lid_fixed if r_lid_fixed is not None else t
        render(l_lid=t, r_lid=r_lid,
               mouth=mouth, mouth_morph=mouth_morph,
               mouth_offset_x=mouth_offset_x,
               glow_color=glow_color, bg=bg,
               l_blink_line=(t > 0.8),
               r_blink_line=False if r_lid_fixed is not None else (t > 0.8),
               extra_fn=extra_fn)
        time.sleep(0.013)


# ─────────────────────────────────────────────────────────────────────────────
# ПЛАВНИЙ ПЕРЕХІД (0.5 сек, очі + рот синхронно)
# ─────────────────────────────────────────────────────────────────────────────
_NUMERIC_KEYS = {
    "l_lid", "r_lid", "l_lid_angle", "r_lid_angle",
    "l_gaze_x", "l_gaze_y", "r_gaze_x", "r_gaze_y",
    "l_iris_scale", "r_iris_scale",
    "hw", "hh",
    "mouth_morph", "mouth_offset_x",
    "brow_lift",
}
_COLOR_KEYS = {"glow_color", "sclera_color", "bg"}


def transition_to(from_state, to_state, duration=0.5):
    steps      = max(4, int(duration / DT))
    from_mouth = from_state.get("mouth", "none")
    to_mouth   = to_state.get("mouth",   "none")
    same_mouth = (from_mouth == to_mouth)

    for i in range(steps + 1):
        t     = ease_inout(i / steps)
        frame = {}

        for key in set(list(from_state.keys()) + list(to_state.keys())):
            fv = from_state.get(key)
            tv = to_state.get(key)
            if fv is None and tv is None:
                continue
            if fv is None: fv = tv
            if tv is None: tv = fv

            if key in _NUMERIC_KEYS:
                frame[key] = lerp(fv, tv, t)
            elif key in _COLOR_KEYS:
                frame[key] = lerp_color(fv, tv, t)
            else:
                frame[key] = tv if t >= 0.5 else fv

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
# СТАНИ
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
    l_iris_scale=1.0, r_iris_scale=1.0,
    hw=EW, hh=EH,
    mouth="surprised", mouth_morph=1.0, mouth_offset_x=0,
    brows=False, brow_lift=0.0,           # ← брів немає!
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

ALL_EMOTIONS = [
    ("happy",     STATE_HAPPY),
    ("surprised", STATE_SURPRISED),
    ("sad",       STATE_SAD),
    ("angry",     STATE_ANGRY),
    ("thinking",  STATE_THINKING),
]
EMOTION_WEIGHTS = [0.30, 0.20, 0.20, 0.15, 0.15]


# ─────────────────────────────────────────────────────────────────────────────
# АНІМАЦІЇ ЕМОЦІЙ
# ─────────────────────────────────────────────────────────────────────────────

# ── 😊 HAPPY ──────────────────────────────────────────────────────────────────
def anim_happy(duration=6.0):
    t_start = time.time()
    t       = 0.0
    blink_t = time.time() + random.uniform(2.5, 4.5)
    gx = gy = tgx = tgy = 0.0
    gaze_t  = time.time() + random.uniform(1.5, 3.0)

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
    """
    Очі плавно збільшуються на 15% (0.8с),
    тримаються 1с, потім плавно повертаються (0.8с).
    Без бров, без хвильок.
    """
    t_start   = time.time()
    GROW_DUR  = 0.8    # час росту
    HOLD_DUR  = 1.0    # час утримання
    SHRINK_DUR = 0.8   # час повернення
    SCALE_MAX  = 1.15  # +15%

    while time.time() - t_start < duration:
        elapsed = time.time() - t_start

        if elapsed < GROW_DUR:
            # Збільшення
            s  = ease_inout(elapsed / GROW_DUR)
            sc = 1.0 + (SCALE_MAX - 1.0) * s
        elif elapsed < GROW_DUR + HOLD_DUR:
            # Утримання
            sc = SCALE_MAX
        elif elapsed < GROW_DUR + HOLD_DUR + SHRINK_DUR:
            # Повернення
            s  = ease_inout((elapsed - GROW_DUR - HOLD_DUR) / SHRINK_DUR)
            sc = SCALE_MAX - (SCALE_MAX - 1.0) * s
        else:
            # Тримаємо базовий розмір до кінця duration
            sc = 1.0

        hw = int(EW * sc)
        hh = int(EH * sc)

        render(hw=hw, hh=hh,
               l_iris_scale=1.0, r_iris_scale=1.0,
               mouth="surprised", mouth_morph=1.0,
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
            col = (0, int(140 * pulse), 255)
            draw.text((W // 2 - 14, 8), "!!!", fill=col,
                      font=FONT_FORMULA)

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

    mouth_base_x   = 24
    mouth_target_x = 40
    mx_curr        = float(mouth_base_x)

    FORMULAS = ["E=mc²", "π≈3.14", "42?", "∑n²", "∞", "AI>0", "f(x)?",
                "∂/∂x", "log₂n", "λ=?", "∇f", "ℏ/2"]
    f_text  = ""
    f_alpha = 0
    f_x = 300
    f_y = 28
    f_t = time.time() + 1.0

    def thinking_extra(draw):
        nonlocal f_text, f_alpha, f_x, f_y, f_t
        if time.time() >= f_t:
            f_text  = random.choice(FORMULAS)
            f_x     = random.randint(240, 420)
            f_y     = random.randint(10, 60)
            f_alpha = 255
            f_t     = time.time() + random.uniform(1.8, 3.2)
        if f_alpha > 0:
            # Cyan колір з плавним затуханням
            bright = int(255 * f_alpha / 255)
            col    = (bright, int(bright * 0.86), 0)   # PIL→екран: cyan
            draw.text((f_x, f_y), f_text, fill=col, font=FONT_FORMULA)
            f_alpha = max(0, f_alpha - 8)

    while time.time() - t_start < duration:
        t += DT
        elapsed = time.time() - t_start

        # Плавне зміщення smirk вправо-назад
        phase = (elapsed % 4.0) / 4.0
        if phase < 0.5:
            mx_curr = lerp(mouth_base_x, mouth_target_x,
                           ease_inout(phase * 2))
        else:
            mx_curr = lerp(mouth_target_x, mouth_base_x,
                           ease_inout((phase - 0.5) * 2))

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
                   mouth_offset_x=int(mx_curr),
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
# СЛОВНИК АНІМАЦІЙ
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
    print("🤖 AIKO eyes_v2 v3.1 запущено! Ctrl+C щоб зупинити")

    # Поява — розкриття очей
    for i in range(12):
        t = ease_inout(1.0 - i / 12)
        render(l_lid=t, r_lid=t, mouth="happy",
               mouth_morph=ease_inout(i / 12),
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.04)

    current_name  = "happy"
    current_state = STATE_HAPPY

    while True:
        anim_fn, dur = EMOTION_ANIMS[current_name]
        print(f"🎭 Емоція: {current_name} ({dur:.1f}с)")
        anim_fn(duration=dur)

        # Наступна емоція — випадково, не та сама
        candidates = [
            (n, s, w)
            for (n, s), w in zip(ALL_EMOTIONS, EMOTION_WEIGHTS)
            if n != current_name
        ]
        names   = [c[0] for c in candidates]
        states  = [c[1] for c in candidates]
        weights = [c[2] for c in candidates]
        total   = sum(weights)
        norm_w  = [w / total for w in weights]

        next_name  = random.choices(names, weights=norm_w, k=1)[0]
        next_state = states[names.index(next_name)]

        print(f"   → перехід до: {next_name}")
        transition_to(current_state, next_state, duration=0.5)

        current_name  = next_name
        current_state = next_state


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
