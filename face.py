#!/usr/bin/env python3
"""
AIKO face.py — міст між brain.py та eyes_v3.py
Надсилає команди емоцій через FIFO /tmp/aiko_emotion

Використання:
  from face import set_emotion
  set_emotion("happy")
  set_emotion("sad")
"""

import os
import time

FIFO_PATH = "/tmp/aiko_emotion"
VALID_EMOTIONS = [
    "neutral", "happy", "surprised", "sad", "angry",
    "thinking", "love", "confused", "sleep", "listening", "speaking"
]

def set_emotion(emotion: str, wait_ms: int = 0) -> bool:
    """
    Надсилає емоцію до eyes_v3.py через FIFO.
    emotion  — назва емоції (рядок)
    wait_ms  — затримка після надсилання (мс)
    Повертає True якщо успішно, False якщо помилка.
    """
    if emotion not in VALID_EMOTIONS:
        print(f"[FACE] ⚠️ Невідома емоція: '{emotion}'. "
              f"Доступні: {VALID_EMOTIONS}")
        return False

    if not os.path.exists(FIFO_PATH):
        print(f"[FACE] ⚠️ FIFO не знайдено: {FIFO_PATH} "
              f"(eyes_v3.py не запущено?)")
        return False

    try:
        with open(FIFO_PATH, "w") as f:
            f.write(emotion + "\n")
        print(f"[FACE] ✅ → {emotion}")
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0)
        return True
    except Exception as e:
        print(f"[FACE] ❌ Помилка надсилання: {e}")
        return False


def neutral(wait_ms=0):   return set_emotion("neutral",   wait_ms)
def happy(wait_ms=0):     return set_emotion("happy",     wait_ms)
def surprised(wait_ms=0): return set_emotion("surprised", wait_ms)
def sad(wait_ms=0):       return set_emotion("sad",       wait_ms)
def angry(wait_ms=0):     return set_emotion("angry",     wait_ms)
def thinking(wait_ms=0):  return set_emotion("thinking",  wait_ms)
def love(wait_ms=0):      return set_emotion("love",      wait_ms)
def confused(wait_ms=0):  return set_emotion("confused",  wait_ms)
def sleep(wait_ms=0):     return set_emotion("sleep",     wait_ms)
def listening(wait_ms=0): return set_emotion("listening", wait_ms)
def speaking(wait_ms=0):  return set_emotion("speaking",  wait_ms)


# ── Тест при прямому запуску ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # Якщо передано аргумент — надсилаємо конкретну емоцію
    if len(sys.argv) > 1:
        em = sys.argv[1].strip()
        set_emotion(em)
        sys.exit(0)

    # Інакше — авто-тест всіх емоцій по 2 секунди
    print("[FACE] 🧪 Авто-тест всіх емоцій (потрібен запущений eyes_v3.py)")
    for em in VALID_EMOTIONS:
        ok = set_emotion(em)
        if ok:
            time.sleep(2)
    print("[FACE] ✅ Тест завершено")
