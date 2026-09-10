cat > /home/aiko/motors.py << 'EOF'
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

ENA = 12
IN1 = 5
IN2 = 6
IN3 = 13
IN4 = 19
ENB = 26

for pin in [ENA, IN1, IN2, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)

pwm_a = GPIO.PWM(ENA, 100)
pwm_b = GPIO.PWM(ENB, 100)
pwm_a.start(0)
pwm_b.start(0)

def set_motors(left_fwd, right_fwd, speed):
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
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

def cleanup():
    stop()
    GPIO.cleanup()
EOF
