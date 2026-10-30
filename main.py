"""Pintu masuk aplikasi Weets. Desktop/Termux: python main.py
Android (buildozer, bootstrap webview): server di port 5000 dibuka WebView; layanan latar depan (service.py)
menjalankan pembelajar yang terus belajar walau layar mati atau aplikasi di latar belakang."""
import os, sys, time, webbrowser
import importlib.util, subprocess
if importlib.util.find_spec("numpy") is None and not os.environ.get("ANDROID_ARGUMENT"):
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "numpy"])  # NumPy ikut terpasang otomatis

if os.environ.get("ANDROID_ARGUMENT"):
    try:   # izin notifikasi (Android 13+)
        from android.permissions import request_permissions
        request_permissions(["android.permission.POST_NOTIFICATIONS"])
    except Exception:
        pass
    try:   # layanan latar depan: ada notifikasi tetap, proses tidak dimatikan sistem saat layar mati
        from android import AndroidService
        AndroidService("Weets", "Belajar di latar belakang").start("weets")
        os.environ["WEETS_NO_LEARNER"] = "1"       # pembelajar dijalankan layanan, bukan proses ini
    except Exception:
        pass
    def _battery_once():
        time.sleep(8)
        try:
            import server, apptools
            flag = os.path.join(server.HOME, ".battery_asked")
            if not os.path.exists(flag):
                apptools.ask_battery()
                open(flag, "w").write("1")
        except Exception:
            pass
    import threading
    threading.Thread(target=_battery_once, daemon=True).start()
    try:
        import server
        server.serve(5000)
    except Exception:       # tampilkan galatnya di layar supaya bisa difoto, bukan layar putih kosong
        import traceback, http.server
        msg = traceback.format_exc()

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                b = ("<meta name=viewport content='width=device-width'><body style='font:14px sans-serif;padding:20px'>"
                     "<h3>Weets gagal dimulai</h3><pre style='white-space:pre-wrap'>%s</pre>" % msg.replace("<", "&lt;")).encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
        http.server.HTTPServer(("127.0.0.1", 5000), _H).serve_forever()
else:
    import server
    port = int(os.environ.get("PORT", 8765))
    server.serve(port, block=False)
    url = "http://127.0.0.1:%d" % port
    try:
        import webview  # pip install pywebview -> jendela aplikasi asli
        webview.create_window("Weets", url, width=1000, height=760)
        webview.start()
    except Exception:
        print("Weets jalan di", url)
        webbrowser.open(url)
        while True:
            time.sleep(3600)
