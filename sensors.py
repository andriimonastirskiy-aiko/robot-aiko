import board
import busio
import adafruit_vl53l0x
import RPi.GPIO as GPIO
import time

XSHUT1 = 4
XSHUT2 = 27
XSHUT3 = 22

OBSTACLE_LIMIT = 150
CLIFF_LIMIT = 200

def init_sensors():
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
    return sensor1, sensor2, sensor3

def read_sensors(sensor1, sensor2, sensor3):
    front = sensor1.range
    cliff_front = sensor2.range
    cliff_back = sensor3.range
    return front, cliff_front, cliff_back

def is_safe(front, cliff_front, cliff_back, direction):
    if direction == 'forward':
        if front < OBSTACLE_LIMIT and front > 0:
            return False, 'перешкода спереду'
        if cliff_front > CLIFF_LIMIT:
            return False, 'край спереду'
    if direction == 'backward':
        if cliff_back > CLIFF_LIMIT:
            return False, 'край ззаду'
    return True, 'ok'
  
