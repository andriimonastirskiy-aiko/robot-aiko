cat > /home/aiko/test_tof.py << 'EOF'
import RPi.GPIO as GPIO
import board
import busio
import adafruit_vl53l0x
import time

XSHUT1 = 4
XSHUT2 = 27
XSHUT3 = 22

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(XSHUT1, GPIO.OUT)
GPIO.setup(XSHUT2, GPIO.OUT)
GPIO.setup(XSHUT3, GPIO.OUT)

GPIO.output(XSHUT1, GPIO.LOW)
GPIO.output(XSHUT2, GPIO.LOW)
GPIO.output(XSHUT3, GPIO.LOW)
time.sleep(0.1)

i2c = busio.I2C(board.SCL, board.SDA)

GPIO.output(XSHUT1, GPIO.HIGH)
time.sleep(0.1)
sensor1 = adafruit_vl53l0x.VL53L0X(i2c)
sensor1.set_address(0x30)

GPIO.output(XSHUT2, GPIO.HIGH)
time.sleep(0.1)
sensor2 = adafruit_vl53l0x.VL53L0X(i2c)
sensor2.set_address(0x31)

GPIO.output(XSHUT3, GPIO.HIGH)
time.sleep(0.1)
sensor3 = adafruit_vl53l0x.VL53L0X(i2c)
sensor3.set_address(0x32)

print("Всі сенсори підключені!")

try:
    while True:
        print(f"Спереду: {sensor1.range} мм | Вниз-вперед: {sensor2.range} мм | Вниз-назад: {sensor3.range} мм")
        time.sleep(0.5)
except KeyboardInterrupt:
    GPIO.cleanup()
EOF
