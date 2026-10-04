import threading
import time

OBSTACLE_LIMIT = 200  # менше 200мм спереду — стоп
CLIFF_LIMIT = 80      # більше 80мм вниз — край столу, стоп

sensor_data = {'front': 0, 'cliff_front': 0, 'cliff_back': 0}
_lock = threading.Lock()
_moving = False
_direction = 'stop'   # ✅ 'forward' / 'backward' / 'left' / 'right' / 'stop'
_stop_callback = None
_available = False

def _try_init():
    global _available
    try:
        import RPi.GPIO as GPIO
        import board
        import busio
        import adafruit_vl53l0x

        XSHUT1, XSHUT2, XSHUT3 = 4, 27, 22
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in [XSHUT1, XSHUT2, XSHUT3]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        time.sleep(0.1)

        i2c = busio.I2C(board.SCL, board.SDA)
        GPIO.output(XSHUT1, GPIO.HIGH); time.sleep(0.1)
        s1 = adafruit_vl53l0x.VL53L0X(i2c); s1.set_address(0x30)
        GPIO.output(XSHUT2, GPIO.HIGH); time.sleep(0.1)
        s2 = adafruit_vl53l0x.VL53L0X(i2c); s2.set_address(0x31)
        GPIO.output(XSHUT3, GPIO.HIGH); time.sleep(0.1)
        s3 = adafruit_vl53l0x.VL53L0X(i2c); s3.set_address(0x32)

        _available = True
        print("Сенсори підключені!")

        while True:
            try:
                with _lock:
                    sensor_data['front'] = s1.range
                    sensor_data['cliff_front'] = s2.range
                    sensor_data['cliff_back'] = s3.range
                _check_safety()
            except:
                pass
            time.sleep(0.05)

    except Exception as e:
        print(f"Сенсори не знайдені — продовжуємо без них")

def init():
    t = threading.Thread(target=_try_init, daemon=True)
    t.start()

def set_moving(moving, direction='stop', stop_cb=None):
    """
    moving    — True/False чи робот рухається
    direction — напрямок: 'forward' / 'backward' / 'left' / 'right' / 'stop'
    stop_cb   — функція яку викликати при небезпеці
    """
    global _moving, _direction, _stop_callback
    _moving = moving
    _direction = direction
    _stop_callback = stop_cb

def _check_safety():
    if not _moving:
        return
    d = sensor_data
    danger = False

    # ✅ Перевіряємо тільки те що небезпечно для ПОТОЧНОГО напрямку
    if _direction == 'forward':
        if d['front'] < OBSTACLE_LIMIT and d['front'] > 0:
            danger = True   # перешкода спереду
            print("⚠️ перешкода спереду — блокую forward")
        if d['cliff_front'] > CLIFF_LIMIT:
            danger = True   # край столу спереду
            print("⚠️ край столу спереду — блокую forward")

    elif _direction == 'backward':
        if d['cliff_back'] > CLIFF_LIMIT:
            danger = True   # край столу ззаду
            print("⚠️ край столу ззаду — блокую backward")

    # ✅ left / right — не блокуємо (повороти на місці безпечні)

    if danger and _stop_callback:
        _stop_callback()

def get_data():
    with _lock:
        return dict(sensor_data)

def is_safe(direction):
    if not _available:
        return True, 'ok'
    d = get_data()
    if direction == 'forward':
        if d['front'] < OBSTACLE_LIMIT and d['front'] > 0:
            return False, 'перешкода спереду (менше 200мм)'
        if d['cliff_front'] > CLIFF_LIMIT:
            return False, 'край столу спереду!'
    if direction == 'backward':
        if d['cliff_back'] > CLIFF_LIMIT:
            return False, 'край столу ззаду!'
    return True, 'ok'
