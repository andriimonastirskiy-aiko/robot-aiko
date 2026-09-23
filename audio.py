import os
import time

CMD_FILE = '/tmp/audio_cmd'
STATUS_FILE = '/tmp/audio_status'

AUDIO_DEVICE = 'hw:1,0'
RECORD_FILE = '/home/aiko/test.wav'
LOUD_FILE = '/home/aiko/test_loud.wav'

def send_cmd(cmd):
    open(CMD_FILE, 'w').write(cmd)

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
