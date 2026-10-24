# 🤖 AIKO — Домашній Робот

Проект домашнього робота для дітей дошкільного віку з функціями гри,
навчання та ШІ-взаємодії на базі Raspberry Pi.

---

## 🧠 Технічний паспорт

### Мозок
- **Raspberry Pi Zero 2W** → IP: `192.168.0.103` | User: `aiko`
- Python 3.13 | OS: Debian trixie
- ✅ **Raspberry Pi 4 4GB отримано!** — готується до переходу

### 🚗 Драйвер моторів — L298N
| Сигнал | GPIO |
|--------|------|
| ENA    | 12   |
| IN1    | 5    |
| IN2    | 6    |
| IN3    | 13   |
| IN4    | 16 ⚠️ (перенесено з GPIO19 через конфлікт з I2S) |
| ENB    | 26   |

### 🔊 Аудіо I2S
| Компонент | Сигнал | GPIO |
|-----------|--------|------|
| INMP441 + MAX98357A | SCK/BCLK | 18 |
| INMP441 + MAX98357A | WS/LRC | 19 |
| MAX98357A | DIN | 21 |
| INMP441 | SD | 20 |

> ⚠️ **Конфлікт:** GPIO19 ділять I2S (WS/LRC) та L298N (IN4 — перенесено на GPIO16)

### 📡 Сенсори ToF — 3x VL53L0X (без мультиплексора)
| Позиція | Адреса I2C | XSHUT GPIO |
|---------|-----------|------------|
| Фронт | 0x30 | 4 |
| Вниз-Перед | 0x31 | 27 |
| Вниз-Зад | 0x32 | 22 |
- Перешкода спереду: < 200 мм → стоп
- Край столу: > 80 мм вниз → стоп

### 🖥️ Дисплей — ILI9488 3.5" SPI (luma.lcd)
| Сигнал | GPIO |
|--------|------|
| MOSI | 10 |
| SCK | 11 |
| CS | 8 |
| DC | 25 |
| RESET | 17 |

### 🤖 Серво голови (диференціальний механізм)
| Сигнал | GPIO |
|--------|------|
| Pan (Servo 1) | 23 |
| Tilt (Servo 2) | 24 |
- 2x SG90 180°
- ✅ **Підключено та протестовано!** pan ±30°, tilt +30°/-10°, плавний рух (pigpio)

### 🔘 Кнопка керування
| Сигнал | GPIO | Фізичний пін |
|--------|------|--------------|
| Кнопка (wake/sleep) | 17 | 11 |
- Схема: **GPIO17 → кнопка → GND**
- Вбудований pull-up резистор Pi → зовнішній резистор НЕ потрібен!
- Код: `GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)`
- ⚠️ GPIO3 не використовуємо — зайнятий I2C (сенсори VL53L0X)

---

## 📁 Файли проєкту

| Файл | Опис | Статус |
|------|------|--------|
| `eyes_v3.py` | Система емоцій (ILI9488, 11 емоцій, pygame, FIFO керування) | ✅ Фінальний |
| `motors.py` | Керування моторами L298N | ✅ Фінальний |
| `sensor_manager.py` | ToF сенсори VL53L0X, захист від падіння | ✅ Фінальний |
| `audio_daemon.py` | I2S аудіо INMP441 + MAX98357A, TTS | ✅ Фінальний |
| `web_server.py` | Веб-панель керування Flask (порт 5000) | ✅ Фінальний |
| `servo.py` | Серво голови GPIO23/24, pan ±30°, tilt +30°/-10° | ✅ Фінальний |
| `face.py` | Міст між brain.py та eyes_v3 (FIFO/сокет) | 🔜 Крок 1 |
| `talker.py` | GPT-4o-mini + TTS + емоції | 🔜 Крок 2 |
| `listener.py` | Запис мікрофону + Whisper STT | 🔜 Крок 3 |
| `mover.py` | Обгортка motors + servo (nod, shake тощо) | 🔜 Крок 4 |
| `brain.py` | Головний цикл (кнопка → STT → GPT → дія) | 🔜 Крок 5 |

---

## 🧠 OpenAI — ШІ Інтеграція

- Модель: `gpt-4o-mini`
- STT: Whisper API (`openai.audio.transcriptions.create()`)
- Ключ: `/home/aiko/.env` → `OPENAI_API_KEY`
- Бібліотека: `openai` (Python)
- ✅ Тест пройдено — AIKO відповідає через GPT-4o-mini

---

## 👁️ eyes_v3.py — Система емоцій (ФІНАЛЬНА)

- Canvas: 480×320, pygame + SDL2
- Дисплей: luma.lcd ILI9488, BGR swap (`[:, :, ::-1]`)
- Переходи: миттєві, без lerp
- Керування: `echo "emotion" > /tmp/aiko_emotion`
- Коміт: `dd496aa2`

| Емоція | Ефекти |
|--------|--------|
| neutral | Авто-моргання |
| happy | Широка усмішка |
| surprised | Іскри SparkManager |
| sad | Сльози TearManager |
| angry | Червоний фон #3A0000, зигзаг |
| thinking | Формули FormulaManager |
| love | Серця + рум'янець HeartManager |
| confused | Знак питання, хвилястий рот |
| sleep | ZZZ-анімація, дихання |
| listening | Смужки гучності LoudnessBars |
| speaking | Відкритий рот |

---

## 🚗 motors.py — Мотори (ФІНАЛЬНИЙ)

