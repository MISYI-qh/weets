"""Layanan latar belakang Android: belajar saat ponsel diam. Berhenti sendiri bila pengguna membatalkannya di aplikasi."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WEETS_SERVICE"] = "1"
import server
E_, L_ = server.init(service=True)


def _stop():
    L_.stop()
    try:
        from jnius import autoclass
        autoclass("org.kivy.android.PythonService").mService.stopSelf()
    except Exception:
        pass
    os._exit(0)


while True:
    time.sleep(5)
    L_.refresh()
    if L_.state.get("background") is not True:      # dibatalkan dari UI
        _stop()
