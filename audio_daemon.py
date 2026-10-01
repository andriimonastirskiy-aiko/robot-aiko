cat > /home/aiko/audio_daemon.py << 'EOF'
import subprocess
import os

AUDIO_DEVICE = 'hw:1,0'
FIFO_PATH = '/tmp/audio_fifo'
RECORD_FILE = '/dev/shm/rec.wav'
LOUD_FILE = '/dev/shm/rec_loud.wav'

def write_status(status):
    open('/tmp/audio_status', 'w').write(status)

def record(seconds):
    write_status('recording')
    subprocess.run([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S32_LE', '-r', '48000', '-c', '2',
        '-d', str(seconds), RECORD_FILE
    ], timeout=seconds+3)
    subprocess.run([
        'sox', RECORD_FILE, LOUD_FILE,
        'gain', '20'
    ])
    write_status('ready')

def play():
    write_status('playing')
    subprocess.run(['sox', LOUD_FILE, '-t', 'alsa', AUDIO_DEVICE])
    write_status('ready')

def speak(text):
    write_status('speaking')
    tts = subprocess.Popen([
        'espeak-ng', '-v', 'uk',
        '-s', '120', '-p', '5', '-a', '5',
        text, '--stdout'
    ], stdout=subprocess.PIPE)
    subprocess.run([
        'sox', '-t', 'wav', '-', '-t', 'alsa', AUDIO_DEVICE
    ], stdin=tts.stdout)
    write_status('ready')

if os.path.exists(FIFO_PATH):
    os.remove(FIFO_PATH)
os.mkfifo(FIFO_PATH)

write_status('ready')
print('Аудіо демон запущено!')

while True:
    try:
        with open(FIFO_PATH, 'r') as f:
            cmd = f.read().strip()
        if not cmd:
            continue
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
EOF
