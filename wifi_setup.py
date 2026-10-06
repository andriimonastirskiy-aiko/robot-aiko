#!/usr/bin/env python3
# wifi_setup.py — Captive Portal для AIKO
# Піднімає точку доступу AIKO-Setup, показує сторінку вибору Wi-Fi

import os
import sys
import time
import subprocess
import threading
import json
import logging
from flask import Flask, request, redirect, render_template_string

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WiFi] %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

# ── Конфігурація ───────────────────────────────────────────────────────────────
AP_SSID     = "AIKO-Setup"
AP_PASSWORD = "aiko1234"
AP_IP       = "192.168.4.1"
IFACE       = "wlan0"
WPA_CONF    = "/etc/wpa_supplicant/wpa_supplicant.conf"

# ── HTML шаблон сторінки ───────────────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIKO — Підключення до Wi-Fi</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: rgba(255,255,255,0.08);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 24px;
      padding: 40px 32px;
      width: 100%;
      max-width: 420px;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .robot-icon { font-size: 64px; margin-bottom: 12px; }
    h1 { color: #fff; font-size: 28px; margin-bottom: 6px; }
    .subtitle { color: rgba(255,255,255,0.6); font-size: 14px; margin-bottom: 32px; }
    label { display: block; text-align: left; color: rgba(255,255,255,0.8); font-size: 13px; margin-bottom: 6px; margin-top: 16px; }
    select, input[type=password], input[type=text] {
      width: 100%;
      padding: 14px 16px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.2);
      background: rgba(255,255,255,0.1);
      color: #fff;
      font-size: 15px;
      outline: none;
      transition: border 0.2s;
    }
    select:focus, input:focus { border-color: #e94560; }
    select option { background: #1a1a2e; color: #fff; }
    .btn {
      width: 100%;
      margin-top: 28px;
      padding: 16px;
      border-radius: 14px;
      border: none;
      background: linear-gradient(135deg, #e94560, #c62a47);
      color: #fff;
      font-size: 17px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s, transform 0.1s;
      letter-spacing: 0.5px;
    }
    .btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    .msg {
      margin-top: 20px;
      padding: 14px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 500;
    }
    .msg.ok  { background: rgba(46,213,115,0.2); color: #2ed573; border: 1px solid #2ed573; }
    .msg.err { background: rgba(255,71,87,0.2);  color: #ff4757; border: 1px solid #ff4757; }
    .footer { margin-top: 24px; color: rgba(255,255,255,0.3); font-size: 12px; }
    .scan-btn {
      background: transparent;
      border: 1px solid rgba(255,255,255,0.3);
      color: rgba(255,255,255,0.7);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      cursor: pointer;
      margin-top: 8px;
      transition: all 0.2s;
    }
    .scan-btn:hover { border-color: #e94560; color: #e94560; }
  </style>
</head>
<body>
<div class="card">
  <div class="robot-icon">🤖</div>
  <h1>Привіт! Я AIKO</h1>
  <p class="subtitle">Підключи мене до Wi-Fi і ми почнемо!</p>

  {% if message %}
    <div class="msg {{ msg_type }}">{{ message }}</div>
  {% endif %}

  <form method="POST" action="/connect">
    <label>📡 Оберіть мережу Wi-Fi</label>
    <select name="ssid">
      {% for net in networks %}
        <option value="{{ net }}">{{ net }}</option>
      {% endfor %}
      <option value="__manual__">✏️ Ввести вручну...</option>
    </select>

    <label>✏️ Або введіть назву мережі вручну</label>
    <input type="text" name="ssid_manual" placeholder="Назва мережі (якщо не в списку)">

    <label>🔒 Пароль</label>
    <input type="password" name="password" placeholder="Введіть пароль від Wi-Fi">

    <button class="btn" type="submit">🚀 Підключити AIKO!</button>
  </form>

  <div class="footer">AIKO v1.0 • {{ ap_ip }}</div>
</div>
</body>
</html>
"""

HTML_SUCCESS = """
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIKO — Підключено!</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
      min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
    }
    .card {
      background: rgba(255,255,255,0.08);
      border-radius: 24px;
      padding: 40px 32px;
      max-width: 380px;
      text-align: center;
      color: #fff;
    }
    .icon { font-size: 72px; margin-bottom: 16px; }
    h1 { font-size: 26px; margin-bottom: 12px; }
    p { color: rgba(255,255,255,0.7); line-height: 1.6; }
    .net { color: #2ed573; font-weight: bold; font-size: 18px; margin: 12px 0; }
  </style>
</head>
<body>
<div class="card">
  <div class="icon">🎉</div>
  <h1>Підключаюсь!</h1>
  <p>Намагаюсь підключитись до:</p>
  <div class="net">{{ ssid }}</div>
  <p>Зачекай 20-30 секунд...<br>Потім підключись до своєї домашньої мережі<br>і знайди мене за адресою:<br><strong>http://aiko.local</strong></p>
</div>
</body>
</html>
"""

# ── Сканування мереж ───────────────────────────────────────────────────────────
def scan_networks():
    try:
        result = subprocess.run(
            ["iwlist", IFACE, "scan"],
            capture_output=True, text=True, timeout=10
        )
        networks = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if 'ESSID:"' in line:
                ssid = line.split('ESSID:"')[1].rstrip('"')
                if ssid and ssid not in networks and ssid != AP_SSID:
                    networks.append(ssid)
        return networks
    except Exception as e:
        log.error(f"Помилка сканування: {e}")
        return []

# ── Запуск точки доступу ───────────────────────────────────────────────────────
def start_ap():
    log.info("🚀 Запускаємо точку доступу AIKO-Setup...")

    # Зупиняємо wpa_supplicant
    subprocess.run(["sudo", "systemctl", "stop", "wpa_supplicant"], capture_output=True)
    time.sleep(1)

    # Налаштовуємо IP
    subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
    subprocess.run(["sudo", "ip", "addr", "add", f"{AP_IP}/24", "dev", IFACE], capture_output=True)
    subprocess.run(["sudo", "ip", "link", "set", IFACE, "up"], capture_output=True)
    time.sleep(1)

    # Записуємо конфіг hostapd
    hostapd_conf = f"""interface={IFACE}
driver=nl80211
ssid={AP_SSID}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={AP_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(hostapd_conf)

    # Записуємо конфіг dnsmasq
    dnsmasq_conf = f"""interface={IFACE}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/{AP_IP}
dhcp-option=3,{AP_IP}
dhcp-option=6,{AP_IP}
"""
    with open("/tmp/dnsmasq_ap.conf", "w") as f:
        f.write(dnsmasq_conf)

    # Зупиняємо системний dnsmasq якщо є
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], capture_output=True)
    time.sleep(0.5)

    # Запускаємо dnsmasq
    subprocess.Popen(["sudo", "dnsmasq", "-C", "/tmp/dnsmasq_ap.conf", "--no-daemon"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    # Запускаємо hostapd
    subprocess.Popen(["sudo", "hostapd", "/tmp/hostapd.conf"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    log.info(f"✅ Точка доступу активна! SSID: {AP_SSID}, пароль: {AP_PASSWORD}")

# ── Зупинка точки доступу ──────────────────────────────────────────────────────
def stop_ap():
    log.info("🛑 Зупиняємо точку доступу...")
    subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
    subprocess.run(["sudo", "pkill", "-f", "dnsmasq_ap"], capture_output=True)
    time.sleep(1)

# ── Підключення до Wi-Fi ───────────────────────────────────────────────────────
def connect_wifi(ssid, password):
    log.info(f"🔌 Підключаємось до: {ssid}")

    wpa_config = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=UA

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
    # Зберігаємо конфіг
    with open("/tmp/wpa_new.conf", "w") as f:
        f.write(wpa_config)

    subprocess.run(["sudo", "cp", "/tmp/wpa_new.conf", WPA_CONF], capture_output=True)
    subprocess.run(["sudo", "chmod", "600", WPA_CONF], capture_output=True)

    # Запускаємо підключення у фоні
    def do_connect():
        time.sleep(2)
        stop_ap()
        subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
        subprocess.run(["sudo", "systemctl", "restart", "wpa_supplicant"], capture_output=True)
        time.sleep(3)
        subprocess.run(["sudo", "dhclient", IFACE], capture_output=True)
        time.sleep(5)

        # Перевіряємо чи підключились
        result = subprocess.run(["ip", "addr", "show", IFACE], capture_output=True, text=True)
        if "inet " in result.stdout:
            log.info(f"✅ Підключено до {ssid}!")
        else:
            log.warning(f"❌ Не вдалось підключитись до {ssid}, повертаємось в AP режим...")
            time.sleep(5)
            start_ap()

    thread = threading.Thread(target=do_connect, daemon=True)
    thread.start()

# ── Flask маршрути ─────────────────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    networks = scan_networks()
    return render_template_string(HTML_PAGE,
                                  networks=networks,
                                  message=None,
                                  msg_type='',
                                  ap_ip=AP_IP)

@app.route('/connect', methods=['POST'])
def connect():
    ssid_select = request.form.get('ssid', '').strip()
    ssid_manual = request.form.get('ssid_manual', '').strip()
    password    = request.form.get('password', '').strip()

    # Визначаємо яку мережу використовувати
    if ssid_select == '__manual__' or ssid_manual:
        ssid = ssid_manual
    else:
        ssid = ssid_select

    if not ssid:
        networks = scan_networks()
        return render_template_string(HTML_PAGE,
                                      networks=networks,
                                      message="❌ Введіть назву мережі!",
                                      msg_type='err',
                                      ap_ip=AP_IP)

    if len(password) < 8:
        networks = scan_networks()
        return render_template_string(HTML_PAGE,
                                      networks=networks,
                                      message="❌ Пароль має бути мінімум 8 символів!",
                                      msg_type='err',
                                      ap_ip=AP_IP)

    # Запускаємо підключення у фоні
    connect_wifi(ssid, password)

    return render_template_string(HTML_SUCCESS, ssid=ssid)

# Captive portal redirect
@app.route('/generate_204')
@app.route('/hotspot-detect.html')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
def captive():
    return redirect(f'http://{AP_IP}/', 302)

# ── Головна функція ────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("🤖 AIKO Wi-Fi Setup запущено!")
    log.info("=" * 50)

    # Запускаємо точку доступу
    start_ap()

    # Запускаємо Flask
    log.info(f"🌐 Веб-сервер на http://{AP_IP}:80")
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
