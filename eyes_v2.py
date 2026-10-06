"""
AIKO eyes_v2.py — процедурна анімація очей
Стиль: glowing neon, чорний фон, мультяшний, виразний
Автор: AIKO Robot Project
"""

from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw, ImageFilter
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

# ── Кольори (neon palette) ────────────────────────────────────────────────────
C_BG          = (0,   0,   0)
C_BG_ANGRY    = (60,  0,   0)
C_WHITE       = (255, 255, 255)
C_IRIS        = (30,  160, 255)       # синя райдужка
C_IRIS_ANGRY  = (255, 60,  0)         # помаранчева при злості
C_IRIS_SAD    = (80,  100, 220)       # тьмяніша при смутку
C_PUPIL       = (0,   0,   0)
C_GLOW        = (0,   100, 255)       # glow навколо ока
C_GLOW_ANGRY  = (255, 40,  0)
C_BROW        = (255, 255, 255)
C_MOUTH       = (255, 255, 255)
C_TEAR        = (100, 180, 255)
C_SHINE       = (255, 255, 255)       # відблиск

# ── Позиції очей ──────────────────────────────────────────────────────────────
EYE_L_X = 145    # центр лівого ока X
EYE_R_X = 335    # центр правого ока X
EYE_Y   = 148    # центр очей Y (трохи вище середини)
EYE_RX  = 72     # радіус ока по X (білок)
EYE_RY  = 80     # радіус ока по Y (білок)

# Брови
BROW_LX = EYE_L_X
BROW_RX = EYE_R_X
BROW_Y  = EYE_Y - EYE_RY - 18
BROW_W  = 90     # ширина брови
BROW_H  = 14     # товщина брови

# Рот
MOUTH_X = W // 2
MOUTH_Y = 272
MOUTH_W = 120    # півширина рота
MOUTH_H = 38     # висота дуги

# ─────────────────────────────────────────────────────────────────────────────
# СТАН ЕМОЦІЇ — всі параметри що плавно інтерполюються
# ─────────────────────────────────────────────────────────────────────────────
class EmoState:
    def __init__(self):
        # Очі
        self.eye_open     = 1.0    # 0=закрите, 1=відкрите
        self.eye_scale    = 1.0    # масштаб всього ока
        self.iris_r       = 0.55   # радіус райдужки відносно ока
        self.pupil_r      = 0.28   # радіус зіниці відносно ока
        # Зіниця — напрям погляду
        self.gaze_x       = 0.0    # -1..1  (ліво-право)
        self.gaze_y       = 0.0    # -1..1  (вгору-вниз)
        # Брови
        self.brow_y_off   = 0.0    # зміщення вгору(−) / вниз(+) px
        self.brow_angle_l = 0.0    # нахил лівої брови (градуси)
        self.brow_angle_r = 0.0    # нахил правої брови
        self.brow_squeeze = 0.0    # 0=рівні, 1=насуплені (зближення до центру)
        # Рот
        self.mouth_curve  = 1.0    # +1=усмішка, 0=рівний, -1=сумний
        self.mouth_open   = 0.0    # 0=закритий, 1=відкритий (здивування/говоріння)
        self.mouth_w      = 1.0    # масштаб ширини рота
        # Фон
        self.bg_r         = 0.0    # 0=чорний, 1=червоний (злість)
        # Кольори
        self.iris_color   = list(C_IRIS)
        self.glow_color   = list(C_GLOW)

# ── Пресети емоцій ────────────────────────────────────────────────────────────
def preset_happy():
    s = EmoState()
    s.eye_open     = 1.0
    s.eye_scale    = 1.05
    s.brow_y_off   = -8.0
    s.brow_angle_l = 5.0
    s.brow_angle_r = -5.0
    s.mouth_curve  = 1.0
    s.mouth_w      = 1.1
    s.iris_color   = list(C_IRIS)
    s.glow_color   = list(C_GLOW)
    return s

def preset_blink():
    s = preset_happy()
    s.eye_open = 0.0
    return s

