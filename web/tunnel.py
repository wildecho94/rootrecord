# RootRecord/plugins/web/tunnel.py
# Version: 1.42.20260114 – Cloudflare Tunnel manager (cloudflared.exe)

import subprocess
import threading
import time
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] tunnel: %(message)s',
    handlers=[
        logging.FileHandler(Path("logs") / "tunnel.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tunnel")

WEB_DIR = Path("web")
CLOUDFLARED_EXE = WEB_DIR / "cloudflared.exe"
CONFIG_FILE = WEB_DIR / "cloudflared-config.yml"
LOCK_FILE = WEB_DIR / ".tunnel.lock"

tunnel_process = None
watchdog_thread = None
stop_event = threading.Event()

def is_tunnel_running():
    if not LOCK_FILE.exists():
        return False
    try:
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except:
        LOCK_FILE.unlink(missing_ok=True)
        return False

def start_tunnel():
    global tunnel_process, watchdog_thread

    if is_tunnel_running():
        logger.info("Tunnel already running.")
        return

    if not CLOUDFLARED_EXE.exists():
        logger.error(f"cloudflared.exe missing: {CLOUDFLARED_EXE}")
        return

    if not CONFIG_FILE.exists():
        logger.error(f"Config missing: {CONFIG_FILE}")
        return

    logger.info("Starting Cloudflare Tunnel...")

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    def run():
        global tunnel_process
        while not stop_event.is_set():
            try:
                cmd = [str(CLOUDFLARED_EXE), "tunnel", "--config", str(CONFIG_FILE), "run"]
                tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                for line in iter(tunnel_process.stdout.readline, ''):
                    logger.info(line.strip())
                for line in iter(tunnel_process.stderr.readline, ''):
                    logger.error(line.strip())
                tunnel_process.wait()
            except Exception as e:
                logger.error(f"Error: {e}")
            time.sleep(10)

    watchdog_thread = threading.Thread(target=run, daemon=True)
    watchdog_thread.start()
    logger.info("Tunnel started.")

def stop_tunnel():
    global tunnel_process, stop_event
    stop_event.set()
    if tunnel_process and tunnel_process.poll() is None:
        tunnel_process.terminate()
        try:
            tunnel_process.wait(5)
        except:
            tunnel_process.kill()
    LOCK_FILE.unlink(missing_ok=True)

def initialize():
    start_tunnel()
    print("[tunnel] Initialized")

import atexit
atexit.register(stop_tunnel)