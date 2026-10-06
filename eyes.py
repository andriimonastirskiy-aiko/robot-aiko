from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import time
import math
import random

# ── Дисплей ──────────────────────────────────────────────────────────────────
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=32000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)

W, H = 480, 320

# ── Завантаження PNG ──────────────────────────────────────────────────────────
EYES_DIR = "/home/aiko/eyes"

def load_img(name):
    img = Image.open(f"{EYES_DIR}/{name}.png").convert("RGBA")
    return img.resize((W, H), Image.LANCZOS)

IMGS = {n: load_img(n) for n in ["happy", "blink", "surprised", "sad", "angry", "thinking"]}
print("✅ Всі картинки завантажено!")

# ── Відображення кадру ────────────────────────────────────────────────────────
def show(img):
    device.display(img.convert("RGB"))

# ── Зміщення картинки ─────────────────────────────────────────────────────────
def shift(img, dx=0, dy=0):
    result = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    result.paste(img, (int(dx), int(dy)))
    return result

# ── Масштабування з центру ────────────────────────────────────────────────────
def scale_center(img, factor):
    nw = max(1, int(W * factor))
    nh = max(1, int(H * factor))
    resized = img.resize((nw, nh), Image.LANCZOS)
    result = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    x = (W - nw) // 2
    y = (H - nh) // 2
    result.paste(resized, (x, y))
    return result

# ── Накласти кольоровий оверлей ───────────────────────────────────────────────
def color_overlay(img, color, alpha):
    overlay = Image.new("RGBA", img.size, color + (alpha,))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 ПЕРЕХОДИ МІЖ ЕМОЦІЯМИ
# ─────────────────────────────────────────────────────────────────────────────

# 💥 BURST — нова картинка вибухає з центру
def transition_burst(img_from, img_to):
    steps = 14
    for i in range(steps):
        t = i / steps
        # Нова картинка росте з центру
        scale = 0.05 + 0.95 * t
        new_frame = scale_center(img_to, scale)
        # Стара картинка трохи розмивається і темніє
        alpha = int(255 * (1 - t))
        old_frame = color_overlay(img_from, (0, 0, 0), int(180 * t))
        # Поєднуємо: стара темніє, нова росте поверх
        combined = Image.blend(old_frame.convert("RGB"), new_frame.convert("RGB"), t)
        device.display(combined)
        time.sleep(0.025)

# 🌊 WAVE — хвиля зліва направо
def transition_wave(img_from, img_to):
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        x_split = int(W * t)
        frame = img_from.copy().convert("RGB")
        right_part = img_to.convert("RGB").crop((0, 0, x_split, H))
        frame.paste(right_part, (0, 0))
        # Хвиля — вертикальна лінія
        draw = ImageDraw.Draw(frame)
        for dy in range(-15, 15):
            wave_x = x_split + int(8 * math.sin(dy * 0.4))
            if 0 <= wave_x < W:
                draw.line([(wave_x, max(0, dy*11)), (wave_x, min(H, dy*11+12))],
                          fill=(255, 255, 255, 180), width=2)
        device.display(frame)
        time.sleep(0.02)

# ⚡ FLASH — спалах і нова емоція
def transition_flash(img_from, img_to):
    # Спалах білого
    for alpha in [60, 130, 200, 255, 200, 130]:
        frame = color_overlay(img_from, (255, 255, 200), alpha)
        show(frame)
        time.sleep(0.02)
    # Одразу нова картинка
    show(img_to)
    time.sleep(0.05)
    # Легкий fade щоб не різало
    for alpha in [80, 40, 0]:
        frame = color_overlay(img_to, (255, 255, 200), alpha)
        show(frame)
        time.sleep(0.02)

