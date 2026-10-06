#!/usr/bin/env python3
# wifi_setup.py — Captive Portal для AIKO (NetworkManager версія)

import os, time, subprocess, threading, json, logging
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

# ── Запуск AP ──────────────────────────────────────────────────────────────────
def start_ap():
    log.info("🚀 Запускаємо точку доступу AIKO-Setup...")

    # Зупиняємо все що може заважати
    subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
    subprocess.run(["sudo", "pkill", "dnsmasq"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "NetworkManager"], capture_output=True)
    time.sleep(2)

    # Піднімаємо інтерфейс вручну
    subprocess.run(["sudo", "ip", "link", "set", IFACE, "down"], capture_output=True)
    subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
    subprocess.run(["sudo", "ip", "link", "set", IFACE, "up"], capture_output=True)
    subprocess.run(["sudo", "ip", "addr", "add", f"{AP_IP}/24", "dev", IFACE], capture_output=True)
    time.sleep(1)

    # hostapd конфіг
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

    # dnsmasq конфіг (DHCP + captive portal redirect)
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

# ── Підключення до Wi-Fi через NetworkManager ──────────────────────────────────
def connect_wifi(ssid, password):
    log.info(f"🔌 Підключаємось до: {ssid}")

    def do_connect():
        time.sleep(2)

        # 1. Зупиняємо AP
        log.info("🛑 Зупиняємо точку доступу...")
        subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
        subprocess.run(["sudo", "pkill", "dnsmasq"], capture_output=True)
        time.sleep(1)

        # 2. Очищаємо IP та повертаємо NetworkManager
        subprocess.run(["sudo", "ip", "addr", "flush", "dev", IFACE], capture_output=True)
        subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], capture_output=True)
        time.sleep(3)

        # 3. Видаляємо старе з'єднання з такою ж назвою (якщо є)
        subprocess.run(["sudo", "nmcli", "connection", "delete", ssid],
                       capture_output=True)
        time.sleep(1)

        # 4. Підключаємось через nmcli — він сам керує wpa_supplicant!
        log.info(f"📡 nmcli: підключаємось до {ssid}...")
        result = subprocess.run([
            "sudo", "nmcli", "device", "wifi", "connect", ssid,
            "password", password,
            "ifname", IFACE,
            "name", ssid
        ], capture_output=True, text=True, timeout=40)

        log.info(f"nmcli вивід: {result.stdout.strip()}")
        if result.returncode != 0:
            log.error(f"nmcli помилка: {result.stderr.strip()}")

        # 5. Налаштовуємо таймаути та автопідключення через nmcli
        log.info("⚙️ Налаштовуємо таймаути та автопідключення...")
        subprocess.run([
            "sudo", "nmcli", "connection", "modify", ssid,
            "ipv4.dhcp-timeout", "60",
            "connection.auth-retries", "10",
            "connection.autoconnect", "yes",
            "connection.autoconnect-priority", "100"
        ], capture_output=True)

        # Зберігаємо зміни
        subprocess.run(["sudo", "nmcli", "connection", "up", ssid],
                       capture_output=True, timeout=20)

        # 6. Чекаємо на IP адресу (до 30 секунд)
        log.info("⏳ Чекаємо на IP адресу (до 30 секунд)...")
        ip_obtained = False
        for i in range(30):
            time.sleep(1)
            result = subprocess.run(["ip", "addr", "show", IFACE],
                                    capture_output=True, text=True)
            if "inet " in result.stdout:
                for line in result.stdout.split('\n'):
                    if "inet " in line:
                        ip_addr = line.strip().split()[1]
                        log.info(f"🌐 Отримано IP: {ip_addr}")
                ip_obtained = True
                break

        if ip_obtained:
            # 7. Перевіряємо реальний інтернет
            ping = subprocess.run(["ping", "-c", "2", "-W", "3", "8.8.8.8"],
                                  capture_output=True)
            if ping.returncode == 0:
                log.info(f"✅ Інтернет працює! Підключено до {ssid}")
            else:
                log.warning("⚠️ IP є але інтернету немає. Перевір пароль роутера!")

            save_config(ssid, password)
            log.info("💤 Wi-Fi налаштовано! Завершуємо setup...")
            time.sleep(2)
            os._exit(0)
        else:
            log.warning(f"❌ Не вдалось підключитись до '{ssid}'! Повертаємось в AP режим...")
            # Видаляємо невдале з'єднання
            subprocess.run(["sudo", "nmcli", "connection", "delete", ssid],
                           capture_output=True)
            time.sleep(2)
            start_ap()

    threading.Thread(target=do_connect, daemon=True).start()

