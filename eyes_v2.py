"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AIKO eyes_v2.py — процедурна анімація очей                       ║
║           Стиль: neon cyan glow, чорний фон, мультяшний                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  РЕФЕРЕНС ДИЗАЙНУ (з PNG фото смайликів):                                  ║
║                                                                              ║
║  ФОРМА ОКА: rounded rectangle (НЕ еліпс!) ~160x200px, radius~45px          ║
║  GLOW: cyan (0,220,255) по контуру, angry = помаранч (255,80,0)            ║
║                                                                              ║
║  happy:     білок білий, райдужка синя, зіниця чорна, відблиск,            ║
║             рот = маленька БІЛА дуга внизу. Брів НЕМАЄ.                    ║
║                                                                              ║
║  blink:     контур+glow ЗАЛИШАЄТЬСЯ, всередині CYAN горизонт. лінія        ║
║                                                                              ║
║  surprised: очі такі самі але райдужка/зіниця МЕНШІ (широко відкриті),     ║
║             над очима БІЛІ ДУГИ (брови). Рота НЕМАЄ.                       ║
║                                                                              ║
║  sad:       верхня повіка опущена ~40% (чорна смуга зверху),               ║
║             райдужка/зіниця зміщені ВНИЗ, рот = маленька CYAN              ║
║             перевернута дуга. Брів НЕМАЄ.                                   ║
║                                                                              ║
║  angry:     білок РОЖЕВИЙ (255,200,200), повіка ПІД КУТОМ (трапеція!),     ║
║             внутр. край (до носа) нижче — зовн. вище. Glow ЧЕРВОНИЙ.      ║
║             Рота і брів НЕМАЄ. Ефект злості = тільки повіки!               ║
║                                                                              ║
║  thinking:  ліве oko = відкрите (як happy),                                ║
║             праве oko = повіка ~50% (примружене). Рота/брів НЕМАЄ.         ║
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

# ── Кольори ───────────────────────────────────────────────────────────────────
C_BG           = (0,   0,   0)
C_CYAN         = (0,   220, 255)   # основний glow
C_CYAN_DIM     = (0,   140, 180)   # тьмяний (sad)
C_GLOW_ANGRY   = (255, 80,  0)     # glow злості
C_WHITE        = (255, 255, 255)
C_SCLERA       = (255, 255, 255)   # білок нормальний
C_SCLERA_ANGRY = (255, 200, 200)   # білок рожевий (злість)
C_IRIS         = (30,  140, 255)   # райдужка синя
C_PUPIL        = (0,   0,   0)
C_SHINE        = (255, 255, 255)   # відблиск
C_TEAR         = (0,   200, 255)   # сльоза cyan

# ── Геометрія очей ────────────────────────────────────────────────────────────
# Центри очей
EL_X, ER_X = 138, 342   # X лівого і правого
EY          = 152        # Y центр (трохи вище середини)
# Розмір rounded rect ока (половини)
EW = 100   # напів-ширина
EH = 110   # напів-висота
ER = 44    # радіус заокруглення кутів

# Рот
MX = W // 2   # X центру рота
MY = 282       # Y рота
MW = 72        # напів-ширина рота

# Брови (surprised)
BROW_H = 22    # висота над оком

# ─────────────────────────────────────────────────────────────────────────────
# ДОПОМІЖНІ ФУНКЦІЇ
# ─────────────────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def ease_inout(t):
    return t * t * (3 - 2 * t)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ── Малювання rounded rectangle з glow ───────────────────────────────────────
def draw_rrect(draw, cx, cy, hw, hh, r, fill=None, outline=None, width=3):
    """Заокруглений прямокутник з центром (cx, cy), напів-розміром (hw, hh)"""
    x0, y0 = cx - hw, cy - hh
    x1, y1 = cx + hw, cy + hh
    draw.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=fill, outline=outline, width=width)

