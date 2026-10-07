"""
😠 AIKO — emotion_angry.py
Тестовий файл емоції ANGRY (нескінченний цикл, Ctrl+C для виходу)
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

# ── Кольори ───────────────────────────────────────────────────────────────────
C_GLOW     = (30,  30,  255)
C_GLOW_DIM = (20,  20,  160)
C_SCLERA   = (255, 255, 255)
C_IRIS     = (255, 140, 30 )
C_PUPIL    = (0,   0,   0  )
C_SHINE    = (255, 255, 255)
C_TOOTH    = (240, 240, 240)
C_EXCLAIM  = (0, 220, 255)     # жовтий (BGR swap для ILI9488)

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

# ── Шрифт ─────────────────────────────────────────────────────────────────────
try:
    FONT_EXCLAIM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
except:
    FONT_EXCLAIM = ImageFont.load_default()

# ── Утиліти ───────────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))

def lerp(a, b, t): return a + (b - a) * clamp(t, 0.0, 1.0)

def cubic_ease_in_out(t):
    """Кубічна крива: дуже плавний старт і кінець"""
    t = clamp(t, 0.0, 1.0)
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        p = 2.0 * t - 2.0
        return 0.5 * p * p * p + 1.0

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
             eye_offset_px=0,
             glow_color=C_GLOW_DIM, bg_color=(120, 20, 10),
             mirror=False):
    if not mirror:
        real_cx = cx + eye_offset_px
    else:
        real_cx = cx - eye_offset_px

    draw_glow(draw, real_cx, cy, hw, hh, ER, glow_color)
    draw.rounded_rectangle(
        (real_cx - hw, cy - hh, real_cx + hw, cy + hh),
        radius=ER, fill=C_SCLERA
    )

    iris_hw = int(hw * 0.50)
    iris_hh = int(hh * 0.50)
    max_gx  = max(1, hw - iris_hw - 4)
    max_gy  = max(1, hh - iris_hh - 4)

    off_x = int(clamp(gaze_x * max_gx, -max_gx, max_gx))
    off_y = int(clamp(gaze_y * max_gy, -max_gy, max_gy))

    icx, icy = real_cx + off_x, cy + off_y

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
        draw_lid_angry(draw, real_cx, cy, hw, hh,
                       lid_frac=lid_frac,
                       sway_px=sway_px,
                       bg_color=bg_color,
                       glow_color=glow_color,
                       mirror=mirror)

    gc_outline = tuple(min(255, c + 40) for c in glow_color)
    draw.rounded_rectangle(
        (real_cx - hw, cy - hh, real_cx + hw, cy + hh),
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

# ── Знаки оклику ──────────────────────────────────────────────────────────────
_exclaims = []
_next_exclaim_t = 0.0

def update_exclaims(now):
    """Рандомно генерує та прибирає знаки оклику"""
    global _next_exclaim_t

    # Прибираємо старі (живуть 1 секунду)
    active = [e for e in _exclaims if now - e['born'] < 1.0]
    _exclaims.clear()
    _exclaims.extend(active)

    # Час для нового?
    if now >= _next_exclaim_t:
        count = random.randint(2, 3)
        used_x = []
        for _ in range(count):
            for attempt in range(20):
                nx = random.randint(30, W - 30)
                if all(abs(nx - ux) > 50 for ux in used_x):
                    used_x.append(nx)
                    _exclaims.append({
                        'x': nx,
                        'y': random.randint(10, 55),
                        'born': now
                    })
                    break
        _next_exclaim_t = now + random.uniform(2.0, 4.0)

def draw_exclaims(draw):
    for e in _exclaims:
        draw.text((e['x'], e['y']), "!", font=FONT_EXCLAIM,
                  fill=C_EXCLAIM, anchor="mt")

# ── Рендер кадру ──────────────────────────────────────────────────────────────
def render(now, lid_frac=LID_FRAC_ANGRY, sway_px=0,
           mouth_morph=1.0, bg=(120, 20, 10),
           eye_offset_px=0, gaze_x=0.0):
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    base_gaze_y = 0.20

    draw_eye(draw, BASE_EL_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=gaze_x,
             gaze_y=base_gaze_y,
             eye_offset_px=eye_offset_px,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=False)

    draw_eye(draw, BASE_ER_X, BASE_EY, EW, EH,
             lid_frac=lid_frac, sway_px=sway_px,
             gaze_x=-gaze_x,
             gaze_y=base_gaze_y,
             eye_offset_px=eye_offset_px,
             glow_color=C_GLOW_DIM, bg_color=bg,
             mirror=True)

    draw_mouth_angry(draw, morph=mouth_morph)

    update_exclaims(now)
    draw_exclaims(draw)

    device.display(img)

# ── Анімація ANGRY ────────────────────────────────────────────────────────────
def anim_angry():
    print("😠 Angry — Ctrl+C для виходу")

    t = 0.0

    STATE_IDLE     = 0
    STATE_MOVE_IN  = 1
    STATE_HOLD     = 2
    STATE_MOVE_OUT = 3

    MOVE_DURATION = 1.2
    HOLD_DURATION = 2.0   # затримка в центрі 2 секунди
    EYE_SHIFT_PX  = 14
    GAZE_TARGET   = 1.0

    state         = STATE_IDLE
    state_start   = time.time()
    next_idle_t   = time.time() + random.uniform(1.0, 1.5)

    eye_offset_px = 0.0
    gaze_x        = 0.0

    last_frame = time.time()

    while True:
        now   = time.time()
        delta = now - last_frame
        last_frame = now
        t += delta

        bg = (120, 20, 10)

        # Легке тремтіння повік
        sway_px = int(1.5 * math.sin(t * 1.8))

        # ── Машина станів ────────────────────────────────────────────────────
        elapsed = now - state_start

        if state == STATE_IDLE:
            eye_offset_px = 0.0
            gaze_x        = 0.0
            if now >= next_idle_t:
                state       = STATE_MOVE_IN
                state_start = now

        elif state == STATE_MOVE_IN:
            progress      = cubic_ease_in_out(elapsed / MOVE_DURATION)
            eye_offset_px = lerp(0.0, EYE_SHIFT_PX, progress)
            gaze_x        = lerp(0.0, GAZE_TARGET,   progress)
            if elapsed >= MOVE_DURATION:
                eye_offset_px = EYE_SHIFT_PX
                gaze_x        = GAZE_TARGET
                state         = STATE_HOLD
                state_start   = now

        elif state == STATE_HOLD:
            eye_offset_px = EYE_SHIFT_PX
            gaze_x        = GAZE_TARGET
            if elapsed >= HOLD_DURATION:
                state       = STATE_MOVE_OUT
                state_start = now

        elif state == STATE_MOVE_OUT:
            progress      = cubic_ease_in_out(elapsed / MOVE_DURATION)
            eye_offset_px = lerp(EYE_SHIFT_PX, 0.0, progress)
            gaze_x        = lerp(GAZE_TARGET,   0.0, progress)
            if elapsed >= MOVE_DURATION:
                eye_offset_px = 0.0
                gaze_x        = 0.0
                state         = STATE_IDLE
                next_idle_t   = now + random.uniform(1.0, 1.5)

        render(now,
               lid_frac=LID_FRAC_ANGRY,
               sway_px=sway_px,
               bg=bg,
               eye_offset_px=int(eye_offset_px),
               gaze_x=gaze_x)

        time.sleep(DT)

# ── Старт ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        anim_angry()
    except KeyboardInterrupt:
        print("\n👋 Вихід")
        device.display(Image.new("RGB", (W, H), (0, 0, 0)))
