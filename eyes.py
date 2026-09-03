cat > /home/aiko/eyes.py << 'EOF'
from luma.lcd.device import ili9488
from luma.core.interface.serial import spi
from luma.core.render import canvas
import time

serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=17, bus_speed_hz=8000000)
device = ili9488(serial, width=480, height=320, rotate=0, bgr=True)
device.backlight(True)

def draw_eyes(draw, mood="happy"):
    draw.rectangle((0, 0, 480, 320), fill=(0, 0, 0))
    if mood == "happy":
        draw.ellipse((100, 80, 210, 190), fill=(255, 255, 255))
        draw.ellipse((270, 80, 380, 190), fill=(255, 255, 255))
        draw.ellipse((135, 115, 175, 155), fill=(0, 150, 255))
        draw.ellipse((305, 115, 345, 155), fill=(0, 150, 255))
        draw.ellipse((148, 128, 162, 142), fill=(0, 0, 0))
        draw.ellipse((318, 128, 332, 142), fill=(0, 0, 0))
        draw.arc((160, 230, 320, 290), start=0, end=180, fill=(255, 255, 255), width=5)
    elif mood == "blink":
        draw.ellipse((100, 130, 210, 145), fill=(255, 255, 255))
        draw.ellipse((270, 130, 380, 145), fill=(255, 255, 255))
    elif mood == "surprised":
        draw.ellipse((90, 60, 220, 200), fill=(255, 255, 255))
        draw.ellipse((260, 60, 390, 200), fill=(255, 255, 255))
        draw.ellipse((135, 105, 175, 155), fill=(0, 150, 255))
        draw.ellipse((305, 105, 345, 155), fill=(0, 150, 255))
        draw.ellipse((148, 120, 162, 140), fill=(0, 0, 0))
        draw.ellipse((318, 120, 332, 140), fill=(0, 0, 0))
        draw.ellipse((190, 240, 290, 300), fill=(255, 255, 255))
    elif mood == "sad":
        draw.ellipse((100, 80, 210, 190), fill=(255, 255, 255))
        draw.ellipse((270, 80, 380, 190), fill=(255, 255, 255))
        draw.ellipse((135, 115, 175, 155), fill=(0, 100, 200))
        draw.ellipse((305, 115, 345, 155), fill=(0, 100, 200))
        draw.ellipse((148, 128, 162, 142), fill=(0, 0, 0))
        draw.ellipse((318, 128, 332, 142), fill=(0, 0, 0))
        draw.arc((160, 260, 320, 300), start=180, end=360, fill=(255, 255, 255), width=5)

print("AIKO емоції! Ctrl+C щоб зупинити")

try:
    while True:
        with canvas(device) as draw:
            draw_eyes(draw, "happy")
        time.sleep(3)
        with canvas(device) as draw:
            draw_eyes(draw, "blink")
        time.sleep(0.15)
        with canvas(device) as draw:
            draw_eyes(draw, "happy")
        time.sleep(2)
        with canvas(device) as draw:
            draw_eyes(draw, "surprised")
        time.sleep(2)
        with canvas(device) as draw:
            draw_eyes(draw, "blink")
        time.sleep(0.15)
        with canvas(device) as draw:
            draw_eyes(draw, "sad")
        time.sleep(2)
except KeyboardInterrupt:
    pass
EOF
