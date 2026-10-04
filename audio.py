FIFO_PATH = '/tmp/audio_fifo'
STATUS_FILE = '/tmp/audio_status'

def send_cmd(cmd):
    try:
        with open(FIFO_PATH, 'w') as f:
            f.write(cmd)
    except Exception as e:
        print(f"Помилка відправки команди: {e}")

def get_status():
    try:
        return open(STATUS_FILE).read().strip()
    except:
        return 'unknown'

def record(seconds=5, filename=None):
    send_cmd(f'record|{seconds}')
    return True

def play(filename=None):
    send_cmd('play')
    return True

def play_text(text):
    send_cmd(f'speak|{text}')
    return True