# ── Сканування мереж через nmcli ──────────────────────────────────────────────
def scan_networks():
    try:
        # Спочатку примусове сканування
        subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"],
                       capture_output=True, timeout=10)
        time.sleep(2)

        r = subprocess.run(
            ["sudo", "nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
            capture_output=True, text=True, timeout=15
        )
        networks, seen = [], set()
        for line in r.stdout.split('\n'):
            ssid = line.strip()
            if ssid and ssid not in seen and ssid != AP_SSID and ssid != "--":
                networks.append(ssid)
                seen.add(ssid)
        log.info(f"📡 Знайдено мереж: {len(networks)}")
        return networks
    except Exception as e:
        log.error(f"Помилка сканування: {e}")
        return []

# ── HTML сторінка ──────────────────────────────────────────────────────────────
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
    .btn{width:100%;margin-top:28px;padding:16px;border-radius:14px;border:none;background:linear-gradient(135deg,#e94560,#c62a47);color:#fff;font-size:17px;font-weight:600;cursor:pointer;transition:opacity 0.2s}
    .btn:active{opacity:0.8}
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
    <label>✏️ Або введіть назву вручну (якщо не бачите свою)</label>
    <input type="text" name="ssid_manual" placeholder="Назва мережі">
    <label>🔒 Пароль Wi-Fi</label>
    <input type="password" name="password" placeholder="Пароль від Wi-Fi">
    <button class="btn" type="submit">🚀 Підключити AIKO!</button>
  </form>
  <div class="footer">AIKO v1.2 • {{ ap_ip }}</div>
</div></body></html>
"""

HTML_SUCCESS = """
<!DOCTYPE html><html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>AIKO — Підключаюсь!</title>
  <style>
    body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:rgba(255,255,255,0.08);border-radius:24px;padding:40px 32px;max-width:380px;text-align:center;color:#fff}
    .icon{font-size:72px;margin-bottom:16px}
    h1{font-size:26px;margin-bottom:12px}
    p{color:rgba(255,255,255,0.7);line-height:1.7;margin-bottom:8px}
    .net{color:#2ed573;font-weight:bold;font-size:20px;margin:16px 0}
    .note{background:rgba(46,213,115,0.1);border:1px solid rgba(46,213,115,0.3);border-radius:12px;padding:14px;margin-top:16px;font-size:13px;color:rgba(255,255,255,0.8)}
  </style>
</head>
<body><div class="card">
  <div class="icon">🎉</div>
  <h1>Підключаюсь!</h1>
  <p>Намагаюсь підключитись до:</p>
  <div class="net">📶 {{ ssid }}</div>
  <p>Зачекай <strong>20-30 секунд...</strong></p>
  <div class="note">
    Потім підключись до своєї домашньої мережі<br>
    і знайди AIKO за адресою:<br><br>
    <strong style="font-size:16px">192.168.0.103</strong>
  </div>
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

    # Визначаємо SSID: ручне введення має пріоритет
    ssid = ssid_manual if (ssid_select == '__manual__' or ssid_manual) else ssid_select

    if not ssid:
        return render_template_string(HTML_PAGE, networks=scan_networks(),
                                      message="❌ Введіть назву мережі!", ap_ip=AP_IP)
    if len(password) < 8:
        return render_template_string(HTML_PAGE, networks=scan_networks(),
                                      message="❌ Пароль має бути мінімум 8 символів!", ap_ip=AP_IP)

    connect_wifi(ssid, password)
    return render_template_string(HTML_SUCCESS, ssid=ssid)

# Captive portal redirects (для автовідкриття на телефонах)
@app.route('/generate_204')
@app.route('/hotspot-detect.html')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
@app.route('/redirect')
def captive():
    return redirect(f'http://{AP_IP}/', 302)

# ── Головна функція ────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("🤖 AIKO Wi-Fi Setup v1.2 (NetworkManager) запущено!")
    log.info("=" * 50)

    # Якщо вже є збережений конфіг — AP не потрібна
    cfg = load_config()
    if cfg:
        log.info(f"📋 Знайдено збережений Wi-Fi: {cfg['ssid']}")
        log.info("✅ Конфіг вже є — пропускаємо AP режим.")
        return

    start_ap()
    log.info(f"🌐 Веб-сервер запущено на http://{AP_IP}:80")
    log.info(f"📱 Підключись до Wi-Fi '{AP_SSID}' (пароль: {AP_PASSWORD})")
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
