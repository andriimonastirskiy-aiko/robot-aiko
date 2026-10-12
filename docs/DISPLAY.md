# 🖥️ Дисплей ILI9488 3.5" — Технічні нотатки

## Підключення
| Дисплей | GPIO |
|---------|------|
| MOSI    | 10   |
| SCK     | 11   |
| CS      | 8    |
| DC      | 25   |
| RESET   | 17   |

## ✅ Як працює дисплей: luma.lcd напряму через SPI
Дисплей керується через `luma.lcd` **без framebuffer (fbtft) взагалі!**
Не додавати жодних `dtoverlay=fbtft,...` в `/boot/firmware/config.txt`.

Ініціалізація в коді:
```python
from luma.lcd.device import ili9488
from luma.core.interface.serial import spi

serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=32000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)
```

## 🤖 Основний файл очей: eyes_v3.py
Розташування: `/home/aiko/eyes_v3.py`
Запуск: `python3 /home/aiko/eyes_v3.py`

- Canvas: 480×320 px, чорний фон #000000
- Рендеринг: **pygame + SDL2**, малюється в реальному часі (без спрайтів)
- Ціль: **30 fps**
- Перехід між емоціями: **350 мс, ease-in-out**

### Геометрія
| Елемент    | Параметр                              |
|------------|---------------------------------------|
| Ліве око   | центр (155, 160), розмір 130×120 px   |
| Праве око  | центр (325, 160), розмір 130×120 px   |
| Рот        | центр (240, 245)                      |
| Sclera     | білий #FFFFFF                         |
| Outline    | 4 px, #00BFFF, glow ~12 px           |
| Iris       | R=38 px, #00BFFF                      |
| Pupil      | R=20 px, #000000                      |
| Highlight  | R=7 px, білий, зміщення (+12, −14)   |

> ⚠️ Вертикальний центр очей y=160 **ніколи не змінюється** — жодна емоція не рухає очі по вертикалі!

## 🎭 Специфікація емоцій
Повна специфікація: `AIKO специфікація емоцій (Англійська).md`

| Емоція    | Top lid | Bot lid | Зіниця (x,y)       | Eye scale     | Outline     | Рот              | Extras                  |
|-----------|---------|---------|---------------------|---------------|-------------|------------------|-------------------------|
| neutral   | 0%      | 0%      | (0, 0)              | 1.0           | #00BFFF     | curve +4, w=50   | —                       |
| happy     | 0%      | 10%     | (0, 0)              | 1.0–1.02      | #00BFFF     | curve +18, w=70  | highlight twinkle       |
| surprised | 0%      | 0%      | (0,0) iris R30 p R14| 1.12          | #00BFFF     | round «o», w=22  | sparks                  |
| sad       | 35%     | 0%      | (0, +12)            | 1.0           | #00BFFF 70% | curve −12, w=50  | tears                   |
| angry     | 40%     | 0%      | (±6 inward, 0)      | 1.0           | #FF2200     | zigzag, w=60     | red bg pulse, shake     |
| thinking  | 0%      | R: 30%  | (+14, −14)          | 1.0           | #00BFFF     | sideways, w=35   | формули над очима       |
| love      | 0%      | 10%     | hearts centered     | 1.0           | #FF4FA3     | curve +14, w=60  | pulse, blush, hearts    |
| confused  | R: 25%  | 0%      | L(−10,−8) R(+8,+6)  | L:1.08 / R:1.0| #00BFFF     | wavy line, w=55  | «?» над правим оком     |
| sleep     | 50%     | 50%     | —                   | 1.0           | #00BFFF 40% | oval open 0.3–0.5| breathing, «z z z»      |
| listening | 0%      | 0%      | (0,0) iris R=41     | 1.05          | #00BFFF     | w=30, curve +2   | loudness bars           |
| speaking  | з емоції| з емоції| з емоції            | з емоції      | з емоції    | oval, RMS audio  | emphasis nods           |

## ⚡ SPI обмеження та оптимізація
- Повний кадр 480×320 × 16 bit ≈ 300 KB
- При 32 MHz SPI → ~13 fps (повний екран)
- При 48 MHz SPI → ~19 fps (повний екран)
- **Рішення:** `pygame.display.update(dirty_rects)` — оновлюємо лише змінені зони
- В більшості емоцій змінюється ~20–25% екрану → стабільні **25–30 fps**
- ⚠️ Angry (червоний фон) — дорогий ефект! Пульсувати кроками (8–10 рівнів), не кожен кадр

## 🔧 Перевірка
```bash
pip3 show luma.lcd
pip3 show luma.core
python3 -c "from luma.lcd.device import ili9488; print('OK')"
python3 /home/aiko/eyes_v3.py
```