def preset_surprised():
    s = EmoState()
    s.eye_open     = 1.0
    s.eye_scale    = 1.18
    s.iris_r       = 0.48
    s.pupil_r      = 0.22
    s.brow_y_off   = -22.0
    s.brow_angle_l = 10.0
    s.brow_angle_r = -10.0
    s.mouth_curve  = 0.0
    s.mouth_open   = 0.85
    s.mouth_w      = 0.7
    s.iris_color   = list(C_IRIS)
    s.glow_color   = [60, 180, 255]
    return s

def preset_sad():
    s = EmoState()
    s.eye_open     = 0.75
    s.eye_scale    = 0.95
    s.brow_y_off   = 10.0
    s.brow_angle_l = -12.0
    s.brow_angle_r = 12.0
    s.brow_squeeze = 0.3
    s.mouth_curve  = -1.0
    s.mouth_w      = 0.85
    s.iris_color   = list(C_IRIS_SAD)
    s.glow_color   = [40, 60, 180]
    return s

def preset_angry():
    s = EmoState()
    s.eye_open     = 0.7
    s.eye_scale    = 1.0
    s.brow_y_off   = 8.0
    s.brow_angle_l = -20.0
    s.brow_angle_r = 20.0
    s.brow_squeeze = 0.6
    s.mouth_curve  = -0.5
    s.mouth_w      = 0.9
    s.bg_r         = 1.0
    s.iris_color   = list(C_IRIS_ANGRY)
    s.glow_color   = list(C_GLOW_ANGRY)
    return s

def preset_thinking():
    s = EmoState()
    s.eye_open     = 0.85
    s.eye_scale    = 0.98
    s.gaze_x       = 0.4
    s.gaze_y       = -0.3
    s.brow_y_off   = -5.0
    s.brow_angle_l = 0.0
    s.brow_angle_r = -15.0
    s.mouth_curve  = 0.2
    s.mouth_w      = 0.8
    s.iris_color   = [60, 180, 255]
    s.glow_color   = [40, 140, 220]
    return s

# ── Лінійна інтерполяція між двома станами ───────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_state(s_from, s_to, t):
    s = EmoState()
    s.eye_open     = lerp(s_from.eye_open,     s_to.eye_open,     t)
    s.eye_scale    = lerp(s_from.eye_scale,    s_to.eye_scale,    t)
    s.iris_r       = lerp(s_from.iris_r,       s_to.iris_r,       t)
    s.pupil_r      = lerp(s_from.pupil_r,      s_to.pupil_r,      t)
    s.gaze_x       = lerp(s_from.gaze_x,       s_to.gaze_x,       t)
    s.gaze_y       = lerp(s_from.gaze_y,       s_to.gaze_y,       t)
    s.brow_y_off   = lerp(s_from.brow_y_off,   s_to.brow_y_off,   t)
    s.brow_angle_l = lerp(s_from.brow_angle_l, s_to.brow_angle_l, t)
    s.brow_angle_r = lerp(s_from.brow_angle_r, s_to.brow_angle_r, t)
    s.brow_squeeze = lerp(s_from.brow_squeeze, s_to.brow_squeeze, t)
    s.mouth_curve  = lerp(s_from.mouth_curve,  s_to.mouth_curve,  t)
    s.mouth_open   = lerp(s_from.mouth_open,   s_to.mouth_open,   t)
    s.mouth_w      = lerp(s_from.mouth_w,      s_to.mouth_w,      t)
    s.bg_r         = lerp(s_from.bg_r,         s_to.bg_r,         t)
    s.iris_color   = [int(lerp(s_from.iris_color[i], s_to.iris_color[i], t)) for i in range(3)]
    s.glow_color   = [int(lerp(s_from.glow_color[i], s_to.glow_color[i], t)) for i in range(3)]
    return s