def draw_glow(draw, cx, cy, hw, hh, r, color, layers=4):
    """Neon glow навколо rounded rect — кілька шарів що розширюються"""
    for i in range(layers, 0, -1):
        expand = i * 5
        alpha  = int(60 / i)
        gc = tuple(clamp(c, 0, 255) for c in color[:3])
        # Темніємо по шарах
        dim = layers - i + 1
        gc2 = tuple(max(0, c // dim) for c in gc)
        draw.rounded_rectangle(
            (cx - hw - expand, cy - hh - expand,
             cx + hw + expand, cy + hh + expand),
            radius=r + expand // 2,
            outline=gc2,
            width=2
        )

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ ОДНОГО ОКА
# ─────────────────────────────────────────────────────────────────────────────
def draw_eye(draw, cx, cy, hw, hh,
             lid_top=0.0,      # 0.0=відкрите, 1.0=закрите (частка висоти)
             lid_angle=0.0,    # кут повіки (для злості), градуси
             gaze_x=0.0,       # -1..1
             gaze_y=0.0,       # -1..1
             iris_scale=1.0,   # масштаб райдужки
             glow_color=None,
             sclera_color=None,
             blink_line=False): # True = cyan лінія замість зіниці (blink)
    """
    Малює одне oko як rounded rectangle зі всіма деталями.
    lid_top: 0=повністю відкрите, 1=повністю закрите
    lid_angle: кут нахилу повіки (для angry)
    """
    if glow_color  is None: glow_color  = C_CYAN
    if sclera_color is None: sclera_color = C_SCLERA

    r = ER  # радіус заокруглення

    # 1. GLOW
    draw_glow(draw, cx, cy, hw, hh, r, glow_color)

    # 2. БІЛОК
    draw_rrect(draw, cx, cy, hw, hh, r, fill=sclera_color)

    # 3. РАЙДУЖКА + ЗІНИЦЯ (якщо не blink_line)
    if not blink_line:
        iris_hw = int(hw * 0.52 * iris_scale)
        iris_hh = int(hh * 0.52 * iris_scale)
        # Зміщення погляду (обмежуємо щоб не виходив за білок)
        max_gx = hw - iris_hw - 4
        max_gy = hh - iris_hh - 4
        off_x = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
        off_y = int(clamp(gaze_y * max_gy, -max_gy, max_gy))
        icx, icy = cx + off_x, cy + off_y

        # Зовнішня темна частина райдужки
        dark = tuple(max(0, c - 70) for c in C_IRIS)
        draw.ellipse((icx - iris_hw, icy - iris_hh,
                      icx + iris_hw, icy + iris_hh), fill=dark)
        # Яскрава внутрішня
        in_hw = int(iris_hw * 0.70)
        in_hh = int(iris_hh * 0.70)
        draw.ellipse((icx - in_hw, icy - in_hh,
                      icx + in_hw, icy + in_hh), fill=C_IRIS)
        # Зіниця
        p_hw = int(iris_hw * 0.48)
        p_hh = int(iris_hh * 0.48)
        draw.ellipse((icx - p_hw, icy - p_hh,
                      icx + p_hw, icy + p_hh), fill=C_PUPIL)
        # Відблиск (верх-ліво від зіниці)
        sh_x = icx - int(iris_hw * 0.32)
        sh_y = icy - int(iris_hh * 0.32)
        sh_r = max(4, int(iris_hw * 0.18))
        draw.ellipse((sh_x - sh_r, sh_y - sh_r,
                      sh_x + sh_r, sh_y + sh_r), fill=C_SHINE)
        # Маленький другий відблиск
        sh2_r = max(2, sh_r // 2)
        draw.ellipse((sh_x + sh_r, sh_y + sh_r // 2 - sh2_r,
                      sh_x + sh_r + sh2_r * 2, sh_y + sh_r // 2 + sh2_r),
                     fill=(200, 230, 255))

    # 4. ПОВІКА (clip зверху)
    if lid_top > 0.01 or lid_angle != 0.0:
        lid_px = int(hh * 2 * lid_top)   # скільки пікселів перекриває

        if abs(lid_angle) < 0.5:
            # Горизонтальна повіка (happy/sad/thinking blink)
            # Малюємо чорний прямокутник зверху
            draw.rectangle(
                (cx - hw - 2, cy - hh - 2,
                 cx + hw + 2, cy - hh + lid_px),
                fill=C_BG
            )
            # Якщо майже закрито — cyan лінія (blink)
            if blink_line or lid_top > 0.85:
                line_y = cy - hh + lid_px
                gc = glow_color
                draw.line([(cx - hw + 8, line_y), (cx + hw - 8, line_y)],
                          fill=gc, width=4)
        else:
            # КУТОВА повіка (angry)
            # Ліва сторона вища, права нижча (для лівого ока) і навпаки
            # lid_angle > 0 → внутр. край (до носа) нижче
            angle_rad = math.radians(lid_angle)
            # Чотири точки трапеції-повіки
            half_tilt = int(hw * math.tan(angle_rad))
            top_y = cy - hh - 2
            # Ліво і право верхнього краю
            left_lid_y  = top_y
            right_lid_y = top_y
            # Нижній край повіки (похилий)
            left_bot_y  = cy - hh + lid_px - half_tilt
            right_bot_y = cy - hh + lid_px + half_tilt
            draw.polygon(
                [(cx - hw - 2, left_lid_y),
                 (cx + hw + 2, right_lid_y),
                 (cx + hw + 2, right_bot_y),
                 (cx - hw - 2, left_bot_y)],
                fill=C_BG
            )

    # 5. КОНТУР (neon outline) — поверх всього
    gc_outline = tuple(min(255, c + 30) for c in glow_color)
    draw_rrect(draw, cx, cy, hw, hh, r, outline=gc_outline, width=3)

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ РОТА
# ─────────────────────────────────────────────────────────────────────────────
def draw_mouth(draw, style="happy", open_factor=0.0, glow_color=None):
    """
    style: 'happy', 'sad', 'open', 'none'
    open_factor: 0=закритий, 1=відкритий (для говоріння)
    """
    if style == "none":
        return
    if glow_color is None:
        glow_color = C_CYAN

    if style == "open" or open_factor > 0.05:
        # Відкритий рот (овал)
        ow = int(MW * 0.7)
        oh = int(30 + 28 * open_factor)
        gc = tuple(max(0, c // 4) for c in glow_color)
        draw.ellipse((MX - ow - 4, MY - oh - 4, MX + ow + 4, MY + oh + 4), fill=gc)
        draw.ellipse((MX - ow, MY - oh, MX + ow, MY + oh), fill=(15, 15, 15))
        draw.ellipse((MX - ow, MY - oh, MX + ow, MY + oh),
                     outline=C_WHITE, width=3)

    elif style == "happy":
        # Маленька біла усмішка — дуга вниз
        arc_h = 22
        bbox = (MX - MW, MY - arc_h, MX + MW, MY + arc_h)
        # Glow
        gc = tuple(max(0, c // 5) for c in C_WHITE)
        draw.arc((MX - MW - 4, MY - arc_h - 4, MX + MW + 4, MY + arc_h + 4),
                 start=10, end=170, fill=gc, width=8)
        draw.arc(bbox, start=10, end=170, fill=C_WHITE, width=5)

    elif style == "sad":
        # Маленька перевернута дуга — cyan
        arc_h = 18
        bbox = (MX - MW, MY - arc_h, MX + MW, MY + arc_h)
        gc = tuple(max(0, c // 4) for c in C_CYAN)
        draw.arc((MX - MW - 4, MY - arc_h - 4, MX + MW + 4, MY + arc_h + 4),
                 start=190, end=350, fill=gc, width=8)
        draw.arc(bbox, start=190, end=350, fill=C_CYAN, width=4)

# ─────────────────────────────────────────────────────────────────────────────
# МАЛЮВАННЯ БРІВ (тільки surprised — білі дуги)
# ─────────────────────────────────────────────────────────────────────────────
def draw_brows_surprised(draw, lift=1.0):
    """lift: 0=нормально, 1=максимально підняті"""
    for cx in [EL_X, ER_X]:
        bw = 55
        bh = int(18 * lift)
        by = EY - EH - BROW_H - int(20 * lift)
        bbox = (cx - bw, by - bh, cx + bw, by + bh)
        # Glow
        draw.arc((cx - bw - 3, by - bh - 3, cx + bw + 3, by + bh + 3),
                 start=200, end=340, fill=(80, 80, 80), width=8)
        draw.arc(bbox, start=200, end=340, fill=C_WHITE, width=5)

# ─────────────────────────────────────────────────────────────────────────────
# СЛЬОЗИ
# ─────────────────────────────────────────────────────────────────────────────
def draw_tears(draw, elapsed):
    for base_x, offset in [(EL_X - 18, 0.0), (ER_X + 18, 0.55)]:
        drop_y = EY + EH + int((elapsed * 60 + offset * 100) % 120)
        # Крапля
        draw.ellipse((base_x - 8, drop_y - 16, base_x + 8, drop_y + 8),
                     fill=C_TEAR)
        # Shine на краплі
        draw.ellipse((base_x - 3, drop_y - 11, base_x + 1, drop_y - 5),
                     fill=(200, 240, 255))

# ─────────────────────────────────────────────────────────────────────────────
# РЕНДЕР КАДРУ — основна функція
# ─────────────────────────────────────────────────────────────────────────────
def render(
    # Ліве oko
    l_lid=0.0, l_lid_angle=0.0, l_gaze_x=0.0, l_gaze_y=0.0,
    l_iris_scale=1.0, l_blink_line=False,
    # Праве oko
    r_lid=0.0, r_lid_angle=0.0, r_gaze_x=0.0, r_gaze_y=0.0,
    r_iris_scale=1.0, r_blink_line=False,
    # Спільне
    hw=EW, hh=EH,
    glow_color=None, sclera_color=None,
    # Рот
    mouth="none", mouth_open=0.0,
    # Брови
    brows=False, brow_lift=1.0,
    # Фон
    bg=(0, 0, 0),
    # Сльози
    tears=False, tears_elapsed=0.0,
    # Екстра функція
    extra_fn=None
):
    if glow_color   is None: glow_color   = C_CYAN
    if sclera_color is None: sclera_color = C_SCLERA

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Ліве oko
    draw_eye(draw, EL_X, EY, hw, hh,
             lid_top=l_lid, lid_angle=-l_lid_angle,   # симетрія кута
             gaze_x=l_gaze_x, gaze_y=l_gaze_y,
             iris_scale=l_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=l_blink_line)
    # Праве oko
    draw_eye(draw, ER_X, EY, hw, hh,
             lid_top=r_lid, lid_angle=r_lid_angle,
             gaze_x=r_gaze_x, gaze_y=r_gaze_y,
             iris_scale=r_iris_scale,
             glow_color=glow_color,
             sclera_color=sclera_color,
             blink_line=r_blink_line)

    # Брови
    if brows:
        draw_brows_surprised(draw, lift=brow_lift)

    # Рот
    draw_mouth(draw, style=mouth, open_factor=mouth_open, glow_color=glow_color)

    # Сльози
    if tears:
        draw_tears(draw, tears_elapsed)

    # Екстра
    if extra_fn:
        extra_fn(draw)

    device.display(img)

# ─────────────────────────────────────────────────────────────────────────────
# АНІМАЦІЇ ЕМОЦІЙ
# ─────────────────────────────────────────────────────────────────────────────

# ── Внутрішнє моргання ───────────────────────────────────────────────────────
def _blink(mouth="happy", glow_color=None):
    """Швидке плавне моргання: відкрите → cyan лінія → відкрите"""
    if glow_color is None: glow_color = C_CYAN
    steps = 7
    # Закриваємо
    for i in range(steps):
        t = ease_inout(i / steps)
        render(l_lid=t, r_lid=t, mouth=mouth, glow_color=glow_color,
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.014)
    # Cyan лінія
    render(l_lid=1.0, r_lid=1.0, mouth=mouth, glow_color=glow_color,
           l_blink_line=True, r_blink_line=True)
    time.sleep(0.055)
    # Відкриваємо
    for i in range(steps):
        t = ease_inout(1.0 - i / steps)
        render(l_lid=t, r_lid=t, mouth=mouth, glow_color=glow_color,
               l_blink_line=(t > 0.8), r_blink_line=(t > 0.8))
        time.sleep(0.014)

# ── 😊 HAPPY ─────────────────────────────────────────────────────────────────
def anim_happy(duration=6.0):
    t_start = time.time()
    t = 0.0
    blink_t = time.time() + random.uniform(2.5, 4.5)
    # Погляд
    gx, gy = 0.0, 0.0
    tgx, tgy = 0.0, 0.0
    gaze_t = time.time() + random.uniform(1.5, 3.0)

    while time.time() - t_start < duration:
        t += DT
        # Дихання — мікро-пульс розміру
        breathe = 0.012 * math.sin(t * 1.5)
        hw = int(EW * (1 + breathe))
        hh = int(EH * (1 + breathe))

        # Плавний рух погляду
        gx = lerp(gx, tgx, 0.07)
        gy = lerp(gy, tgy, 0.07)
        if time.time() >= gaze_t:
            tgx = random.uniform(-0.55, 0.55)
            tgy = random.uniform(-0.3,  0.3)
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
    t_start = time.time()
    t = 0.0
    spring_dur = 0.55

    while time.time() - t_start < duration:
        elapsed = time.time() - t_start
        t += DT

        if elapsed < spring_dur:
            # Пружина — overshoot
            st = elapsed / spring_dur
            overshoot = 1.0 + 0.14 * math.exp(-st * 4) * math.cos(st * 18)
            hw = int(EW * overshoot)
            hh = int(EH * overshoot)
            iris_sc = max(0.5, 1.0 - 0.3 * st)   # зменшуємо плавно
            brow_lift = st
        else:
            hw = EW
            hh = EH
            iris_sc = 0.72   # менша райдужка = широко відкриті
            brow_lift = 1.0
            # Очі блукають здивовано
            gx = 0.3 * math.sin(t * 1.4)
            gy = -0.2 * abs(math.sin(t * 0.9))

        render(hw=hw, hh=hh,
               l_gaze_x=gx if elapsed >= spring_dur else 0,
               r_gaze_x=gx if elapsed >= spring_dur else 0,
               l_gaze_y=gy if elapsed >= spring_dur else 0,
               r_gaze_y=gy if elapsed >= spring_dur else 0,
               l_iris_scale=iris_sc, r_iris_scale=iris_sc,
               brows=True, brow_lift=brow_lift,
               glow_color=C_CYAN, mouth="none")
        time.sleep(DT)

# ── 😢 SAD ────────────────────────────────────────────────────────────────────
def anim_sad(duration=6.0):
    t_start = time.time()
    t = 0.0
    blink_t = time.time() + random.uniform(3.5, 6.0)
    LID = 0.42   # повіка опущена на 42%

    while time.time() - t_start < duration:
        elapsed = time.time() - t_start
        t += DT

        # Легке хитання вниз
        sway = 0.06 * math.sin(t * 0.55)

        render(l_lid=LID + sway, r_lid=LID + sway,
               l_gaze_y=0.35, r_gaze_y=0.35,   # погляд вниз
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
    t = 0.0
    frame_n = 0
    LID = 0.38   # повіка опущена
    ANGLE = 18.0 # кут повіки (градуси) — до носа нижче

    excl_visible = True

    def angry_extra(draw):
        nonlocal excl_visible
        if frame_n % 6 < 3:
            pulse = abs(math.sin(frame_n * 0.28))
            col = (255, int(160 * pulse), 0)
            draw.text((W // 2 - 10, 8), "!!!", fill=col)

    # Плавне з'явлення червоного фону
    bg_r = 0
    while time.time() - t_start < duration:
        t += DT
        frame_n += 1
        elapsed = time.time() - t_start

        # Фон поступово червоніє
        bg_r = min(55, int(55 * min(1.0, elapsed / 0.8)))
        bg = (bg_r, 0, 0)

        # Тремтіння
        shake = int(8 * max(0, 1.0 - elapsed * 0.5))   # стихає з часом
        sx = random.randint(-shake, shake) if shake > 1 else 0
        sy = random.randint(-shake // 2, shake // 2) if shake > 1 else 0

        # Пульс розміру очей
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
    t = 0.0
    blink_t = time.time() + random.uniform(2.0, 3.5)

    L_LID = 0.0    # ліве = відкрите
    R_LID = 0.50   # праве = напів-закрите

    FORMULAS = ["E=mc²", "π≈3.14", "42?", "∑n²", "∞", "AI>0", "f(x)?", "..."]
    formula_text  = ""
    formula_alpha = 0
    formula_x, formula_y = 300, 28
    formula_t = time.time() + 1.0

    def thinking_extra(draw):
        nonlocal formula_text, formula_alpha, formula_x, formula_y, formula_t
        if time.time() >= formula_t:
            formula_text  = random.choice(FORMULAS)
            formula_x     = random.randint(270, 400)
            formula_y     = random.randint(12, 65)
            formula_alpha = 210
            formula_t     = time.time() + random.uniform(2.0, 3.5)
        if formula_alpha > 0:
            col = (0, int(180 * formula_alpha / 210),
                      int(255 * formula_alpha / 210))
            draw.text((formula_x, formula_y), formula_text, fill=col)
            formula_alpha = max(0, formula_alpha - 14)

    while time.time() - t_start < duration:
        t += DT

        # Погляд вбік — ліве oko
        gx = 0.38 + 0.12 * math.sin(t * 0.7)
        gy = -0.25 + 0.08 * math.sin(t * 0.5)

        # Праве oko — погляд теж вбік але трохи вниз (примружене)
        render(
            l_lid=L_LID, l_gaze_x=gx, l_gaze_y=gy,
            r_lid=R_LID, r_gaze_x=gx, r_gaze_y=gy + 0.15,
            glow_color=C_CYAN,
            mouth="none",
            extra_fn=thinking_extra
        )

        if time.time() >= blink_t:
            # Моргає тільки лівим (правe вже примружене)
            for i in range(6):
                tv = ease_inout(i / 6)
                render(l_lid=tv, r_lid=R_LID,
                       l_blink_line=(tv > 0.8),
                       glow_color=C_CYAN, mouth="none")
                time.sleep(0.014)
            time.sleep(0.05)
            for i in range(6):
                tv = ease_inout(1.0 - i / 6)
                render(l_lid=tv, r_lid=R_LID,
                       l_blink_line=(tv > 0.8),
                       glow_color=C_CYAN, mouth="none")
                time.sleep(0.014)
            blink_t = time.time() + random.uniform(2.0, 3.5)

        time.sleep(DT)

# ── Говоріння (виклик ззовні) ─────────────────────────────────────────────────
def anim_talking(duration=3.0):
    t_start = time.time()
    t = 0.0
    while time.time() - t_start < duration:
        t += DT
        open_f = max(0.0, 0.6 * abs(math.sin(t * 9.0)))
        render(mouth="open", mouth_open=open_f, glow_color=C_CYAN)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# ПЛАВНИЙ ПЕРЕХІД МІЖ СТАНАМИ
# ─────────────────────────────────────────────────────────────────────────────
def transition_to(
    from_state: dict, to_state: dict, duration=0.45
):
    """
    Плавно переходить від from_state до to_state.
    Стан = dict з параметрами функції render().
    """
    steps = max(4, int(duration / DT))
    for i in range(steps + 1):
        t = ease_inout(i / steps)
        blended = {}
        for key in to_state:
            fv = from_state.get(key, to_state[key])
            tv = to_state[key]
            if isinstance(tv, (int, float)):
                blended[key] = lerp(fv, tv, t)
            elif isinstance(tv, tuple) and len(tv) == 3:
                blended[key] = tuple(int(lerp(fv[j], tv[j], t)) for j in range(3))
            else:
                blended[key] = tv if t > 0.5 else fv
        render(**blended)
        time.sleep(DT)

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────
STATE_HAPPY = dict(l_lid=0.0, r_lid=0.0, mouth="happy",
                   glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)
STATE_SURPRISED = dict(l_lid=0.0, r_lid=0.0, l_iris_scale=0.72, r_iris_scale=0.72,
                       brows=True, brow_lift=1.0, mouth="none",
                       glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)
STATE_SAD = dict(l_lid=0.42, r_lid=0.42, l_gaze_y=0.35, r_gaze_y=0.35,
                 mouth="sad", glow_color=C_CYAN_DIM,
                 sclera_color=C_SCLERA, bg=C_BG)
STATE_ANGRY = dict(l_lid=0.38, r_lid=0.38, l_lid_angle=18.0, r_lid_angle=18.0,
                   mouth="none", glow_color=C_GLOW_ANGRY,
                   sclera_color=C_SCLERA_ANGRY, bg=(55, 0, 0))
STATE_THINKING = dict(l_lid=0.0, r_lid=0.50, mouth="none",
                      glow_color=C_CYAN, sclera_color=C_SCLERA, bg=C_BG)

def run():
    print("🤖 AIKO eyes_v2 запущено! Ctrl+C щоб зупинити")

    # Поява — моргання з нуля
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
