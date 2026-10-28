"""Pintu masuk aplikasi WEETS (Python). Desktop/Termux: python main.py
Android (buildozer, bootstrap webview): server berjalan di port 5000 dan dibuka WebView."""
import os, sys, time, webbrowser
import importlib.util, subprocess
if importlib.util.find_spec("numpy") is None and not os.environ.get("ANDROID_ARGUMENT"):
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "numpy"])  # NumPy ikut terpasang otomatis
import server

if os.environ.get("ANDROID_ARGUMENT"):
    server.serve(5000)
else:
    port = int(os.environ.get("PORT", 8765))
    server.serve(port, block=False)
    url = "http://127.0.0.1:%d" % port
    try:
        import webview  # pip install pywebview -> jendela aplikasi asli
        webview.create_window("WEETS", url, width=1000, height=760)
        webview.start()
    except Exception:
        print("WEETS jalan di", url)
        webbrowser.open(url)
        while True:
            time.sleep(3600)
