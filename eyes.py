from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from luma.core.render import canvas
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
    frame = img.convert("RGB")
    device.display(frame)

# ── Накласти кольоровий оверлей ───────────────────────────────────────────────
def color_overlay(img, color, alpha):
    overlay = Image.new("RGBA", img.size, color + (alpha,))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

# ── Зміщення картинки ─────────────────────────────────────────────────────────
def shift(img, dx=0, dy=0):
    result = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    result.paste(img, (int(dx), int(dy)))
    return result

# ── Масштабування з центру ────────────────────────────────────────────────────
def scale_center(img, factor):
    nw = int(W * factor)
    nh = int(H * factor)
    resized = img.resize((nw, nh), Image.LANCZOS)
    result = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    x = (W - nw) // 2
    y = (H - nh) // 2
    result.paste(resized, (x, y))
    return result

# ── Fade між двома картинками ─────────────────────────────────────────────────
def fade(img_from, img_to, steps=12, delay=0.03):
    for i in range(steps + 1):
        alpha = i / steps
        blended = Image.blend(img_from.convert("RGB"), img_to.convert("RGB"), alpha)
        device.display(blended)
        time.sleep(delay)

# ─────────────────────────────────────────────────────────────────────────────
# 😊 HAPPY — дихання + рух вгору-вниз + моргання + усмішка
# ─────────────────────────────────────────────────────────────────────────────
def anim_happy(duration=5.0):
    base = IMGS["happy"].copy()
    t_start = time.time()
    blink_timer = time.time() + random.uniform(2.5, 4.0)

    # Малюємо усмішку поверх картинки
    smile_img = base.copy()
    draw = ImageDraw.Draw(smile_img)
    draw.arc((180, 245, 300, 295), start=0, end=180, fill=(255, 220, 180, 200), width=4)

    t = 0.0
    while time.time() - t_start < duration:
        t += 0.08

        # Дихання — масштаб 1.00 → 1.03
        scale = 1.0 + 0.015 * math.sin(t * 1.5)
        # Рух вгору-вниз ±4px
        dy = 4 * math.sin(t * 1.2)

        frame = scale_center(smile_img, scale)
        frame = shift(frame, dy=dy)
        show(frame)

        # Моргання
        if time.time() >= blink_timer:
            _do_blink(smile_img)
            blink_timer = time.time() + random.uniform(2.5, 4.0)

        time.sleep(0.04)

# ─────────────────────────────────────────────────────────────────────────────
# 😑 BLINK — плавне моргання через fade
# ─────────────────────────────────────────────────────────────────────────────
def _do_blink(base_img):
    blink_img = IMGS["blink"]
    fade(base_img, blink_img, steps=6, delay=0.02)
    time.sleep(0.08)
    fade(blink_img, base_img, steps=6, delay=0.02)

def anim_blink(times=3):
    base = IMGS["happy"]
    for _ in range(times):
        _do_blink(base)
        time.sleep(0.2)

# ─────────────────────────────────────────────────────────────────────────────
# 😲 SURPRISED — стрибок з маленького + брови + рот
# ─────────────────────────────────────────────────────────────────────────────
def anim_surprised(duration=3.0):
    base = IMGS["surprised"].copy()

    # Малюємо брови та рот поверх картинки
    draw = ImageDraw.Draw(base)
    # Брови
    draw.arc((100, 55, 210, 95), start=200, end=340, fill=(255, 255, 255, 230), width=5)
    draw.arc((270, 55, 380, 95), start=200, end=340, fill=(255, 255, 255, 230), width=5)
    # Рот — кружечок здивування
    draw.ellipse((210, 240, 270, 300), outline=(255, 255, 255, 220), width=4)

    # Стрибок — від 0.3 до 1.0
    steps = 18
    for i in range(steps):
        factor = 0.3 + 0.7 * (i / steps)
        # Пружинний ефект наприкінці
        if i > steps * 0.7:
            overshoot = 1.0 + 0.04 * math.sin((i - steps * 0.7) * 3.0)
            factor = min(factor * overshoot, 1.08)
        frame = scale_center(base, factor)
        show(frame)
        time.sleep(0.03)

    # Утримуємо
    t_start = time.time()
    t = 0.0
    while time.time() - t_start < duration:
        t += 0.08
        scale = 1.0 + 0.01 * math.sin(t * 2.0)
        frame = scale_center(base, scale)
        show(frame)
        time.sleep(0.04)

# ─────────────────────────────────────────────────────────────────────────────
# 😢 SAD — опускання вниз + сльоза
# ─────────────────────────────────────────────────────────────────────────────
def anim_sad(duration=5.0):
    base = IMGS["sad"].copy()

    t_start = time.time()
    t = 0.0
    tear_y = 180  # початок сльози

    while time.time() - t_start < duration:
        t += 0.06
        # Повільне опускання вниз ±8px
        dy = 8 * math.sin(t * 0.6)

        frame = base.copy()

        # Малюємо сльозу
        draw = ImageDraw.Draw(frame)
        tear_offset = int(tear_y + (time.time() - t_start) * 18) % 140
        # Ліва сльоза
        draw.ellipse((152, 180 + tear_offset, 162, 195 + tear_offset),
                     fill=(100, 180, 255, 200))
        # Права сльоза (трохи зміщена по часу)
        tear_offset2 = (tear_offset + 30) % 140
        draw.ellipse((318, 180 + tear_offset2, 328, 195 + tear_offset2),
                     fill=(100, 180, 255, 200))

        # Сумний рот
        draw.arc((180, 260, 300, 300), start=180, end=360,
                 fill=(200, 200, 255, 180), width=4)

        frame = shift(frame, dy=dy)
        show(frame)
        time.sleep(0.04)

