cat > /home/aiko/web_server.py << 'EOF'
from flask import Flask, render_template_string, jsonify, request
import motors
import sensors
import safety
import threading
import time

app = Flask(__name__)

sensor1, sensor2, sensor3 = sensors.init_sensors()

sensor_data = {'front': 0, 'cliff_front': 0, 'cliff_back': 0}

def sensor_loop():
    while True:
        try:
            f, cf, cb = sensors.read_sensors(sensor1, sensor2, sensor3)
            sensor_data['front'] = f
            sensor_data['cliff_front'] = cf
            sensor_data['cliff_back'] = cb
        except:
            pass
        time.sleep(0.1)

t = threading.Thread(target=sensor_loop, daemon=True)
t.start()

safety.start(sensor_data)

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
.nav { margin-left: auto; display: flex; gap: 4px; }
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
.joy-btn { width: 52px; height: 52px; border-radius: 10px; border: 1px solid #ddd; background: #f9f9f9; cursor: pointer; font-size: 20px; transition: all 0.1s; }
.joy-btn:active { background: #dbeafe; border-color: #93c5fd; transform: scale(0.95); }
.joy-btn.stop { background: #fee2e2; border-color: #fca5a5; font-size: 13px; font-weight: 500; color: #dc2626; }
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
</style>
</head>
<body>
<div class="topbar">
  <div class="logo"><div class="dot"></div> AIKO debug panel</div>
  <div style="font-size:11px;color:#aaa;">192.168.0.103:5000</div>
  <div class="nav">
    <button class="nav-btn active" onclick="showPage('control',this)">Керування</button>
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
            <button class="joy-btn" id="btn-fwd"
              onmousedown="startCmd('forward')" onmouseup="startCmd('stop')"
              ontouchstart="startCmd('forward')" ontouchend="startCmd('stop')">↑</button>
            <div style="width:52px"></div>
          </div>
          <div class="joy-row">
            <button class="joy-btn"
              onmousedown="startCmd('left')" onmouseup="startCmd('stop')"
              ontouchstart="startCmd('left')" ontouchend="startCmd('stop')">←</button>
            <button class="joy-btn stop" onclick="startCmd('stop')">STOP</button>
            <button class="joy-btn"
              onmousedown="startCmd('right')" onmouseup="startCmd('stop')"
              ontouchstart="startCmd('right')" ontouchend="startCmd('stop')">→</button>
          </div>
          <div class="joy-row">
            <div style="width:52px"></div>
            <button class="joy-btn"
              onmousedown="startCmd('backward')" onmouseup="startCmd('stop')"
              ontouchstart="startCmd('backward')" ontouchend="startCmd('stop')">↓</button>
            <div style="width:52px"></div>
          </div>
        </div>
        <div class="slider-wrap">
          <div class="slider-label"><span>Швидкість</span><span class="slider-val" id="spd-val">50%</span></div>
          <input type="range" min="0" max="100" value="50" oninput="speed=this.value; document.getElementById('spd-val').textContent=this.value+'%'">
        </div>
      </div>
      <div class="card">
        <div class="card-title">Сенсори (live)</div>
        <div class="sensor-row">
          <span class="sensor-name">Спереду</span>
          <span class="sensor-val" id="live-front">— мм</span>
        </div>
        <div class="sensor-row">
          <span class="sensor-name">Вниз-вперед</span>
          <span class="sensor-val" id="live-cf">— мм</span>
        </div>
        <div class="sensor-row">
          <span class="sensor-name">Вниз-назад</span>
          <span class="sensor-val" id="live-cb">— мм</span>
        </div>
        <div class="sensor-row">
          <span class="sensor-name">Cliff alarm</span>
          <span class="sensor-val" id="live-cliff" style="color:#22c55e">ні</span>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Лог команд</div>
      <div class="log-box" id="log-box">
        <div class="log-line"><span class="ok">● Система готова</span></div>
      </div>
    </div>
  </div>

  <div class="page" id="page-info">
    <div class="card" style="margin-top:12px; margin-bottom:12px">
      <div class="card-title">ToF сенсори (відстань)</div>
      <div class="sensor-row"><span class="sensor-name">Спереду</span><span class="sensor-val" id="val-front">— мм</span></div>
      <div class="sensor-row"><span class="sensor-name">Вниз-вперед (cliff)</span><span class="sensor-val" id="val-cf">— мм</span></div>
      <div class="sensor-row"><span class="sensor-name">Вниз-назад (cliff)</span><span class="sensor-val" id="val-cb">— мм</span></div>
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
        <div class="sensor-row"><span class="sensor-name">Перешкода спереду</span><span class="sensor-val">150 мм</span></div>
        <div class="sensor-row"><span class="sensor-name">Край столу</span><span class="sensor-val">200 мм</span></div>
      </div>
    </div>
  </div>

</div>
<script>
var speed = 50;
var cmdInterval = null;

function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  btn.classList.add('active');
}

function addLog(msg, type) {
  var box = document.getElementById('log-box');
  var d = document.createElement('div');
  d.className = 'log-line';
  var t = new Date(); var ts = String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0');
  d.innerHTML = '<span style="color:#555">['+ts+'] </span><span class="'+(type||'')+'">'+msg+'</span>';
  box.appendChild(d); box.scrollTop = box.scrollHeight;
}

function sendCmd(direction) {
  fetch('/motor/'+direction+'?speed='+speed).then(r=>r.json()).then(d=>{
    if(d.blocked){
      addLog('⚠️ '+d.reason, 'warn');
      document.getElementById('alert-bar').classList.add('show');
      document.getElementById('alert-msg').textContent = d.reason;
    } else {
      document.getElementById('alert-bar').classList.remove('show');
    }
  });
}

function startCmd(direction) {
  if(cmdInterval) { clearInterval(cmdInterval); cmdInterval = null; }
  sendCmd(direction);
  if(direction !== 'stop') {
    cmdInterval = setInterval(() => sendCmd(direction), 150);
  }
}

function updateSensors() {
  fetch('/sensors').then(r=>r.json()).then(d=>{
    document.getElementById('live-front').textContent = d.front+' мм';
    document.getElementById('live-cf').textContent = d.cliff_front+' мм';
    document.getElementById('live-cb').textContent = d.cliff_back+' мм';
    document.getElementById('val-front').textContent = d.front+' мм';
    document.getElementById('val-cf').textContent = d.cliff_front+' мм';
    document.getElementById('val-cb').textContent = d.cliff_back+' мм';
    var cliff = d.cliff_front > 200 || d.cliff_back > 200;
    var el = document.getElementById('live-cliff');
    el.textContent = cliff ? 'ТАК!' : 'ні';
    el.style.color = cliff ? '#dc2626' : '#22c55e';
    if(cliff) {
      document.getElementById('alert-bar').classList.add('show');
      document.getElementById('alert-msg').textContent = 'Край столу!';
    }
  });
  fetch('/info').then(r=>r.json()).then(d=>{
    document.getElementById('val-cpu').textContent = d.cpu+'%';
    document.getElementById('val-ram').textContent = d.ram+' MB';
    document.getElementById('val-temp').textContent = d.temp+'°C';
  });
}
setInterval(updateSensors, 300);
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/motor/<direction>')
def motor(direction):
    speed = int(request.args.get('speed', 50))
    front = sensor_data['front']
    cliff_front = sensor_data['cliff_front']
    cliff_back = sensor_data['cliff_back']
    safe, reason = sensors.is_safe(front, cliff_front, cliff_back, direction)
    if not safe:
        motors.stop()
        safety.set_direction('stop')
        return jsonify({'blocked': True, 'reason': reason})
    motors_map = {'forward': motors.forward, 'backward': motors.backward,
                  'left': motors.left, 'right': motors.right, 'stop': motors.stop}
    if direction in motors_map:
        if direction == 'stop': motors_map[direction]()
        else: motors_map[direction](speed)
    safety.set_direction(direction)
    return jsonify({'blocked': False, 'cmd': direction, 'speed': speed})

@app.route('/sensors')
def get_sensors():
    return jsonify(sensor_data)

@app.route('/info')
def info():
    import subprocess
    try:
        cpu = subprocess.check_output(['top','-bn1']).decode()
        cpu_val = 0
        for line in cpu.split('\n'):
            if 'Cpu' in line:
                cpu_val = round(100 - float(line.split('id,')[0].split()[-1]))
                break
        temp = subprocess.check_output(['vcgencmd','measure_temp']).decode().strip().replace("temp=","").replace("'C","")
        mem = subprocess.check_output(['free','-m']).decode().split('\n')[1].split()
        ram = int(mem[2])
    except:
        cpu_val, temp, ram = 0, 0, 0
    return jsonify({'cpu': cpu_val, 'temp': temp, 'ram': ram})

if __name__ == '__main__':
    print('AIKO веб-панель запущена! Відкрий: http://192.168.0.103:5000')
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        motors.cleanup()
EOF
