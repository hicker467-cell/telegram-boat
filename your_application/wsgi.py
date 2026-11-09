import os
import sys
import time
import subprocess
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")

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

# Launch supervisor thread immediately
supervisor_thread = threading.Thread(target=start_bot_supervisor, daemon=True)
supervisor_thread.start()

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
