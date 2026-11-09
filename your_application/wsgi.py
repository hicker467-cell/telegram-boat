import os
import sys
import subprocess
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")

_bot_started = False
_lock = threading.Lock()

def start_bot_process():
    global _bot_started
    with _lock:
        if _bot_started:
            return
        _bot_started = True
    print("🚀 Starting Telegram Bot from WSGI wrapper...")
    subprocess.run([sys.executable, BOT_SCRIPT])

# Start exactly one daemon thread
bot_thread = threading.Thread(target=start_bot_process, daemon=True)
bot_thread.start()

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b"Sagar Coaching Centre NMMS Bot is Active and Running 24/7 on Render!\n"]

app = application