# ─────────────────────────────────────────────────────────────────────────────
# 😠 ANGRY — шейк + червоний оверлей + вогники
# ─────────────────────────────────────────────────────────────────────────────
FIRE_CHARS = ["🔥", "💢", "!!!"]

def anim_angry(duration=4.0):
    base = IMGS["angry"].copy()
    t_start = time.time()
    frame_count = 0

    while time.time() - t_start < duration:
        # Шейк — хаотичне тремтіння
        dx = random.randint(-8, 8)
        dy = random.randint(-4, 4)

        # Пульсуючий червоний оверлей
        pulse = abs(math.sin(frame_count * 0.3))
        red_alpha = int(40 + 50 * pulse)

        frame = base.copy()
        frame = color_overlay(frame, (255, 30, 0), red_alpha)
        frame = shift(frame, dx=dx, dy=dy)

        # Малюємо вогники по кутах
        draw = ImageDraw.Draw(frame)
        if frame_count % 4 < 2:
            # Вогники у кутах (комедійний стиль)
            for fx, fy in [(10, 10), (430, 10), (10, 270), (430, 270)]:
                draw.ellipse((fx, fy, fx+30, fy+40), fill=(255, 100+random.randint(0,50), 0, 200))
                draw.ellipse((fx+5, fy-10, fx+25, fy+15), fill=(255, 200, 0, 180))
        # Знак оклику по центру
        if frame_count % 8 < 4:
            draw.text((220, 15), "!!!", fill=(255, 255, 0, 230))

        show(frame)
        frame_count += 1
        time.sleep(0.05)

# ─────────────────────────────────────────────────────────────────────────────
# 🤔 THINKING — хитання + формули
# ─────────────────────────────────────────────────────────────────────────────
FORMULAS = [
    "E = mc²",
    "π = 3.14159...",
    "∑(n²) = ?",
    "42 = ?",
    "AI > 0",
    "f(x) = ax²+b",
    "∞ / ∞ = ?",
    "log₂(256) = 8",
]

def anim_thinking(duration=5.0):
    base = IMGS["thinking"].copy()
    t_start = time.time()
    t = 0.0
    formula_timer = 0.0
    current_formula = random.choice(FORMULAS)
    formula_alpha = 0
    formula_x = random.randint(280, 380)
    formula_y = random.randint(20, 80)

    while time.time() - t_start < duration:
        t += 0.07
        # Хитання вліво-вправо ±12px
        dx = 12 * math.sin(t * 1.0)
        # Легкий нахил (вгору-вниз ±3px)
        dy = 3 * math.sin(t * 2.0)

        frame = base.copy()

        # Формула з'являється і зникає
        formula_timer += 0.07
        if formula_timer > 2.5:
            formula_timer = 0.0
            current_formula = random.choice(FORMULAS)
            formula_x = random.randint(250, 380)
            formula_y = random.randint(15, 80)
            formula_alpha = 255

        # Fade формули
        if formula_alpha > 0:
            draw = ImageDraw.Draw(frame)
            draw.text((formula_x, formula_y), current_formula,
                      fill=(0, 220, 255, formula_alpha))
            formula_alpha = max(0, formula_alpha - 8)

        # Крапки "думає" внизу
        dots = "." * (int(time.time() * 2) % 4)
        draw = ImageDraw.Draw(frame)
        draw.text((220, 285), f"думаю{dots}", fill=(150, 150, 255, 200))

        frame = shift(frame, dx=dx, dy=dy)
        show(frame)
        time.sleep(0.04)

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("🤖 AIKO очі запущено! Ctrl+C щоб зупинити")

    # Початкова поява
    black = Image.new("RGB", (W, H), (0, 0, 0))
    fade(black, IMGS["happy"], steps=15, delay=0.04)

    while True:
        print("😊 Happy...")
        anim_happy(duration=5.0)

        print("😑 Blink...")
        anim_blink(times=2)

        print("😲 Surprised!")
        fade(IMGS["happy"], IMGS["surprised"], steps=8, delay=0.03)
        anim_surprised(duration=3.0)

        print("😑 Blink...")
        anim_blink(times=1)

        print("😢 Sad...")
        fade(IMGS["surprised"], IMGS["sad"], steps=12, delay=0.04)
        anim_sad(duration=5.0)

        print("😠 Angry!")
        fade(IMGS["sad"], IMGS["angry"], steps=8, delay=0.03)
        anim_angry(duration=4.0)

        print("🤔 Thinking...")
        fade(IMGS["angry"], IMGS["thinking"], steps=10, delay=0.04)
        anim_thinking(duration=5.0)

        print("😊 Happy знову!")
        fade(IMGS["thinking"], IMGS["happy"], steps=12, delay=0.04)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n👋 AIKO вимикає очі...")
        black = Image.new("RGB", (W, H), (0, 0, 0))
        device.display(black)
