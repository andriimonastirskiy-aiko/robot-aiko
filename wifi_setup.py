#!/usr/bin/env python3
# wifi_setup.py — Captive Portal для AIKO (виправлена версія)

import os, sys, time, subprocess, threading, json, logging
from flask import Flask, request, redirect, render_template_string

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WiFi] %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

AP_SSID     = "AIKO-Setup"
AP_PASSWORD = "aiko1234"
AP_IP       = "192.168.4.1"
IFACE       = "wlan0"
CONFIG_FILE = "/home/aiko/wifi_config.json"

# ── Збереження/завантаження конфігу ───────────────────────────────────────────
def save_config(ssid, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"ssid": ssid, "password": password}, f)
    log.info(f"💾 Збережено конфіг для: {ssid}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

# ── Визначення DHCP клієнта ────────────────────────────────────────────────────
def get_dhcp_client():
    if subprocess.run(["which", "dhclient"], capture_output=True).returncode == 0:
        return "dhclient"
    if subprocess.run(["which", "dhcpcd"], capture_output=True).returncode == 0:
        return "dhcpcd"
    return None

# ── Запуск AP ──────────────────────────────────────────────────────────────────
def start_ap():
    log.info("🚀 Запускаємо точку доступу AIKO-Setup...")

    subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
    subprocess.run(["sudo", "pkill", "dnsmasq"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "wpa_supplicant"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "NetworkManager"], capture_output=True)
    time.sleep(2)

    subprocess.run(["sudo", "ip", "link", "set", IFACE, "down"], capture_output=True)
    subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
    subprocess.run(["sudo", "ip", "link", "set", IFACE, "up"], capture_output=True)
    subprocess.run(["sudo", "ip", "addr", "add", f"{AP_IP}/24", "dev", IFACE], capture_output=True)
    time.sleep(1)

    with open("/tmp/hostapd.conf", "w") as f:
        f.write(f"""interface={IFACE}
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
""")

    with open("/tmp/dnsmasq_ap.conf", "w") as f:
        f.write(f"""interface={IFACE}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/{AP_IP}
dhcp-option=3,{AP_IP}
dhcp-option=6,{AP_IP}
""")

    subprocess.Popen(["sudo", "dnsmasq", "-C", "/tmp/dnsmasq_ap.conf", "--no-daemon"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen(["sudo", "hostapd", "/tmp/hostapd.conf"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    log.info(f"✅ AP активна! SSID: {AP_SSID} | пароль: {AP_PASSWORD}")

# ── Підключення до Wi-Fi ───────────────────────────────────────────────────────
def connect_wifi(ssid, password):
    log.info(f"🔌 Підключаємось до: {ssid}")

    def do_connect():
        time.sleep(2)

        # Зупиняємо AP
        subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
        subprocess.run(["sudo", "pkill", "dnsmasq"], capture_output=True)
        time.sleep(1)

        # Пишемо wpa_supplicant конфіг
        wpa = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=UA

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
        with open("/tmp/wpa_client.conf", "w") as f:
            f.write(wpa)

        subprocess.run(["sudo", "cp", "/tmp/wpa_client.conf",
                        "/etc/wpa_supplicant/wpa_supplicant.conf"], capture_output=True)
        subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
        subprocess.run(["sudo", "systemctl", "restart", "wpa_supplicant"], capture_output=True)
        time.sleep(5)

        # ── ВИПРАВЛЕННЯ: автовизначення DHCP клієнта ──
        dhcp = get_dhcp_client()
        if dhcp == "dhclient":
            subprocess.run(["sudo", "dhclient", IFACE], capture_output=True, timeout=15)
        elif dhcp == "dhcpcd":
            subprocess.run(["sudo", "dhcpcd", IFACE], capture_output=True, timeout=15)
        else:
            log.warning("⚠️ DHCP клієнт не знайдено! Спробуємо networkctl...")
            subprocess.run(["sudo", "networkctl", "renew", IFACE], capture_output=True)

        # ── ВИПРАВЛЕННЯ: більший таймаут на отримання IP ──
        log.info("⏳ Чекаємо на IP адресу (до 15 секунд)...")
        ip_obtained = False
        for i in range(15):
            time.sleep(1)
            result = subprocess.run(["ip", "addr", "show", IFACE], capture_output=True, text=True)
            if "inet " in result.stdout:
                for line in result.stdout.split('\n'):
                    if "inet " in line:
                        ip_addr = line.strip().split()[1]
                        log.info(f"🌐 Отримано IP: {ip_addr}")
                ip_obtained = True
                break

        if ip_obtained:
            # ── ВИПРАВЛЕННЯ: перевірка реального інтернету ──
            ping = subprocess.run(["ping", "-c", "2", "-W", "3", "8.8.8.8"], capture_output=True)
            if ping.returncode == 0:
                log.info(f"✅ Інтернет працює! Підключено до {ssid}")
            else:
                log.warning("⚠️ IP є але інтернету немає. Можливо неправильний пароль роутера?")

            save_config(ssid, password)
            log.info("💤 Завершуємо Wi-Fi setup скрипт...")
            time.sleep(2)
            # ── ВИПРАВЛЕННЯ: коректно зупиняємо Flask ──
            os._exit(0)
        else:
            log.warning(f"❌ Не вдалось підключитись до {ssid}! Повертаємось в AP режим...")
            time.sleep(2)
            start_ap()

    threading.Thread(target=do_connect, daemon=True).start()

# ── Сканування мереж ───────────────────────────────────────────────────────────
def scan_networks():
    try:
        r = subprocess.run(["sudo", "iwlist", IFACE, "scan"],
                           capture_output=True, text=True, timeout=15)
        networks, seen = [], set()
        for line in r.stdout.split('\n'):
            if 'ESSID:"' in line:
                ssid = line.strip().split('ESSID:"')[1].rstrip('"')
                if ssid and ssid not in seen and ssid != AP_SSID:
                    networks.append(ssid)
                    seen.add(ssid)
        return networks
    except Exception as e:
        log.error(f"Помилка сканування: {e}")
        return []

# ── HTML ───────────────────────────────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html><html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIKO — Підключення до Wi-Fi</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:rgba(255,255,255,0.08);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.15);border-radius:24px;padding:40px 32px;width:100%;max-width:420px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5)}
    .icon{font-size:64px;margin-bottom:12px}
    h1{color:#fff;font-size:28px;margin-bottom:6px}
    .sub{color:rgba(255,255,255,0.6);font-size:14px;margin-bottom:32px}
    label{display:block;text-align:left;color:rgba(255,255,255,0.8);font-size:13px;margin-bottom:6px;margin-top:16px}
    select,input{width:100%;padding:14px 16px;border-radius:12px;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.1);color:#fff;font-size:15px;outline:none}
    select option{background:#1a1a2e}
    .btn{width:100%;margin-top:28px;padding:16px;border-radius:14px;border:none;background:linear-gradient(135deg,#e94560,#c62a47);color:#fff;font-size:17px;font-weight:600;cursor:pointer}
    .msg{margin-top:20px;padding:14px;border-radius:12px;font-size:14px}
    .err{background:rgba(255,71,87,0.2);color:#ff4757;border:1px solid #ff4757}
    .footer{margin-top:24px;color:rgba(255,255,255,0.3);font-size:12px}
  </style>
</head>
<body><div class="card">
  <div class="icon">🐱</div>
  <h1>Привіт! Я AIKO</h1>
  <p class="sub">Підключи мене до Wi-Fi і ми почнемо!</p>
  {% if message %}<div class="msg err">{{ message }}</div>{% endif %}
  <form method="POST" action="/connect">
    <label>📡 Оберіть мережу Wi-Fi</label>
    <select name="ssid">
      {% for net in networks %}<option value="{{ net }}">{{ net }}</option>{% endfor %}
      <option value="__manual__">✏️ Ввести вручну...</option>
    </select>
    <label>✏️ Або введіть назву вручну</label>
    <input type="text" name="ssid_manual" placeholder="Назва мережі">
    <label>🔒 Пароль</label>
    <input type="password" name="password" placeholder="Пароль від Wi-Fi">
    <button class="btn" type="submit">🚀 Підключити AIKO!</button>
  </form>
  <div class="footer">AIKO v1.1 • {{ ap_ip }}</div>
</div></body></html>
"""

HTML_SUCCESS = """
<!DOCTYPE html><html lang="uk">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AIKO — Підключено!</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:rgba(255,255,255,0.08);border-radius:24px;padding:40px 32px;max-width:380px;text-align:center;color:#fff}
  .icon{font-size:72px;margin-bottom:16px}
  h1{font-size:26px;margin-bottom:12px}
  p{color:rgba(255,255,255,0.7);line-height:1.6}
  .net{color:#2ed573;font-weight:bold;font-size:18px;margin:12px 0}
</style></head>
<body><div class="card">
  <div class="icon">🎉</div>
  <h1>Підключаюсь!</h1>
  <p>Намагаюсь підключитись до:</p>
  <div class="net">{{ ssid }}</div>
  <p>Зачекай 20-30 секунд...<br>Потім підключись до своєї домашньої мережі<br>і знайди мене за адресою:<br><strong>192.168.0.103</strong></p>
</div></body></html>
"""

# ── Flask маршрути ─────────────────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    networks = scan_networks()
    return render_template_string(HTML_PAGE, networks=networks,
                                  message=None, ap_ip=AP_IP)

@app.route('/connect', methods=['POST'])
def connect():
    ssid_select = request.form.get('ssid', '').strip()
    ssid_manual = request.form.get('ssid_manual', '').strip()
    password    = request.form.get('password', '').strip()

    ssid = ssid_manual if (ssid_select == '__manual__' or ssid_manual) else ssid_select

    if not ssid:
        return render_template_string(HTML_PAGE, networks=scan_networks(),
                                      message="❌ Введіть назву мережі!", ap_ip=AP_IP)
    if len(password) < 8:
        return render_template_string(HTML_PAGE, networks=scan_networks(),
                                      message="❌ Пароль мінімум 8 символів!", ap_ip=AP_IP)

    connect_wifi(ssid, password)
    return render_template_string(HTML_SUCCESS, ssid=ssid)

# Captive portal redirects
@app.route('/generate_204')
@app.route('/hotspot-detect.html')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
def captive():
    return redirect(f'http://{AP_IP}/', 302)

# ── Головна функція ────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("🤖 AIKO Wi-Fi Setup v1.1 запущено!")
    log.info("=" * 50)

    cfg = load_config()
    if cfg:
        log.info(f"📋 Знайдено збережений Wi-Fi: {cfg['ssid']}")
        log.info("✅ Конфіг вже є — AP не потрібна. Виходимо.")
        return

    start_ap()
    log.info(f"🌐 Веб-сервер на http://{AP_IP}:80")
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
