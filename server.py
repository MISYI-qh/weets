"""Server HTTP lokal Weets (hanya 127.0.0.1). API untuk UI, aliran obrolan NDJSON, pembaca tautan, belajar, model .wt."""
import json, os, re, sys, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apptools, websearch, wt
from engine import Engine, STATUS, STYLES
from learner import Learner

E = None
L = None
VERSION = "2.1.0"
MAX_BODY = 40 * 1024 * 1024
MIME = {".html": "text/html; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"}


def data_dir():
    d = os.environ.get("WEETS_DATA")
    if not d:
        base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~/.weets")
        d = os.path.join(base, "weets_data") if os.environ.get("ANDROID_PRIVATE") else base
    os.makedirs(d, exist_ok=True)
    return d


def init(service=False):
    """Buat mesin + pembelajar sekali per proses."""
    global E, L
    if E is not None:
        return E, L
    E = Engine(data_dir(), starter=os.path.join(HERE, "model", "weets-starter.wt"))
    E.recent_queries = []
    L = Learner(E, data_dir(), max_params=int(os.environ.get("WEETS_MAX_PARAMS", 6_000_000)))
    L.battery_ok = apptools.battery_ok
    L.online = lambda: True
    if service or os.environ.get("WEETS_LEARN", "1") == "1":
        L.start()
    return E, L


def set_background(on):
    """on=True: layanan Android yang belajar (proses UI berhenti belajar). on=False: layanan dihentikan, belajar hanya saat app terbuka."""
    L.state["background"] = bool(on)
    L._save_state()
    if on:
        r = apptools.start_background_service() if apptools.is_android() else {"ok": True}
        if r.get("ok") and apptools.is_android():
            L.stop()                          # jangan belajar ganda di dua proses
        elif not apptools.is_android():
            L.start()
        return {"ok": r.get("ok", False), "on": bool(r.get("ok")) or not apptools.is_android(), **{k: v for k, v in r.items() if k == "alasan"}}
    apptools.stop_background_service()
    L.start()
    return {"ok": True, "on": False}


