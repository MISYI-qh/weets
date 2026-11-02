"""Titik masuk Android (p4a webview bootstrap) & desktop. Jalankan server, lalu tampilkan UI."""
import os, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "weets_core")) if os.path.isdir(os.path.join(HERE, "weets_core")) else None


def _ensure_numpy():
    import importlib.util
    if importlib.util.find_spec("numpy") is None:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "numpy"], check=False)


def start_service():
    """Layanan latar belakang hanya dijalankan bila pengguna memilihnya (dan bisa dibatalkan di app)."""
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.POST_NOTIFICATIONS]) if hasattr(Permission, "POST_NOTIFICATIONS") else None
    except Exception:
        pass


def main():
    _ensure_numpy()
    import server
    if "ANDROID_ARGUMENT" in os.environ:
        os.environ["WEETS_LEARN"] = "0"                  # diputuskan di bawah sesuai pilihan pengguna
        start_service()
        server.serve(int(os.environ.get("PORT", 5000)), block=False)
        import apptools
        if server.L.state.get("background") is True:
            apptools.start_background_service()         # pilihan sebelumnya: belajar di latar belakang
        else:
            server.L.start()                            # belum memilih / menolak: belajar hanya saat app terbuka
        print("Weets jalan di 127.0.0.1:5000")
        while True:
            time.sleep(3600)
    port = int(os.environ.get("PORT", 8765))
    server.serve(port, block=False)
    url = "http://127.0.0.1:%d" % port
    print("Weets jalan di", url)
    try:
        import webview
        webview.create_window("Weets", url, width=1000, height=760)
        webview.start()
    except Exception:
        import webbrowser
        webbrowser.open(url)
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
