import atexit
import RPi.GPIO as GPIO

# ==== Піни L298N (за паспортом AIKO) ====
ENA = 12
IN1 = 5
IN2 = 6
IN3 = 13
IN4 = 16   # ✅ Було GPIO19 (конфлікт з I2S WS/LRC) — перенесено на GPIO16
ENB = 26

# ==== Ініціалізація GPIO ====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [ENA, IN1, IN2, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)

pwm_a = GPIO.PWM(ENA, 100)
pwm_b = GPIO.PWM(ENB, 100)
pwm_a.start(0)
pwm_b.start(0)

_cleaned_up = False


def _clamp_speed(speed):
    """Обмежує швидкість діапазоном 0–100."""
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, speed))


def set_motors(left_fwd, right_fwd, speed):
    if _cleaned_up:
        return
    speed = _clamp_speed(speed)

    if right_fwd:
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)
    else:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

    if left_fwd:
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)
    else:
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

    pwm_a.ChangeDutyCycle(speed)
    pwm_b.ChangeDutyCycle(speed)


def forward(speed=50):
    set_motors(left_fwd=True, right_fwd=True, speed=speed)


def backward(speed=50):
    set_motors(left_fwd=False, right_fwd=False, speed=speed)


def left(speed=50):
    set_motors(left_fwd=False, right_fwd=True, speed=speed)


def right(speed=50):
    set_motors(left_fwd=True, right_fwd=False, speed=speed)


def stop():
    if _cleaned_up:
        return
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)


def cleanup():
    """Безпечно зупиняє мотори та звільняє GPIO (можна викликати кілька разів)."""
    global _cleaned_up
    if _cleaned_up:
        return
    stop()
    pwm_a.stop()
    pwm_b.stop()
    GPIO.cleanup()
    _cleaned_up = True


# Автоматична зупинка моторів при виході з програми
atexit.register(cleanup)