# ── Малювання одного ока ──────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, rx, ry, state, side=1):
    """
    cx, cy   — центр ока
    rx, ry   — радіус білка
    state    — EmoState
    side     — +1 правий, -1 лівий (для симетрії погляду)
    """
    eye_open = state.eye_open
    sc       = state.eye_scale
    irx      = rx * sc
    iry      = ry * sc

    # ── Glow навколо ока (розмитий великий еліпс) ──────────────────────────
    glow_col = tuple(state.glow_color)
    glow_expand = 18
    for gi in range(3):
        alpha_factor = [0.25, 0.15, 0.08][gi]
        ge = glow_expand * (gi + 1)
        gc = tuple(int(c * alpha_factor) for c in glow_col)
        draw.ellipse(
            (cx - irx - ge, cy - iry - ge, cx + irx + ge, cy + iry + ge),
            fill=gc
        )

    # ── Білок ──────────────────────────────────────────────────────────────
    draw.ellipse(
        (cx - irx, cy - iry, cx + irx, cy + iry),
        fill=C_WHITE,
        outline=C_WHITE,
        width=2
    )

    # ── Райдужка ───────────────────────────────────────────────────────────
    iris_rx = irx * state.iris_r
    iris_ry = iry * state.iris_r
    # Погляд — зміщуємо райдужку
    gaze_off_x = (irx - iris_rx) * 0.6 * state.gaze_x
    gaze_off_y = (iry - iris_ry) * 0.6 * state.gaze_y
    icx = cx + gaze_off_x
    icy = cy + gaze_off_y

    iris_col = tuple(state.iris_color)
    # Зовнішній обідок райдужки (темніший)
    dark_iris = tuple(max(0, c - 60) for c in iris_col)
    draw.ellipse(
        (icx - iris_rx, icy - iris_ry, icx + iris_rx, icy + iris_ry),
        fill=dark_iris
    )
    # Внутрішня частина (яскравіша)
    inner_rx = iris_rx * 0.72
    inner_ry = iris_ry * 0.72
    draw.ellipse(
        (icx - inner_rx, icy - inner_ry, icx + inner_rx, icy + inner_ry),
        fill=iris_col
    )

    # ── Зіниця ─────────────────────────────────────────────────────────────
    pup_rx = irx * state.pupil_r
    pup_ry = iry * state.pupil_r
    draw.ellipse(
        (icx - pup_rx, icy - pup_ry, icx + pup_rx, icy + pup_ry),
        fill=C_PUPIL
    )

    # ── Відблиск (shine) ────────────────────────────────────────────────────
    sh_off_x = -iris_rx * 0.38
    sh_off_y = -iris_ry * 0.38
    sh_rx = iris_rx * 0.22
    sh_ry = iris_ry * 0.22
    draw.ellipse(
        (icx + sh_off_x - sh_rx, icy + sh_off_y - sh_ry,
         icx + sh_off_x + sh_rx, icy + sh_off_y + sh_ry),
        fill=C_SHINE
    )
    # Маленький другий відблиск
    sh2_rx = sh_rx * 0.45
    sh2_ry = sh_ry * 0.45
    draw.ellipse(
        (icx + sh_off_x * 0.3 + iris_rx*0.18 - sh2_rx,
         icy + sh_off_y * 0.3 + iris_ry*0.18 - sh2_ry,
         icx + sh_off_x * 0.3 + iris_rx*0.18 + sh2_rx,
         icy + sh_off_y * 0.3 + iris_ry*0.18 + sh2_ry),
        fill=(220, 240, 255)
    )

    # ── Повіка (моргання) ──────────────────────────────────────────────────
    # eye_open=1 → повіка вгорі (невидима), eye_open=0 → повіка закриває все
    lid_h = iry * 2 * (1.0 - eye_open)
    if lid_h > 1:
        # Верхня повіка опускається зверху
        lid_top    = cy - iry
        lid_bottom = lid_top + lid_h + 4
        draw.ellipse(
            (cx - irx - 2, lid_top - 2, cx + irx + 2, lid_top + iry * 2 + 4),
            fill=(0, 0, 0)
        )
        # Лінія повіки
        draw.arc(
            (cx - irx, cy - iry, cx + irx, cy + iry),
            start=200, end=340,
            fill=tuple(int(c * 0.6) for c in glow_col),
            width=3
        )

    # ── Обводка білка (neon outline) ───────────────────────────────────────
    outline_col = tuple(min(255, c + 40) for c in glow_col)
    draw.ellipse(
        (cx - irx, cy - iry, cx + irx, cy + iry),
        outline=outline_col,
        width=3
    )

