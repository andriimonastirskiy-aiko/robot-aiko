cat > /home/aiko/safety.py << 'EOF'
import threading
import time
import motors

OBSTACLE_LIMIT = 150
CLIFF_LIMIT = 200

current_direction = 'stop'
running = True

def set_direction(direction):
    global current_direction
    current_direction = direction

def safety_loop(sensor_data):
    global current_direction
    while running:
        try:
            if current_direction != 'stop':
                front = sensor_data['front']
                cliff_front = sensor_data['cliff_front']
                cliff_back = sensor_data['cliff_back']

                if current_direction == 'forward':
                    if (front < OBSTACLE_LIMIT and front > 0) or cliff_front > CLIFF_LIMIT:
                        motors.stop()
                        current_direction = 'stop'

                if current_direction == 'backward':
                    if cliff_back > CLIFF_LIMIT:
                        motors.stop()
                        current_direction = 'stop'

        except:
            pass
        time.sleep(0.1)

def start(sensor_data):
    t = threading.Thread(target=safety_loop, args=(sensor_data,), daemon=True)
    t.start()
EOF