- Драйвер: L298N
- IN4 на GPIO**16** (перенесено з GPIO19)
- PWM 100Hz на ENA/ENB
- Функції: `forward()`, `backward()`, `left()`, `right()`, `stop()`, `cleanup()`
- Auto-cleanup через `atexit`

---

## 📡 sensor_manager.py — Сенсори (ФІНАЛЬНИЙ)

- 3x VL53L0X через XSHUT адресацію
- Потокова робота (daemon thread, 50мс)
- Розумна безпека: блокує тільки небезпечний напрямок
  - `forward` → перевіряє спереду + вниз-вперед
  - `backward` → перевіряє вниз-назад
  - `left/right` → не блокує (повороти безпечні)
- Graceful fallback якщо сенсори не підключені

---

## 🔊 audio_daemon.py — Аудіо (ФІНАЛЬНИЙ)

- Мікрофон: INMP441 (I2S, `hw:1,0`, 48кГц, S32_LE, 2ch)
- Динамік: MAX98357A через sox
- Гучність: `15.0` (оптимально на 20 см)
- Підсилення запису: `gain 20` через sox
- TTS: espeak-ng (`-v uk -s 120 -p 5 -a 5`)
- FIFO: `/tmp/audio_fifo` | Статус: `/tmp/audio_status`
- Команди: `record|N`, `play`, `speak|текст`

---

## 🌐 web_server.py — Веб-панель (ФІНАЛЬНА)

- URL: `http://192.168.0.103:5000`
- Framework: Flask
- Сторінки: Керування / Аудіо / Інформація
- Watchdog: 0.3 сек (авто-стоп якщо клієнт відвалився)
- Live сенсори: оновлення кожні 200мс
- Захист від мікро-дотиків: MIN_HOLD_MS = 120мс

---

## 🤖 servo.py — Серво голови (ФІНАЛЬНИЙ)

- 2x SG90 180°, диференціальний механізм
- Pan: GPIO23, Tilt: GPIO24
- Діапазон: pan ±30°, tilt +30°/-10°
- Бібліотека: pigpio (плавний PWM)
- Функції: `pan()`, `tilt()`, `center()`, `cleanup()`

---

## 🚀 Запуск

```bash
# Клонувати
git clone https://github.com/andriimonastirskiy-aiko/robot-aiko.git
cd robot-aiko

# Веб-панель (основний режим)
python3 web_server.py

# Тест очей
python3 eyes_v3.py

# Аудіо демон (окремий термінал)
python3 audio_daemon.py

# Серво голови
python3 servo.py

# Керування емоціями вручну (другий термінал)
echo "happy" > /tmp/aiko_emotion
echo "sad" > /tmp/aiko_emotion
echo "angry" > /tmp/aiko_emotion
```

---

## ⏳ План розробки brain.py — Поетапно

### Рішення прийняті:
- **STT:** Whisper API (той самий ключ OpenAI — один ключ, дві функції!)
- **Wake:** Кнопка GPIO17 — режим вмик/вимик (натиснув → слухає, ще раз → спить)
- **Мова відповідей:** Українська
- **Wake word "Привіт Айко":** openWakeWord — Крок 6 (пізніше, безкоштовно, офлайн)

---

### 📦 Крок 1 — `face.py` (міст до дисплею)
- [ ] Надсилає команди емоцій до `eyes_v3.py` через FIFO/сокет
- [ ] Тест: `face.set_emotion("happy")` → дисплей реагує

### 🗣️ Крок 2 — `talker.py` (GPT + TTS)
- [ ] Системний промпт: GPT повертає `{"reply": "...", "emotion": "...", "action": "..."}`
- [ ] Інтеграція з `audio_daemon.py` (TTS через espeak-ng)
- [ ] Тест: запит текстом → відповідь → емоція на дисплеї

### 👂 Крок 3 — `listener.py` (мікрофон + Whisper STT)
- [ ] Запис через `audio_daemon.py`
- [ ] Транскрипція через Whisper API
- [ ] Тест: сказав → текст у терміналі

### 🏃 Крок 4 — `mover.py` (рухи голови)
- [ ] Обгортка над `motors.py` + `servo.py`
- [ ] Actions: `nod`, `shake`, `turn_left`, `turn_right`, `idle`
- [ ] Тест: `action="nod"` → голова кивнула

### 🧠 Крок 5 — `brain.py` (головний цикл)
- [ ] Кнопка GPIO17 → вмик/вимик режиму слухання
- [ ] Цикл: запис → STT (Whisper) → GPT → емоція + TTS + рух
- [ ] Тест: повний цикл розмови від А до Я

### 🎙️ Крок 6 — Wake word (опційно, пізніше)
- [ ] openWakeWord "Привіт Айко" замість кнопки
- [ ] Безкоштовно, офлайн, без зовнішніх API

---

## ✅ Вирішені проблеми

| Проблема | Рішення |
|----------|---------| 
| GPIO19 конфлікт L298N + I2S | ✅ IN4 перенесено на GPIO16 |
| Серво конфлікт з L298N (GPIO12/13) | ✅ Серво переназначено на GPIO23/24 |
| Google Voice HAT драйвер | ✅ Звук працює, залишаємо |
| Синій фон замість червоного на ILI9488 | ✅ BGR swap врахований в eyes_v3 |
| Кнопка GPIO3 конфлікт з I2C (VL53L0X) | ✅ Кнопка переназначена на GPIO17 |
| FIFO нескінченний цикл в eyes_v3 | ✅ `for line in f` + `if not cmd: continue` |