# ── Малювання брови ───────────────────────────────────────────────────────────
def draw_brow(draw, cx, cy, state, side=1):
    """
    side: +1 = права брова, -1 = ліва брова
    """
    angle = state.brow_angle_r if side > 0 else state.brow_angle_l
    squeeze_off = state.brow_squeeze * 30 * side * (-1)
    bx = cx + squeeze_off
    by = cy + state.brow_y_off

    bw = BROW_W * 0.5
    bh = BROW_H

    # Кут нахилу
    angle_rad = math.radians(angle)
    dx = bw * math.cos(angle_rad)
    dy = bw * math.sin(angle_rad)

    x0 = bx - dx
    y0 = by - dy
    x1 = bx + dx
    y1 = by + dy

    # Товста лінія = брова
    glow_col = tuple(state.glow_color)
    # Glow брови
    for thickness, alpha in [(10, 0.15), (7, 0.3), (5, 1.0)]:
        col = tuple(int(c * alpha) for c in C_WHITE) if alpha == 1.0 else tuple(int(c * alpha) for c in glow_col)
        draw.line([(x0, y0), (x1, y1)], fill=col, width=thickness)

    # Закруглені кінці (кружечки)
    cap_r = bh * 0.4
    draw.ellipse((x0 - cap_r, y0 - cap_r, x0 + cap_r, y0 + cap_r), fill=C_WHITE)
    draw.ellipse((x1 - cap_r, y1 - cap_r, x1 + cap_r, y1 + cap_r), fill=C_WHITE)

# ── Малювання рота ────────────────────────────────────────────────────────────
def draw_mouth(draw, state):
    mx = MOUTH_X
    my = MOUTH_Y
    mw = int(MOUTH_W * state.mouth_w)
    curve = state.mouth_curve   # +1 усмішка, -1 сумний
    open_h = int(MOUTH_H * state.mouth_open)

    glow_col = tuple(state.glow_color)

    if state.mouth_open > 0.1:
        # Відкритий рот (овал — здивування/говоріння)
        ow = int(mw * 0.55)
        oh = int(MOUTH_H * 0.7 + open_h)
        # Glow
        for ge, ga in [(8, 0.12), (4, 0.25)]:
            gc = tuple(int(c * ga) for c in glow_col)
            draw.ellipse((mx - ow - ge, my - oh - ge, mx + ow + ge, my + oh + ge), fill=gc)
        # Внутрішній темний
        draw.ellipse((mx - ow, my - oh, mx + ow, my + oh), fill=(20, 20, 20))
        # Обводка
        draw.ellipse((mx - ow, my - oh, mx + ow, my + oh), outline=C_WHITE, width=4)
    else:
        # Закритий рот — дуга
        # curve > 0 → усмішка (дуга вниз), curve < 0 → сумний (дуга вгору)
        arc_h = int(abs(curve) * MOUTH_H)
        bbox_y_top = my - arc_h
        bbox_y_bot = my + arc_h

        if curve >= 0:
            # Усмішка — дуга відкрита вниз
            start_a, end_a = 0, 180
        else:
            # Сумний — дуга відкрита вгору
            start_a, end_a = 180, 360

        # Glow рота
        for ge, ga in [(8, 0.12), (4, 0.25)]:
            gc = tuple(int(c * ga) for c in glow_col)
            draw.arc(
                (mx - mw - ge, bbox_y_top - ge, mx + mw + ge, bbox_y_bot + ge),
                start=start_a, end=end_a, fill=gc, width=6
            )
        # Основна лінія
        draw.arc(
            (mx - mw, bbox_y_top, mx + mw, bbox_y_bot),
            start=start_a, end=end_a,
            fill=C_WHITE, width=5
        )
        # Закруглені кінці рота
        cap_r = 5
        # Ліва точка
        lx = mx - mw
        ly = my + (arc_h if curve >= 0 else -arc_h)
        draw.ellipse((lx - cap_r, ly - cap_r, lx + cap_r, ly + cap_r), fill=C_WHITE)
        # Права точка
        rx_ = mx + mw
        ry_ = my + (arc_h if curve >= 0 else -arc_h)
        draw.ellipse((rx_ - cap_r, ry_ - cap_r, rx_ + cap_r, ry_ + cap_r), fill=C_WHITE)

