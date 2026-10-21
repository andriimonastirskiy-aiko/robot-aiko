# servo.py — тест серво AIKO (±30° від центру, плавний рух)
# GPIO23 = Серво 1, GPIO24 = Серво 2

import pigpio
import time

# Піни
SERVO1_PIN = 23
SERVO2_PIN = 24

# Центр = 90°, обмеження ±30°
CENTER = 90
LIMIT = 30
STEP_DELAY = 0.02  # 20мс між кроками = плавний рух

# pigpio: 500-2500мкс = 0-180°
# 90° = 1500мкс, 1° = ~11.1мкс
def angle_to_us(angle):
    return int(500 + (angle / 180.0) * 2000)

pi = pigpio.pi()

# Поточні позиції серво
current = [CENTER, CENTER]

def set_servo(pin, angle):
    angle = max(CENTER - LIMIT, min(CENTER + LIMIT, angle))
    us = angle_to_us(angle)
    pi.set_servo_pulsewidth(pin, us)

def smooth_move(pin, index, to_angle):
    """Плавно переміщує серво від поточної позиції до to_angle"""
    to_angle = max(CENTER - LIMIT, min(CENTER + LIMIT, to_angle))
    from_angle = current[index]
    step = 1 if to_angle > from_angle else -1
    for a in range(from_angle, to_angle + step, step):
        set_servo(pin, a)
        time.sleep(STEP_DELAY)
    current[index] = to_angle

def center():
    print("⏹️  Центруємо...")
    smooth_move(SERVO1_PIN, 0, CENTER)
    smooth_move(SERVO2_PIN, 1, CENTER)
    print("⏹️  Центр (90°/90°)")

def pan(degrees):
    """Поворот: + вправо, - вліво"""
    a1 = CENTER + degrees
    a2 = CENTER + degrees
    print(f"↔️  Pan {degrees:+}° → S1={a1}°, S2={a2}°")
    smooth_move(SERVO1_PIN, 0, a1)
    smooth_move(SERVO2_PIN, 1, a2)

def tilt(degrees):
    """Нахил: + вгору, - вниз"""
    a1 = CENTER + degrees
    a2 = CENTER - degrees
    print(f"↕️  Tilt {degrees:+}° → S1={a1}°, S2={a2}°")
    smooth_move(SERVO1_PIN, 0, a1)
    smooth_move(SERVO2_PIN, 1, a2)

def stop_servos():
    pi.set_servo_pulsewidth(SERVO1_PIN, 0)
    pi.set_servo_pulsewidth(SERVO2_PIN, 0)
    print("🔴 Серво вимкнено (без утримання)")

# ---- ТЕСТ ----
print("🤖 AIKO Servo Test (±30°, плавний рух)")
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
tilt(-30); time.sleep(0.5)
center();  time.sleep(0.5)

stop_servos()
print("✅ Тест завершено!")
pi.stop()
