cat > /home/aiko/audio.py << 'EOF'
import subprocess

AUDIO_DEVICE = 'hw:1,0'
RECORD_FILE = '/home/aiko/test.wav'
LOUD_FILE = '/home/aiko/test_loud.wav'

def record(seconds=5, filename=RECORD_FILE):
    try:
        subprocess.run([
            'arecord', '-D', AUDIO_DEVICE,
            '-f', 'S32_LE',
            '-r', '48000',
            '-c', '2',
            '-d', str(seconds),
            filename
        ], timeout=seconds+3)
        subprocess.run([
            'sox', filename, LOUD_FILE, 'gain', '20'
        ])
        return True
    except Exception as e:
        print(f"Помилка запису: {e}")
        return False

def play(filename=LOUD_FILE):
    try:
        subprocess.Popen([
            'sox', filename, '-t', 'alsa', AUDIO_DEVICE
        ])
        return True
    except Exception as e:
        print(f"Помилка відтворення: {e}")
        return False

def play_text(text):
    try:
        tts = subprocess.Popen([
            'espeak-ng', '-v', 'uk',
            '-s', '120',
            '-p', '5',
            '-a', '5',
            text, '--stdout'
        ], stdout=subprocess.PIPE)
        subprocess.Popen([
            'sox', '-t', 'wav', '-', '-t', 'alsa', AUDIO_DEVICE
        ], stdin=tts.stdout)
        return True
    except Exception as e:
        print(f"Помилка TTS: {e}")
        return False
EOF