# ── Малювання сльози ──────────────────────────────────────────────────────────
def draw_tears(draw, elapsed):
    for base_x, offset in [(EYE_L_X - 15, 0), (EYE_R_X + 15, 40)]:
        drop_y = EYE_Y + EYE_RY + int((elapsed * 55 + offset) % 110)
        # Форма краплі
        draw.ellipse(
            (base_x - 7, drop_y - 14, base_x + 7, drop_y + 7),
            fill=C_TEAR
        )
        # Shine на сльозі
        draw.ellipse(
            (base_x - 3, drop_y - 10, base_x, drop_y - 5),
            fill=(200, 230, 255)
        )

# ── Рендер повного кадру ──────────────────────────────────────────────────────
def render_frame(state, extra_fn=None):
    # Фон
    bg_r = int(C_BG_ANGRY[0] * state.bg_r)
    bg = (bg_r, 0, 0)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    sc = state.eye_scale
    # Ліве oko
    draw_eye(draw,
             int(EYE_L_X), int(EYE_Y),
             int(EYE_RX * sc), int(EYE_RY * sc),
             state, side=-1)
    # Праве oko
    draw_eye(draw,
             int(EYE_R_X), int(EYE_Y),
             int(EYE_RX * sc), int(EYE_RY * sc),
             state, side=1)

    # Брови
    draw_brow(draw, EYE_L_X, BROW_Y, state, side=-1)
    draw_brow(draw, EYE_R_X, BROW_Y, state, side=1)

    # Рот
    draw_mouth(draw, state)

    # Додаткові ефекти (сльози, вогники, тощо)
    if extra_fn:
        extra_fn(draw, img)

    device.display(img)
    return img

# ─────────────────────────────────────────────────────────────────────────────
# ПЛАВНИЙ ПЕРЕХІД між двома пресетами
# ─────────────────────────────────────────────────────────────────────────────
def transition(s_from, s_to, duration=0.5):
    steps = max(4, int(duration / DT))
    for i in range(steps + 1):
        t = i / steps
        # Ease in-out (плавне прискорення і гальмування)
        t_ease = t * t * (3 - 2 * t)
        s = lerp_state(s_from, s_to, t_ease)
        render_frame(s)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# АНІМАЦІЇ ЕМОЦІЙ
# ─────────────────────────────────────────────────────────────────────────────

# 😊 HAPPY — дихання + дрібний рух очей + автоморгання
def anim_happy(duration=6.0):
    base = preset_happy()
    t_start = time.time()
    t = 0.0
    blink_timer = time.time() + random.uniform(2.5, 4.5)

    # Випадковий рух зіниці (ніби дивиться по сторонах)
    target_gx = 0.0
    target_gy = 0.0
    gaze_timer = time.time() + random.uniform(1.5, 3.0)

    while time.time() - t_start < duration:
        t += DT

        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)

        # Дихання — легкий пульс масштабу
        breath = 0.012 * math.sin(t * 1.4)
        s.eye_scale = base.eye_scale + breath

        # Легкий рух вгору-вниз (ніби живе)
        s.brow_y_off = base.brow_y_off + 2.5 * math.sin(t * 1.1)

        # Плавний рух зіниці до цілі
        s.gaze_x = lerp(s.gaze_x, target_gx, 0.08)
        s.gaze_y = lerp(s.gaze_y, target_gy, 0.08)

        # Час нового погляду
        if time.time() >= gaze_timer:
            target_gx = random.uniform(-0.5, 0.5)
            target_gy = random.uniform(-0.3, 0.3)
            gaze_timer = time.time() + random.uniform(1.5, 3.0)

        render_frame(s)

        # Моргання
        if time.time() >= blink_timer:
            _do_blink(base)
            blink_timer = time.time() + random.uniform(2.5, 4.5)

        time.sleep(DT)

# Моргання (плавне через lerp_state)
def _do_blink(base_state):
    closed = EmoState()
    closed.__dict__.update(base_state.__dict__.copy())
    closed.iris_color = list(base_state.iris_color)
    closed.glow_color = list(base_state.glow_color)
    closed.eye_open = 0.0

    # Закрити
    steps = 6
    for i in range(steps):
        t = i / steps
        s = lerp_state(base_state, closed, t)
        render_frame(s)
        time.sleep(0.016)
    # Пауза із закритими
    time.sleep(0.06)
    # Відкрити
    for i in range(steps):
        t = i / steps
        s = lerp_state(closed, base_state, t)
        render_frame(s)
        time.sleep(0.016)

