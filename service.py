"""Layanan latar depan Android: terus belajar (melatih pelajaran/ketikan baru, menguji pertumbuhan) tanpa membuka aplikasi."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WEETS_SERVICE"] = "1"
import server

try:
    server.E._learner()
except Exception:
    while True:
        time.sleep(3600)
