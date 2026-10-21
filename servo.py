# servo.py — тест серво AIKO (±30° від центру, плавний синхронний рух)
# GPIO23 = Серво 1, GPIO24 = Серво 2

import pigpio
import time

# Піни
SERVO1_PIN = 23
SERVO2_PIN = 24

# Центр = 90°, обмеження ±30°
CENTER = 90
LIMIT = 30
STEP_DELAY = 0.01  # 10мс між кроками = швидший рух

def angle_to_us(angle):
    return int(500 + (angle / 180.0) * 2000)

pi = pigpio.pi()

# Поточні позиції серво
current = [CENTER, CENTER]

def set_servo(pin, angle):
    angle = max(CENTER - LIMIT, min(CENTER + LIMIT, angle))
    us = angle_to_us(angle)
    pi.set_servo_pulsewidth(pin, us)

def smooth_move_both(to1, to2):
    """Рухає обидва серво ОДНОЧАСНО, крок за кроком"""
    to1 = max(CENTER - LIMIT, min(CENTER + LIMIT, to1))
    to2 = max(CENTER - LIMIT, min(CENTER + LIMIT, to2))
    from1, from2 = current[0], current[1]
    steps = max(abs(to1 - from1), abs(to2 - from2))
    if steps == 0:
        return
    for i in range(steps + 1):
        a1 = round(from1 + (to1 - from1) * i / steps)
        a2 = round(from2 + (to2 - from2) * i / steps)
        set_servo(SERVO1_PIN, a1)
        set_servo(SERVO2_PIN, a2)
        time.sleep(STEP_DELAY)
    current[0], current[1] = to1, to2

def center():
    print("⏹️  Центруємо...")
    smooth_move_both(CENTER, CENTER)
    print("⏹️  Центр (90°/90°)")

def pan(degrees):
    """Поворот: + вправо, - вліво"""
    a1 = CENTER - degrees
    a2 = CENTER - degrees
    print(f"↔️  Pan {degrees:+}° → S1={a1}°, S2={a2}°")
    smooth_move_both(a1, a2)

def tilt(degrees):
    """Нахил: + вгору, - вниз"""
    a1 = CENTER - degrees
    a2 = CENTER + degrees
    print(f"↕️  Tilt {degrees:+}° → S1={a1}°, S2={a2}°")
    smooth_move_both(a1, a2)

def stop_servos():
    pi.set_servo_pulsewidth(SERVO1_PIN, 0)
    pi.set_servo_pulsewidth(SERVO2_PIN, 0)
    print("🔴 Серво вимкнено (без утримання)")

# ---- ТЕСТ ----
print("🤖 AIKO Servo Test (±30°, синхронний рух)")
center()
time.sleep(1)

print("\n▶️  Тест повороту:")
pan(+30); time.sleep(0.5)
pan(0);   time.sleep(0.5)
pan(-30); time.sleep(0.5)
center(); time.sleep(0.5)

print("\n▶️  Тест нахилу:")
tilt(+30); time.sleep(0.5)
tilt(0);   time.sleep(0.5)
tilt(-10); time.sleep(0.5)
center();  time.sleep(0.5)

stop_servos()
print("✅ Тест завершено!")
pi.stop()