# 😲 SURPRISED — стрибок + великі очі + відкритий рот
def anim_surprised(duration=4.0):
    base = preset_surprised()
    t_start = time.time()
    t = 0.0

    # Пружинний ефект на початку
    spring_dur = 0.6
    while time.time() - t_start < duration:
        elapsed = time.time() - t_start
        t += DT

        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)

        if elapsed < spring_dur:
            # Пружина — overshoot
            spring_t = elapsed / spring_dur
            overshoot = 1.0 + 0.12 * math.exp(-spring_t * 4) * math.cos(spring_t * 18)
            s.eye_scale = base.eye_scale * overshoot
            s.brow_y_off = base.brow_y_off * (1 + 0.3 * overshoot)
        else:
            # Легке дихання
            s.eye_scale = base.eye_scale + 0.008 * math.sin(t * 2.5)
            # Очі трохи рухаються (ніби дивляться навколо здивовано)
            s.gaze_x = 0.25 * math.sin(t * 1.3)
            s.gaze_y = -0.15 * abs(math.sin(t * 0.9))

        render_frame(s)
        time.sleep(DT)

# 😢 SAD — примружені очі + сльози + сумний рот
def anim_sad(duration=6.0):
    base = preset_sad()
    t_start = time.time()
    t = 0.0
    blink_timer = time.time() + random.uniform(3.0, 5.0)

    def draw_tears_extra(draw, img):
        elapsed = time.time() - t_start
        draw_tears(draw, elapsed)

    while time.time() - t_start < duration:
        t += DT

        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)

        # Повільне хитання вниз — ніби важко
        s.brow_y_off = base.brow_y_off + 3.0 * math.sin(t * 0.6)
        # Зіниця дивиться трохи вниз
        s.gaze_y = 0.3 + 0.1 * math.sin(t * 0.5)

        render_frame(s, extra_fn=draw_tears_extra)

        if time.time() >= blink_timer:
            _do_blink(base)
            blink_timer = time.time() + random.uniform(3.0, 5.0)

        time.sleep(DT)

