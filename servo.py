# servo.py — тест серво AIKO (±10° від центру)
# GPIO23 = Серво 1, GPIO24 = Серво 2

import pigpio
import time

# Піни
SERVO1_PIN = 23
SERVO2_PIN = 24

# Центр = 90°, обмеження ±10°
CENTER = 90
LIMIT = 10

# pigpio: 500-2500мкс = 0-180°
# 90° = 1500мкс, 1° = ~11.1мкс
def angle_to_us(angle):
    return int(500 + (angle / 180.0) * 2000)

pi = pigpio.pi()

def set_servo(pin, angle):
    angle = max(CENTER - LIMIT, min(CENTER + LIMIT, angle))
    us = angle_to_us(angle)
    pi.set_servo_pulsewidth(pin, us)

def center():
    set_servo(SERVO1_PIN, CENTER)
    set_servo(SERVO2_PIN, CENTER)
    print("⏹️  Центр (90°/90°)")

def pan(degrees):
    """Поворот: + вправо, - вліво"""
    a1 = CENTER + degrees
    a2 = CENTER + degrees
    set_servo(SERVO1_PIN, a1)
    set_servo(SERVO2_PIN, a2)
    print(f"↔️  Pan {degrees:+}°  → S1={a1}°, S2={a2}°")

def tilt(degrees):
    """Нахил: + вгору, - вниз"""
    a1 = CENTER + degrees
    a2 = CENTER - degrees
    set_servo(SERVO1_PIN, a1)
    set_servo(SERVO2_PIN, a2)
    print(f"↕️  Tilt {degrees:+}° → S1={a1}°, S2={a2}°")

def stop_servos():
    pi.set_servo_pulsewidth(SERVO1_PIN, 0)
    pi.set_servo_pulsewidth(SERVO2_PIN, 0)
    print("🔴 Серво вимкнено (без утримання)")

# ---- ТЕСТ ----
print("🤖 AIKO Servo Test (±10°)")
print("Центруємо...")
center()
time.sleep(1)

print("\n▶️  Тест повороту:")
pan(+10);  time.sleep(1)
pan(0);    time.sleep(0.5)
pan(-10);  time.sleep(1)
center();  time.sleep(1)

print("\n▶️  Тест нахилу:")
tilt(+10); time.sleep(1)
tilt(0);   time.sleep(0.5)
tilt(-10); time.sleep(1)
center();  time.sleep(1)

stop_servos()
print("✅ Тест завершено!")
pi.stop()
