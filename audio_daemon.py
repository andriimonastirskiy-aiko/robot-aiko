cat > /home/aiko/audio_daemon.py << 'EOF'
import subprocess
import time
import os

AUDIO_DEVICE = 'hw:1,0'
RECORD_FILE = '/home/aiko/test.wav'
LOUD_FILE = '/home/aiko/test_loud.wav'
CMD_FILE = '/tmp/audio_cmd'
STATUS_FILE = '/tmp/audio_status'

def write_status(status):
    open(STATUS_FILE, 'w').write(status)

def record(seconds):
    write_status('recording')
    subprocess.run([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S32_LE', '-r', '48000', '-c', '2',
        '-d', str(seconds), RECORD_FILE
    ], timeout=seconds+3)
    subprocess.run(['sox', RECORD_FILE, LOUD_FILE, 'gain', '20'])
    write_status('ready')

def play():
    write_status('playing')
    subprocess.run(['sox', LOUD_FILE, '-t', 'alsa', AUDIO_DEVICE])
    write_status('ready')

def speak(text):
    write_status('speaking')
    tts = subprocess.Popen([
        'espeak-ng', '-v', 'uk', '-s', '120', '-p', '5', '-a', '5',
        text, '--stdout'
    ], stdout=subprocess.PIPE)
    subprocess.run([
        'sox', '-t', 'wav', '-', '-t', 'alsa', AUDIO_DEVICE
    ], stdin=tts.stdout)
    write_status('ready')

write_status('ready')
print('Аудіо демон запущено!')

while True:
    try:
        if os.path.exists(CMD_FILE):
            cmd = open(CMD_FILE).read().strip()
            os.remove(CMD_FILE)
            parts = cmd.split('|')
            if parts[0] == 'record':
                record(int(parts[1]))
            elif parts[0] == 'play':
                play()
            elif parts[0] == 'speak':
                speak(parts[1])
    except Exception as e:
        print(f"Помилка: {e}")
        write_status('ready')
    time.sleep(0.1)
EOF
