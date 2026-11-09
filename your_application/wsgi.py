import os
import sys
import subprocess
import threading

# Base directory where bot.py is located
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")

def start_bot_process():
    """Runs the Telegram bot in background."""
    print("🚀 Starting Telegram Bot from WSGI wrapper...")
    subprocess.run([sys.executable, BOT_SCRIPT])

# Start the bot in a background thread when Gunicorn starts
bot_thread = threading.Thread(target=start_bot_process, daemon=True)
bot_thread.start()

def application(environ, start_response):
    """Standard WSGI entrypoint for Render Web Service health-check."""
    status = '200 OK'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b"Sagar Coaching Centre NMMS Bot is Active and Running 24/7 on Render!\n"]

app = application
