import os
import sys
import time
import subprocess
import threading
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")
PUBLIC_URL = "https://telegram-boat-1omi.onrender.com"

_bot_started = False
_lock = threading.Lock()
_last_restart_time = None
_restart_count = 0

def start_bot_supervisor():
    global _bot_started, _last_restart_time, _restart_count
    with _lock:
        if _bot_started:
            return
        _bot_started = True

    print("🚀 Telegram Bot Supervisor started. Keeping bot alive 24/7...")
    while True:
        try:
            _restart_count += 1
            _last_restart_time = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            print(f"[{_last_restart_time}] Starting bot.py (Run #{_restart_count})...")
            
            # Run bot.py
            result = subprocess.run([sys.executable, BOT_SCRIPT])
            print(f"⚠️ bot.py exited with code {result.returncode}.")
        except Exception as e:
            print(f"❌ Error in supervisor: {e}")
        
        print("🔄 Restarting bot.py in 5 seconds to ensure 24/7 uptime...")
        time.sleep(5)

def keep_alive_pinger():
    """Pings our public Render URL every 8 minutes to prevent Render free-tier from sleeping."""
    time.sleep(90)  # Wait 90 seconds after boot
    print(f"💓 Keep-alive pinger started for {PUBLIC_URL}")
    while True:
        try:
            req = urllib.request.Request(
                PUBLIC_URL,
                headers={"User-Agent": "SagarBot-KeepAlive/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"💓 Keep-alive ping sent - status: {resp.status}")
        except Exception as e:
            print(f"⚠️ Keep-alive ping note: {e}")
        time.sleep(8 * 60)  # Ping every 8 minutes (Render sleeps after 15 minutes)

# Launch supervisor thread immediately
supervisor_thread = threading.Thread(target=start_bot_supervisor, daemon=True)
supervisor_thread.start()

# Launch keep-alive pinger thread to prevent Render sleep mode
pinger_thread = threading.Thread(target=keep_alive_pinger, daemon=True)
pinger_thread.start()

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    msg = (
        f"🏛️ Sagar Coaching Centre NMMS Bot is Supervised & Running 24/7!\n"
        f"Last Start: {_last_restart_time} | Total Runs: {_restart_count}\n"
    )
    return [msg.encode('utf-8')]

app = application