# 😠 ANGRY — тремтіння + насуплені брови + червоний фон
def anim_angry(duration=5.0):
    base = preset_angry()
    t_start = time.time()
    t = 0.0
    frame_n = 0

    def angry_extra(draw, img):
        # !!! пульсуючий
        if frame_n % 8 < 4:
            pulse = abs(math.sin(frame_n * 0.25))
            col = (255, int(200 * pulse), 0)
            draw.text((W//2 - 14, 12), "!!!", fill=col)

    while time.time() - t_start < duration:
        t += DT
        frame_n += 1

        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)

        # Тремтіння
        shake_amp = 7.0
        shake_x = random.uniform(-shake_amp, shake_amp)
        shake_y = random.uniform(-shake_amp * 0.5, shake_amp * 0.5)

        # Пульс розміру ока
        pulse = abs(math.sin(t * 3.5))
        s.eye_scale = base.eye_scale + 0.04 * pulse

        # Брови ще більше насуплені під час пульсу
        s.brow_y_off = base.brow_y_off + 4.0 * pulse
        s.brow_squeeze = base.brow_squeeze + 0.15 * pulse

        # Рендер зі зміщенням (тремтіння)
        bg_r = int(C_BG_ANGRY[0] * s.bg_r)
        bg = (bg_r, 0, 0)
        img = Image.new("RGB", (W, H), bg)
        draw = ImageDraw.Draw(img)

        off_lx = int(EYE_L_X + shake_x)
        off_rx = int(EYE_R_X + shake_x)
        off_y  = int(EYE_Y + shake_y)
        sc = s.eye_scale

        draw_eye(draw, off_lx, off_y, int(EYE_RX * sc), int(EYE_RY * sc), s, side=-1)
        draw_eye(draw, off_rx, off_y, int(EYE_RX * sc), int(EYE_RY * sc), s, side=1)
        draw_brow(draw, off_lx, BROW_Y + shake_y + s.brow_y_off - base.brow_y_off,
                  s, side=-1)
        draw_brow(draw, off_rx, BROW_Y + shake_y + s.brow_y_off - base.brow_y_off,
                  s, side=1)
        draw_mouth(draw, s)
        angry_extra(draw, img)

        device.display(img)
        time.sleep(DT)

# 🤔 THINKING — погляд вгору-вбік + одна брова вгору
def anim_thinking(duration=6.0):
    base = preset_thinking()
    t_start = time.time()
    t = 0.0
    blink_timer = time.time() + random.uniform(2.0, 3.5)

    # Формули що з'являються
    FORMULAS = ["E=mc²", "π≈3.14", "42?", "∑n²", "∞", "AI>0", "f(x)?"]
    formula_text  = ""
    formula_alpha = 0
    formula_x     = 300
    formula_y     = 30
    formula_timer = time.time() + 1.0

    def thinking_extra(draw, img):
        nonlocal formula_text, formula_alpha, formula_x, formula_y, formula_timer
        if time.time() >= formula_timer:
            formula_text  = random.choice(FORMULAS)
            formula_x     = random.randint(280, 400)
            formula_y     = random.randint(15, 70)
            formula_alpha = 220
            formula_timer = time.time() + random.uniform(2.0, 3.5)
        if formula_alpha > 0:
            col = (0, int(180 * formula_alpha / 220), int(255 * formula_alpha / 220))
            draw.text((formula_x, formula_y), formula_text, fill=col)
            formula_alpha = max(0, formula_alpha - 12)

    while time.time() - t_start < duration:
        t += DT

        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)

        # Повільне хитання погляду вгору-вбік
        s.gaze_x = base.gaze_x + 0.15 * math.sin(t * 0.7)
        s.gaze_y = base.gaze_y + 0.1  * math.sin(t * 0.5)
        # Права брова «задумливо» рухається
        s.brow_angle_r = base.brow_angle_r + 5.0 * math.sin(t * 0.8)

        render_frame(s, extra_fn=thinking_extra)

        if time.time() >= blink_timer:
            _do_blink(base)
            blink_timer = time.time() + random.uniform(2.0, 3.5)

        time.sleep(DT)

# ── ГОВОРІННЯ — анімація рота (виклик ззовні) ────────────────────────────────
def anim_talking(base_preset_fn, duration=3.0):
    """Анімує рот ніби говорить. base_preset_fn — функція пресету (напр. preset_happy)"""
    base = base_preset_fn()
    t_start = time.time()
    t = 0.0
    while time.time() - t_start < duration:
        t += DT
        s = EmoState()
        s.__dict__.update(base.__dict__.copy())
        s.iris_color = list(base.iris_color)
        s.glow_color = list(base.glow_color)
        # Рот відкривається і закривається швидко
        s.mouth_open = max(0.0, 0.5 * abs(math.sin(t * 8.0)))
        render_frame(s)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("🤖 AIKO eyes_v2 запущено! Ctrl+C щоб зупинити")

    # Поява з нуля — eye_open 0→1
    closed = EmoState()
    closed.eye_open = 0.0
    transition(closed, preset_happy(), duration=0.8)

    current = preset_happy()

    while True:
        print("😊 Happy...")
        anim_happy(duration=6.0)

        print("→ 😲 Surprised!")
        transition(current, preset_surprised(), duration=0.4)
        current = preset_surprised()
        anim_surprised(duration=4.0)

        print("→ 😢 Sad...")
        transition(current, preset_sad(), duration=0.7)
        current = preset_sad()
        anim_sad(duration=6.0)

        print("→ 😠 Angry!")
        transition(current, preset_angry(), duration=0.35)
        current = preset_angry()
        anim_angry(duration=5.0)

        print("→ 🤔 Thinking...")
        transition(current, preset_thinking(), duration=0.5)
        current = preset_thinking()
        anim_thinking(duration=6.0)

        print("→ 😊 Happy знову!")
        transition(current, preset_happy(), duration=0.5)
        current = preset_happy()

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        black = Image.new("RGB", (W, H), (0, 0, 0))
        device.display(black)