# 📺 GLITCH — розрізається на смуги
def transition_glitch(img_from, img_to):
    strips = 8
    strip_h = H // strips
    steps = 16
    offsets = [random.randint(-W//2, W//2) for _ in range(strips)]

    for i in range(steps):
        t = i / steps
        frame = Image.new("RGB", (W, H), (0, 0, 0))
        for s in range(strips):
            y0 = s * strip_h
            y1 = y0 + strip_h
            if t < 0.5:
                # Стара картинка розїжджається
                strip = img_from.convert("RGB").crop((0, y0, W, y1))
                off = int(offsets[s] * (t * 2))
            else:
                # Нова картинка збирається
                strip = img_to.convert("RGB").crop((0, y0, W, y1))
                off = int(offsets[s] * (1 - (t - 0.5) * 2))
            frame.paste(strip, (off, y0))
            # Глітч лінія
            if random.random() < 0.3:
                draw = ImageDraw.Draw(frame)
                draw.rectangle([(0, y0), (W, y0+2)], fill=(0, 255, 200))
        device.display(frame)
        time.sleep(0.025)

# 🌀 SPIN ZOOM — крутиться і збільшується
def transition_spinzoom(img_from, img_to):
    steps = 16
    for i in range(steps):
        t = i / steps
        # Стара зменшується
        scale_old = 1.0 - 0.5 * t
        frame_old = scale_center(img_from, max(0.05, scale_old))
        # Нова збільшується
        scale_new = 0.1 + 0.9 * t
        frame_new = scale_center(img_to, scale_new)
        combined = Image.blend(frame_old.convert("RGB"), frame_new.convert("RGB"), t)
        device.display(combined)
        time.sleep(0.025)

# ─────────────────────────────────────────────────────────────────────────────
# 😊 HAPPY — дихання + рух вгору-вниз + моргання
# ─────────────────────────────────────────────────────────────────────────────
def _do_blink():
    base = IMGS["happy"]
    blink = IMGS["blink"]
    # Плавне закривання
    steps = 7
    for i in range(steps):
        t = i / steps
        frame = Image.blend(base.convert("RGB"), blink.convert("RGB"), t)
        device.display(frame)
        time.sleep(0.018)
    time.sleep(0.07)
    # Плавне відкривання
    for i in range(steps):
        t = i / steps
        frame = Image.blend(blink.convert("RGB"), base.convert("RGB"), t)
        device.display(frame)
        time.sleep(0.018)

def anim_happy(duration=5.0):
    base = IMGS["happy"]
    t_start = time.time()
    blink_timer = time.time() + random.uniform(2.5, 4.0)
    t = 0.0

    while time.time() - t_start < duration:
        t += 0.07
        scale = 1.0 + 0.014 * math.sin(t * 1.4)
        dy = 3.5 * math.sin(t * 1.1)

        frame = scale_center(base, scale)
        frame = shift(frame, dy=dy)
        show(frame)

        if time.time() >= blink_timer:
            _do_blink()
            blink_timer = time.time() + random.uniform(2.5, 4.0)

        time.sleep(0.033)

# ─────────────────────────────────────────────────────────────────────────────
# 😲 SURPRISED — стрибок + пружина (без домальовування)
# ─────────────────────────────────────────────────────────────────────────────
def anim_surprised(duration=3.0):
    base = IMGS["surprised"]
    steps = 16
    for i in range(steps):
        factor = 0.25 + 0.75 * (i / steps)
        if i > steps * 0.75:
            spring = 1.0 + 0.05 * math.sin((i - steps * 0.75) * 3.5)
            factor = min(factor * spring, 1.06)
        frame = scale_center(base, factor)
        show(frame)
        time.sleep(0.025)

    t_start = time.time()
    t = 0.0
    while time.time() - t_start < duration:
        t += 0.07
        scale = 1.0 + 0.012 * math.sin(t * 2.2)
        dy = 2.5 * math.sin(t * 1.8)
        frame = scale_center(base, scale)
        frame = shift(frame, dy=dy)
        show(frame)
        time.sleep(0.033)

# ─────────────────────────────────────────────────────────────────────────────
# 😢 SAD — хитання вниз + сльози (без домальовування рота)
# ─────────────────────────────────────────────────────────────────────────────
def anim_sad(duration=5.0):
    base = IMGS["sad"]
    t_start = time.time()
    t = 0.0

    while time.time() - t_start < duration:
        t += 0.05
        dy = 7 * math.sin(t * 0.55)

        frame = base.copy()
        draw = ImageDraw.Draw(frame)

        # Сльози — падаючі краплі
        elapsed = time.time() - t_start
        tear_offset_l = int(elapsed * 20) % 130
        tear_offset_r = int(elapsed * 20 + 45) % 130
        # Ліва сльоза
        draw.ellipse((148, 175 + tear_offset_l, 160, 190 + tear_offset_l),
                     fill=(120, 190, 255, 210))
        # Права сльоза
        draw.ellipse((315, 175 + tear_offset_r, 327, 190 + tear_offset_r),
                     fill=(120, 190, 255, 210))

        frame = shift(frame, dy=dy)
        show(frame)
        time.sleep(0.033)

# ─────────────────────────────────────────────────────────────────────────────
# 😠 ANGRY — шейк + червоний пульс + вогники
# ─────────────────────────────────────────────────────────────────────────────
def anim_angry(duration=4.0):
    base = IMGS["angry"]
    t_start = time.time()
    frame_count = 0

    while time.time() - t_start < duration:
        dx = random.randint(-9, 9)
        dy = random.randint(-4, 4)

        pulse = abs(math.sin(frame_count * 0.28))
        red_alpha = int(35 + 55 * pulse)

        frame = color_overlay(base, (255, 20, 0), red_alpha)
        frame = shift(frame, dx=dx, dy=dy)
        draw = ImageDraw.Draw(frame)

        # Вогники по кутах (мигають)
        if frame_count % 3 < 2:
            for fx, fy in [(8, 8), (435, 8), (8, 265), (435, 265)]:
                r = random.randint(30, 50)
                draw.ellipse((fx, fy, fx+r, fy+r+10),
                             fill=(255, random.randint(60, 120), 0, 220))
                draw.ellipse((fx+6, fy-8, fx+r-6, fy+12),
                             fill=(255, 210, 0, 190))

        # !!! по центру зверху
        if frame_count % 6 < 3:
            draw.text((210, 12), "!!!", fill=(255, 255, 0))

        show(frame)
        frame_count += 1
        time.sleep(0.045)

# ─────────────────────────────────────────────────────────────────────────────
# 🤔 THINKING — хитання + формули що з'являються
# ─────────────────────────────────────────────────────────────────────────────
FORMULAS = [
    "E = mc²", "π ≈ 3.14159", "∑(n²) = ?",
    "42 = ???", "f(x) = ax²+b", "∞ / ∞ = ?",
    "log₂(256) = 8", "AI > 0", "x = (-b±√D)/2a",
]

def anim_thinking(duration=5.0):
    base = IMGS["thinking"]
    t_start = time.time()
    t = 0.0
    formula_timer = 0.0
    current_formula = random.choice(FORMULAS)
    formula_alpha = 255
    formula_x = random.randint(260, 370)
    formula_y = random.randint(18, 70)

    while time.time() - t_start < duration:
        t += 0.06
        dx = 11 * math.sin(t * 0.9)
        dy = 2.5 * math.sin(t * 1.8)

        frame = base.copy()
        draw = ImageDraw.Draw(frame)

        # Формула
        formula_timer += 0.06
        if formula_timer > 2.2:
            formula_timer = 0.0
            current_formula = random.choice(FORMULAS)
            formula_x = random.randint(250, 370)
            formula_y = random.randint(15, 70)
            formula_alpha = 255

        if formula_alpha > 0:
            draw.text((formula_x, formula_y), current_formula,
                      fill=(0, 210, 255, formula_alpha))
            formula_alpha = max(0, formula_alpha - 10)

        # Крапки "думаю..."
        dots = "." * (int(time.time() * 2.5) % 4)
        draw.text((210, 286), f"думаю{dots}", fill=(160, 160, 255, 210))

        frame = shift(frame, dx=dx, dy=dy)
        show(frame)
        time.sleep(0.033)

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("🤖 AIKO очі запущено! Ctrl+C щоб зупинити")

    # Початкова поява — burst з чорного
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    transition_burst(black, IMGS["happy"])

    while True:
        print("😊 Happy...")
        anim_happy(duration=5.0)

        print("💥 Burst → Surprised!")
        transition_burst(IMGS["happy"], IMGS["surprised"])
        anim_surprised(duration=3.0)

        print("🌊 Wave → Sad...")
        transition_wave(IMGS["surprised"], IMGS["sad"])
        anim_sad(duration=5.0)

        print("⚡ Flash → Angry!")
        transition_flash(IMGS["sad"], IMGS["angry"])
        anim_angry(duration=4.0)

        print("📺 Glitch → Thinking...")
        transition_glitch(IMGS["angry"], IMGS["thinking"])
        anim_thinking(duration=5.0)

        print("🌀 SpinZoom → Happy!")
        transition_spinzoom(IMGS["thinking"], IMGS["happy"])

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        black = Image.new("RGB", (W, H), (0, 0, 0))
        device.display(black)
