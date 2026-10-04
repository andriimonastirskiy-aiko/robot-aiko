from flask import Flask, render_template_string, jsonify, request
import motors
import sensor_manager
import audio
import threading
import time
import os

app = Flask(__name__)

sensor_manager.init()

last_cmd_time = time.time()
WATCHDOG_TIMEOUT = 0.3

def watchdog_loop():
    while True:
        if time.time() - last_cmd_time > WATCHDOG_TIMEOUT:
            motors.stop()
            sensor_manager.set_moving(False)
        time.sleep(0.05)

threading.Thread(target=watchdog_loop, daemon=True).start()

def get_sys_info():
    try:
        with open('/proc/stat') as f:
            cpu = f.readline().split()
        idle = int(cpu[4])
        total = sum(int(x) for x in cpu[1:])
        cpu_pct = round(100 * (1 - idle / total))
    except:
        cpu_pct = 0
    try:
        with open('/proc/meminfo') as f:
            lines = f.readlines()
        mem = {l.split(':')[0]: int(l.split()[1]) for l in lines[:5]}
        ram = (mem['MemTotal'] - mem['MemAvailable']) // 1024
    except:
        ram = 0
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp = round(int(f.read()) / 1000, 1)
    except:
        temp = 0
    return cpu_pct, ram, temp

HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIKO debug panel</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: sans-serif; background: #f5f5f5; color: #111; }
.topbar { background: white; border-bottom: 1px solid #e5e5e5; padding: 12px 16px; display: flex; align-items: center; gap: 12px; }
.logo { font-size: 15px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }
.nav { margin-left: auto; display: flex; gap: 4px; flex-wrap: wrap; }
.nav-btn { padding: 6px 14px; border-radius: 8px; border: 1px solid #e5e5e5; background: transparent; font-size: 13px; cursor: pointer; }
.nav-btn.active { background: #f5f5f5; font-weight: 500; }
.content { padding: 16px; max-width: 700px; margin: 0 auto; }
.page { display: none; }
.page.active { display: block; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.card { background: white; border: 1px solid #e5e5e5; border-radius: 12px; padding: 14px 16px; }
.card-title { font-size: 11px; color: #888; margin-bottom: 8px; }
.joystick-wrap { display: flex; flex-direction: column; align-items: center; gap: 6px; margin: 8px 0; }
.joy-row { display: flex; gap: 6px; }
.joy-btn { width: 52px; height: 52px; border-radius: 10px; border: 1px solid #ddd; background: #f9f9f9; cursor: pointer; font-size: 20px; transition: all 0.1s; user-select: none; -webkit-user-select: none; }
.joy-btn:active { background: #dbeafe; border-color: #93c5fd; transform: scale(0.95); }
.joy-btn.stop { background: #fee2e2; border-color: #fca5a5; font-size: 13px; font-weight: 500; color: #dc2626; }
.joy-btn.pressed { background: #dbeafe; border-color: #93c5fd; transform: scale(0.95); }
.slider-wrap { margin-bottom: 12px; }
.slider-label { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-bottom: 6px; }
.slider-val { color: #111; font-weight: 500; }
input[type=range] { width: 100%; }
.sensor-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.sensor-row:last-child { border-bottom: none; }
.sensor-name { font-size: 13px; color: #888; }
.sensor-val { font-size: 13px; font-weight: 500; font-family: monospace; }
.log-box { background: #1a1a1a; border-radius: 8px; padding: 10px; font-family: monospace; font-size: 11px; color: #888; height: 120px; overflow-y: auto; margin-top: 10px; }
.log-line { margin-bottom: 3px; }
.ok { color: #22c55e; }
.warn { color: #f59e0b; }
.alert-bar { display: none; background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #dc2626; font-weight: 500; margin-bottom: 12px; }
.alert-bar.show { display: block; }
.audio-btn { width: 100%; padding: 14px; border-radius: 10px; border: 1px solid #ddd; background: #f9f9f9; cursor: pointer; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
.audio-btn.green { background: #dcfce7; border-color: #86efac; color: #15803d; }
.audio-btn.blue { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; }
.tts-input { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #ddd; font-size: 13px; margin-bottom: 8px; }
</style>
</head>
<body>
<div class="topbar">
  <div class="logo"><div class="dot"></div> AIKO debug panel</div>
  <div style="font-size:11px;color:#aaa;">192.168.0.103:5000</div>
  <div class="nav">
    <button class="nav-btn active" onclick="showPage('control',this)">Керування</button>
    <button class="nav-btn" onclick="showPage('audio',this)">Аудіо</button>
    <button class="nav-btn" onclick="showPage('info',this)">Інформація</button>
  </div>
</div>
<div class="content">

  <div class="page active" id="page-control">
    <div id="alert-bar" class="alert-bar">⚠️ <span id="alert-msg">Небезпека!</span></div>
    <div class="grid-2" style="margin-top:12px">
      <div class="card">
        <div class="card-title">Рух (танкове керування)</div>
        <div class="joystick-wrap">
          <div class="joy-row">
            <div style="width:52px"></div>
            <button class="joy-btn" id="btn-forward"
              onmousedown="startCmd('forward')" onmouseup="stopCmd()"
              onmouseleave="stopCmd()"
              ontouchstart="startCmd('forward');event.preventDefault()" ontouchend="stopCmd()">↑</button>
            <div style="width:52px"></div>
          </div>
          <div class="joy-row">
            <button class="joy-btn" id="btn-left"
              onmousedown="startCmd('left')" onmouseup="stopCmd()"
              onmouseleave="stopCmd()"
              ontouchstart="startCmd('left');event.preventDefault()" ontouchend="stopCmd()">←</button>
            <button class="joy-btn stop" onmousedown="stopCmd()" ontouchstart="stopCmd();event.preventDefault()">STOP</button>
            <button class="joy-btn" id="btn-right"
              onmousedown="startCmd('right')" onmouseup="stopCmd()"
              onmouseleave="stopCmd()"
              ontouchstart="startCmd('right');event.preventDefault()" ontouchend="stopCmd()">→</button>
          </div>
          <div class="joy-row">
            <div style="width:52px"></div>
            <button class="joy-btn" id="btn-backward"
              onmousedown="startCmd('backward')" onmouseup="stopCmd()"
              onmouseleave="stopCmd()"
              ontouchstart="startCmd('backward');event.preventDefault()" ontouchend="stopCmd()">↓</button>
            <div style="width:52px"></div>
          </div>
        </div>
        <div class="slider-wrap">
          <div class="slider-label"><span>Швидкість</span><span class="slider-val" id="spd-val">30%</span></div>
          <input type="range" min="0" max="100" value="30" id="speed-slider"
            oninput="speed=parseInt(this.value); document.getElementById('spd-val').textContent=this.value+'%'">
        </div>
      </div>
      <div class="card">
        <div class="card-title">Сенсори (live)</div>
        <div class="sensor-row"><span class="sensor-name">Спереду</span><span class="sensor-val" id="live-front">— мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Вниз-вперед</span><span class="sensor-val" id="live-cf">— мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Вниз-назад</span><span class="sensor-val" id="live-cb">— мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Cliff alarm</span><span class="sensor-val" id="live-cliff" style="color:#22c55e">ні</span></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Лог команд</div>
      <div class="log-box" id="log-box">
        <div class="log-line"><span class="ok">● Система готова</span></div>
      </div>
    </div>
  </div>

  <div class="page" id="page-audio">
    <div class="card" style="margin-top:12px; margin-bottom:12px">
      <div class="card-title">Мікрофон — тест запису</div>
      <div class="slider-wrap">
        <div class="slider-label"><span>Тривалість</span><span class="slider-val" id="rec-dur-val">5 сек</span></div>
        <input type="range" min="2" max="15" value="5" id="rec-dur" oninput="document.getElementById('rec-dur-val').textContent=this.value+' сек'">
      </div>
      <button class="audio-btn" id="btn-record" onclick="startRecord()">🎤 Записати</button>
      <button class="audio-btn blue" onclick="playRecord()">▶ Відтворити запис</button>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-title">Динамік — TTS</div>
      <input class="tts-input" type="text" id="tts-text" placeholder="Введи текст..." value="Привіт я AIKO">
      <button class="audio-btn green" onclick="speakText()">🔊 Озвучити</button>
    </div>
    <div class="card">
      <div class="card-title">Лог аудіо</div>
      <div class="log-box" id="audio-log">
        <div class="log-line"><span class="ok">● Аудіо готове</span></div>
      </div>
    </div>
  </div>

  <div class="page" id="page-info">
    <div class="card" style="margin-top:12px; margin-bottom:12px">
      <div class="card-title">ToF сенсори</div>
      <div class="sensor-row"><span class="sensor-name">Спереду</span><span class="sensor-val" id="val-front">— мм</span></div>
      <div class="sensor-row"><span class="sensor-name">Вниз-вперед</span><span class="sensor-val" id="val-cf">— мм</span></div>
      <div class="sensor-row"><span class="sensor-name">Вниз-назад</span><span class="sensor-val" id="val-cb">— мм</span></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Система</div>
        <div class="sensor-row"><span class="sensor-name">CPU</span><span class="sensor-val" id="val-cpu">—%</span></div>
        <div class="sensor-row"><span class="sensor-name">RAM</span><span class="sensor-val" id="val-ram">— MB</span></div>
        <div class="sensor-row"><span class="sensor-name">Температура</span><span class="sensor-val" id="val-temp">—°C</span></div>
      </div>
      <div class="card">
        <div class="card-title">Ліміти безпеки</div>
        <div class="sensor-row"><span class="sensor-name">Перешкода</span><span class="sensor-val">150 мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Край столу</span><span class="sensor-val">200 мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Watchdog</span><span class="sensor-val">0.3 сек</span></div>
      </div>
    </div>
  </div>

</div>
<script>
// ======= Фікс 3: speed завжди береться зі слайдера =======
var slider = document.getElementById('speed-slider');
var speed = parseInt(slider.value);

slider.addEventListener('input', function() {
  speed = parseInt(this.value);
  document.getElementById('spd-val').textContent = this.value + '%';
});

var cmdInterval = null;
var infoActive = false;
// ======= Фікс 1: мінімальний час утримання =======
var pressStartTime = 0;
var MIN_HOLD_MS = 120;
var currentDirection = null;

function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  btn.classList.add('active');
  infoActive = (name === 'info');
}

function addLog(msg, type, boxId) {
  var box = document.getElementById(boxId || 'log-box');
  var d = document.createElement('div');
  d.className = 'log-line';
  var t = new Date();
  var ts = String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0');
  d.innerHTML = '<span style="color:#555">['+ts+'] </span><span class="'+(type||'')+'">'+msg+'</span>';
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function sendCmd(direction) {
  fetch('/motor/'+direction+'?speed='+speed).then(r=>r.json()).then(d=>{
    if(d.blocked){
      addLog('⚠️ '+d.reason, 'warn');
      document.getElementById('alert-bar').classList.add('show');
      document.getElementById('alert-msg').textContent = d.reason;
      forceStop();
    } else {
      document.getElementById('alert-bar').classList.remove('show');
    }
  }).catch(function(){ forceStop(); });
}

function startCmd(direction) {
  pressStartTime = Date.now();
  currentDirection = direction;
  if(cmdInterval){ clearInterval(cmdInterval); cmdInterval = null; }
  sendCmd(direction);
  cmdInterval = setInterval(function(){ sendCmd(direction); }, 150);
}

function forceStop() {
  if(cmdInterval){ clearInterval(cmdInterval); cmdInterval = null; }
  currentDirection = null;
  fetch('/motor/stop?speed=0');
}

function stopCmd() {
  var held = Date.now() - pressStartTime;
  // Фікс 1: якщо відпустили занадто швидко — ігноруємо рух
  if(held < MIN_HOLD_MS && currentDirection !== null) {
    addLog('Занадто короткий дотик — ігнорую', '');
  } else if(currentDirection !== null) {
    addLog('Стоп (' + held + 'мс)', '');
  }
  forceStop();
}

function startRecord() {
  var dur = document.getElementById('rec-dur').value;
  addLog('Запис ' + dur + ' сек...', 'ok', 'audio-log');
  fetch('/audio/record?seconds=' + dur).then(r=>r.json()).then(d=>{
    addLog('✅ Запис завершено', 'ok', 'audio-log');
  });
}

function playRecord() {
  addLog('Відтворення...', 'ok', 'audio-log');
  fetch('/audio/play').then(r=>r.json()).then(d=>{
    addLog('✅ Відтворено', 'ok', 'audio-log');
  });
}

function speakText() {
  var text = document.getElementById('tts-text').value;
  if(!text) return;
  addLog('TTS: ' + text, 'ok', 'audio-log');
  fetch('/audio/speak?text=' + encodeURIComponent(text)).then(r=>r.json()).then(d=>{
    addLog('✅ Озвучено', 'ok', 'audio-log');
  });
}

function updateSensors() {
  fetch('/sensors').then(r=>r.json()).then(d=>{
    var front = d.front > 0 ? d.front+' мм' : '—';
    var cf = d.cliff_front > 0 ? d.cliff_front+' мм' : '—';
    var cb = d.cliff_back > 0 ? d.cliff_back+' мм' : '—';
    document.getElementById('live-front').textContent = front;
    document.getElementById('live-cf').textContent = cf;
    document.getElementById('live-cb').textContent = cb;
    document.getElementById('val-front').textContent = front;
    document.getElementById('val-cf').textContent = cf;
    document.getElementById('val-cb').textContent = cb;
    var cliff = d.cliff_front > 200 || d.cliff_back > 200;
    var el = document.getElementById('live-cliff');
    el.textContent = cliff ? 'ТАК!' : 'ні';
    el.style.color = cliff ? '#dc2626' : '#22c55e';
    if(cliff){
      document.getElementById('alert-bar').classList.add('show');
      document.getElementById('alert-msg').textContent = 'Край столу!';
    }
  });
  if(infoActive){
    fetch('/info').then(r=>r.json()).then(d=>{
      document.getElementById('val-cpu').textContent = d.cpu+'%';
      document.getElementById('val-ram').textContent = d.ram+' MB';
      document.getElementById('val-temp').textContent = d.temp+'°C';
    });
  }
}

setInterval(updateSensors, 200);

document.addEventListener('visibilitychange', function(){
  if(document.hidden){ forceStop(); }
});

// Захист: якщо мишка виходить за межі вікна — зупинка
document.addEventListener('mouseup', function(){ if(currentDirection) stopCmd(); });
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/motor/<direction>')
def motor(direction):
    global last_cmd_time
    last_cmd_time = time.time()
    speed = int(request.args.get('speed', 50))
    if direction == 'stop':
        motors.stop()
        sensor_manager.set_moving(False)
        return jsonify({'blocked': False, 'cmd': 'stop'})
    safe, reason = sensor_manager.is_safe(direction)
    if not safe:
        motors.stop()
        sensor_manager.set_moving(False)
        return jsonify({'blocked': True, 'reason': reason})
    motors_map = {
        'forward': motors.forward,
        'backward': motors.backward,
        'left': motors.left,
        'right': motors.right,
    }
    if direction in motors_map:
        motors_map[direction](speed)
    sensor_manager.set_moving(True, motors.stop)
    return jsonify({'blocked': False, 'cmd': direction})

@app.route('/sensors')
def get_sensors():
    return jsonify(sensor_manager.get_data())

@app.route('/audio/record')
def audio_record():
    seconds = int(request.args.get('seconds', 5))
    threading.Thread(target=audio.record, args=(seconds,), daemon=True).start()
    return jsonify({'ok': True})

@app.route('/audio/play')
def audio_play():
    threading.Thread(target=audio.play, daemon=True).start()
    return jsonify({'ok': True})

@app.route('/audio/speak')
def audio_speak():
    text = request.args.get('text', 'Привіт')
    threading.Thread(target=audio.play_text, args=(text,), daemon=True).start()
    return jsonify({'ok': True})

@app.route('/info')
def info():
    cpu, ram, temp = get_sys_info()
    return jsonify({'cpu': cpu, 'ram': ram, 'temp': temp})

if __name__ == '__main__':
    print('AIKO веб-панель запущена! Відкрий: http://192.168.0.103:5000')
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        motors.cleanup()