class H(BaseHTTPRequestHandler):
    server_version = "Weets/" + VERSION
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    # ---- keamanan: hanya localhost, dan tulis hanya dari halaman milik sendiri ----
    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost", "[::1]")

    def _origin_ok(self):
        o = self.headers.get("Origin")
        if not o:
            return True
        return urlparse(o).hostname in ("127.0.0.1", "localhost", "::1")

    def _send(self, code, body=b"", ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("terlalu besar")
        raw = self.rfile.read(n) if n else b""
        return raw

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "host ditolak"})
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        try:
            if p in ("/", "/index.html"):
                return self._file("index.html")
            if p in ("/manifest.json", "/icon.svg", "/icon.png", "/presplash.png", "/icon-1024.png"):
                return self._file(p[1:])
            if p == "/api/status":
                return self._send(200, self.status())
            if p == "/api/stages":
                return self._send(200, [{"i": i, "word": w, "stage": s} for i, (w, s) in enumerate(STATUS)])
            if p == "/api/notes":
                return self._send(200, E.notes[-100:])
            if p == "/api/learn/status":
                return self._send(200, L.status())
            if p == "/api/diag":
                return self._send(200, {"jaringan": websearch.diagnose(), "android": apptools.is_android(), "baterai": apptools.battery_state()})
            if p == "/api/model/export":
                if not E.ready:
                    return self._send(404, {"error": "belum ada model"})
                opt = (q.get("optimizer") or ["1"])[0] != "0"
                blob = wt.export_checkpoint(E.ckpt, with_optimizer=opt)
                name = f"weets-{time.strftime('%Y%m%d-%H%M')}.wt"
                return self._send(200, blob, "application/octet-stream", {"Content-Disposition": f'attachment; filename="{name}"'})
            if p == "/api/dictate/result":
                return self._send(200, apptools.dictate_result())
            return self._send(404, {"error": "tidak ada"})
        except Exception as e:
            traceback.print_exc()
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def _file(self, name):
        path = os.path.join(HERE, name)
        if not os.path.isfile(path):
            return self._send(404, {"error": "berkas tidak ada"})
        ext = os.path.splitext(name)[1]
        with open(path, "rb") as f:
            self._send(200, f.read(), MIME.get(ext, "application/octet-stream"))

    def status(self):
        info = E.info()
        return {"versi_app": VERSION, "model": info, "belajar": {k: L.state[k] for k in ("version", "cycles", "accepted", "rejected", "running", "enabled", "last")},
                "stats": E.stats, "android": apptools.is_android(), "gaya": list(STYLES)}

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            return self._send(403, {"error": "ditolak"})
        p = urlparse(self.path).path
        try:
            raw = self._json_body()
            if p == "/api/model/import":
                head = wt.import_blob(raw, E.ckpt)
                E.load()
                return self._send(200, {"ok": True, "model": head})
            if p == "/api/extract":
                name = self.headers.get("X-Filename", "berkas.txt")
                from urllib.parse import unquote
                text = apptools.extract_text(unquote(name), raw)
                return self._send(200, {"ok": True, "text": text[:60000], "panjang": len(text)})
            d = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            return self.route_post(p, d)
        except (wt.WtError, ValueError, KeyError) as e:
            return self._send(400, {"error": str(e)})
        except websearch.NetError as e:
            return self._send(502, {"error": f"{e.kind}: {e.detail}"})
        except Exception as e:
            traceback.print_exc()
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def route_post(self, p, d):
        if p == "/api/chat":
            return self.chat(d)
        if p == "/api/page":
            return self._send(200, websearch.read_page(str(d["url"])))
        if p == "/api/search":
            res, log = websearch.search(str(d["q"]))
            return self._send(200, {"hasil": res, "log": log})
        if p == "/api/notes/add":
            return self._send(200, {"text": E.add_note(str(d["text"]))})
        if p == "/api/notes/del":
            E.del_note(int(d["id"])); return self._send(200, {"ok": True})
        if p == "/api/learn/lesson":
            return self._send(200, {"ok": True, "total": L.add_lesson(str(d["text"]))})
        if p == "/api/learn/now":
            L.request_now(grow=bool(d.get("grow"))); return self._send(200, {"ok": True})
        if p == "/api/learn/prefs":
            for k, t in (("enabled", bool), ("only_charging", bool), ("idle_seconds", int), ("budget_seconds", int)):
                if k in d:
                    v = t(d[k])
                    if k == "idle_seconds":
                        v = max(10, min(v, 3600))
                    if k == "budget_seconds":
                        v = max(20, min(v, 900))
                    L.state[k] = v
            L._save_state(); return self._send(200, L.status())
        if p == "/api/background":
            return self._send(200, set_background(bool(d.get("on"))))
        if p == "/api/learn/rollback":
            return self._send(200, {"ok": L.rollback()})
        if p == "/api/makefile":
            name, data, ctype = apptools.make_file(str(d.get("kind", "txt")), str(d.get("title", "")), str(d.get("content", "")))
            path = apptools.save_download(name, data)
            import base64
            return self._send(200, {"name": name, "mime": ctype, "path": path, "b64": base64.b64encode(data).decode()})
        if p == "/api/image":
            svg = apptools.make_image(str(d.get("prompt", "weets")))
            path = apptools.save_download("gambar-weets.svg", svg.encode())
            return self._send(200, {"svg": svg, "path": path})
        if p == "/api/run":
            return self._send(200, apptools.run_code(str(d.get("code", ""))))
        if p == "/api/notify":
            return self._send(200, {"ok": apptools.notify(str(d.get("title", "Weets")), str(d.get("text", "")))})
        if p == "/api/battery":
            return self._send(200, apptools.ask_battery_exemption())
        if p == "/api/dictate/start":
            return self._send(200, apptools.dictate_start())
        if p == "/api/open_external":
            return self._send(200, apptools.open_external(str(d.get("url", ""))))
        return self._send(404, {"error": "tidak ada"})

    def chat(self, d):
        msgs = d.get("messages") or []
        if not isinstance(msgs, list) or not msgs:
            return self._send(400, {"error": "pesan kosong"})
        E.reload_if_changed() if hasattr(E, "reload_if_changed") else None
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            last = next((m.get("content", "") for m in reversed(msgs) if m.get("role") == "user"), "")
            if not re.search(r"https?://", last):
                E.recent_queries = (E.recent_queries + [E.make_query(last)])[-6:]
            for ev in E.chat(msgs, d.get("style", "normal"), d.get("opts") or {}):
                self.wfile.write((json.dumps(ev, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:
            traceback.print_exc()
            try:
                self.wfile.write((json.dumps({"t": "error", "text": f"{type(e).__name__}: {e}"}) + "\n").encode("utf-8"))
            except Exception:
                pass


def make_server(port, host="127.0.0.1"):
    init()
    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    return srv


def serve(port=5000, block=True):
    srv = make_server(port)
    if block:
        srv.serve_forever()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print("Weets di http://127.0.0.1:%d" % port)
    serve(port)
