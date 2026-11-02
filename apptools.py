"""Jembatan Android (notifikasi, baterai, dikte, buka tautan) + alat berkas (baca, buat) + gambar generatif. Semua opsional & aman gagal."""
import csv, html, io, json, os, re, struct, sys, time, zipfile, hashlib, random, threading
from xml.sax.saxutils import escape


def is_android():
    return "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def _ctx():
    from jnius import autoclass
    try:
        svc = autoclass("org.kivy.android.PythonService").mService
        if svc is not None:
            return svc
    except Exception:
        pass
    return autoclass("org.kivy.android.PythonActivity").mActivity


# ---------------- notifikasi / baterai / wake ----------------
def notify(title, text):
    if not is_android():
        return False
    try:
        from jnius import autoclass
        ctx = _ctx()
        NM = autoclass("android.app.NotificationManager"); NC = autoclass("android.app.NotificationChannel")
        Build = autoclass("android.os.Build$VERSION"); Ctx = autoclass("android.content.Context")
        mgr = ctx.getSystemService(Ctx.NOTIFICATION_SERVICE)
        if Build.SDK_INT >= 26:
            mgr.createNotificationChannel(NC("weets", "Weets", NM.IMPORTANCE_DEFAULT))
            B = autoclass("android.app.Notification$Builder")(ctx, "weets")
        else:
            B = autoclass("android.app.Notification$Builder")(ctx)
        B.setContentTitle(title).setContentText(text).setSmallIcon(ctx.getApplicationInfo().icon).setAutoCancel(True)
        mgr.notify(1001, B.build())
        return True
    except Exception:
        return False


def battery_state():
    if not is_android():
        return {"level": 100, "charging": True, "known": False}
    try:
        from jnius import autoclass
        ctx = _ctx()
        Intent = autoclass("android.content.Intent"); IF = autoclass("android.content.IntentFilter"); BM = autoclass("android.os.BatteryManager")
        st = ctx.registerReceiver(None, IF(Intent.ACTION_BATTERY_CHANGED))
        lv, sc = st.getIntExtra(BM.EXTRA_LEVEL, -1), st.getIntExtra(BM.EXTRA_SCALE, 100)
        ch = st.getIntExtra(BM.EXTRA_STATUS, -1)
        return {"level": int(100 * lv / max(sc, 1)), "charging": ch in (BM.BATTERY_STATUS_CHARGING, BM.BATTERY_STATUS_FULL), "known": True}
    except Exception:
        return {"level": 100, "charging": False, "known": False}


def battery_ok(only_charging=False):
    b = battery_state()
    if only_charging:
        return b["charging"] or not b["known"]
    return b["charging"] or b["level"] >= 25 or not b["known"]


def ask_battery_exemption():
    if not is_android():
        return {"ok": False, "alasan": "bukan Android"}
    try:
        from jnius import autoclass
        ctx = _ctx()
        PM = ctx.getSystemService(autoclass("android.content.Context").POWER_SERVICE)
        pkg = ctx.getPackageName()
        if PM.isIgnoringBatteryOptimizations(pkg):
            return {"ok": True, "sudah": True}
        Intent = autoclass("android.content.Intent"); Uri = autoclass("android.net.Uri"); S = autoclass("android.provider.Settings")
        it = Intent(S.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS); it.setData(Uri.parse("package:" + pkg))
        autoclass("org.kivy.android.PythonActivity").mActivity.startActivity(it)
        return {"ok": True, "sudah": False}
    except Exception as e:
        return {"ok": False, "alasan": str(e)[:100]}


def wake_lock():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        ctx = _ctx()
        PM = ctx.getSystemService(autoclass("android.content.Context").POWER_SERVICE)
        wl = PM.newWakeLock(1, "weets:belajar"); wl.acquire(10 * 60 * 1000)
        return wl
    except Exception:
        return False


def open_external(url):
    if not re.match(r"https?://", url or ""):
        return {"ok": False}
    if is_android():
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent"); Uri = autoclass("android.net.Uri")
            it = Intent(Intent.ACTION_VIEW, Uri.parse(url)); it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            _ctx().startActivity(it)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "alasan": str(e)[:100]}
    try:
        import webbrowser
        return {"ok": bool(webbrowser.open(url))}
    except Exception:
        return {"ok": False}


# ---------------- layanan latar belakang (bisa dihidupkan & dibatalkan kapan saja) ----------------
_svc = {"obj": None}


def start_background_service():
    if not is_android():
        return {"ok": False, "alasan": "bukan Android"}
    try:
        from android import AndroidService
        if _svc["obj"] is None:
            _svc["obj"] = AndroidService("Weets", "Belajar di latar belakang")
        _svc["obj"].start("1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "alasan": str(e)[:120]}


def stop_background_service():
    """Layanan juga berhenti sendiri bila pengaturan 'background' dimatikan (lihat service.py)."""
    if not is_android():
        return {"ok": True}
    try:
        if _svc["obj"] is not None:
            _svc["obj"].stop()
        else:
            from jnius import autoclass
            autoclass("org.kivy.android.PythonService").mService.stopSelf()
    except Exception:
        pass
    return {"ok": True}


# ---------------- dikte (Google speech lewat Intent; tanpa izin RECORD_AUDIO) ----------------
_dictation = {"text": None, "state": "idle"}


def dictate_start():
    if not is_android():
        return {"ok": False, "alasan": "dikte lewat Android hanya ada di aplikasi; di browser gunakan mikrofon papan ketik"}
    try:
        from jnius import autoclass
        from android import activity
        Intent = autoclass("android.content.Intent"); RI = autoclass("android.speech.RecognizerIntent")
        it = Intent(RI.ACTION_RECOGNIZE_SPEECH)
        it.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM); it.putExtra(RI.EXTRA_LANGUAGE, "id-ID")
        it.putExtra(RI.EXTRA_PROMPT, "Bicara sekarang")
        _dictation.update(text=None, state="listening")

        def on_result(req, res, data):
            if req != 4711:
                return
            try:
                if res == -1 and data is not None:
                    lst = data.getStringArrayListExtra(RI.EXTRA_RESULTS)
                    _dictation.update(text=str(lst.get(0)) if lst and lst.size() else "", state="done")
                else:
                    _dictation.update(text="", state="done")
            finally:
                activity.unbind(on_activity_result=on_result)
        activity.bind(on_activity_result=on_result)
        autoclass("org.kivy.android.PythonActivity").mActivity.startActivityForResult(it, 4711)
        return {"ok": True}
    except Exception as e:
        _dictation["state"] = "idle"
        return {"ok": False, "alasan": f"dikte tidak tersedia: {str(e)[:100]}"}


def dictate_result():
    r = dict(_dictation)
    if r["state"] == "done":
        _dictation.update(state="idle", text=None)
    return r


# ---------------- baca berkas ----------------
def _xml_text(xml):
    xml = re.sub(r"</w:p>|</a:p>|<w:br/>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def extract_text(name, data):
    ext = os.path.splitext(name.lower())[1]
    if ext in (".txt", ".md", ".csv", ".json", ".jsonl", ".log", ".py", ".js", ".html", ".htm", ".xml", ".tsv", ".yml", ".yaml", ".ini"):
        t = data.decode("utf-8", errors="replace")
        if ext in (".html", ".htm"):
            t = html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", t, flags=re.S))
        return re.sub(r"[ \t]+", " ", t).strip()
    if ext in (".docx", ".pptx", ".xlsx", ".odt"):
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        if ext == ".docx":
            return _xml_text(z.read("word/document.xml").decode("utf-8", "replace")).strip()
        if ext == ".pptx":
            sl = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.findall(r"\d+", n)[0]))
            return "\n\n".join(_xml_text(z.read(n).decode("utf-8", "replace")) for n in sl).strip()
        if ext == ".xlsx":
            ss = []
            if "xl/sharedStrings.xml" in names:
                ss = [html.unescape(re.sub(r"<[^>]+>", "", m)) for m in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8", "replace"), re.S)]
            out = []
            for n in sorted(x for x in names if x.startswith("xl/worksheets/sheet")):
                for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read(n).decode("utf-8", "replace"), re.S):
                    cells = []
                    for attrs, body in re.findall(r"<c([^>]*)>(.*?)</c>", row, re.S):
                        v = re.search(r"<v>(.*?)</v>", body, re.S)
                        if not v:
                            continue
                        cells.append(ss[int(v.group(1))] if 't="s"' in attrs and int(v.group(1)) < len(ss) else v.group(1))
                    out.append("\t".join(cells))
            return "\n".join(out).strip()
        return _xml_text(z.read("content.xml").decode("utf-8", "replace")).strip()
    if ext == ".zip":
        z = zipfile.ZipFile(io.BytesIO(data))
        parts = []
        for n in z.namelist()[:40]:
            if n.endswith("/") or z.getinfo(n).file_size > 2_000_000:
                continue
            try:
                parts.append(f"## {n}\n" + extract_text(n, z.read(n)))
            except Exception:
                pass
        return "\n\n".join(parts)
    if ext == ".pdf":
        return _pdf_text(data)
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        return describe_image(data)
    raise ValueError(f"jenis berkas {ext or '?'} belum bisa dibaca")


def _pdf_text(data):
    import zlib
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        s = m.group(1)
        try:
            s = zlib.decompress(s)
        except Exception:
            pass
        for tj in re.findall(rb"\((.*?)(?<!\\)\)\s*(?:Tj|')|\[(.*?)\]\s*TJ", s, re.S):
            seg = tj[0] if tj[0] else b"".join(re.findall(rb"\((.*?)(?<!\\)\)", tj[1], re.S))
            seg = re.sub(rb"\\([()\\])", rb"\1", seg)
            out.append(seg.decode("latin-1", "replace"))
    t = "\n".join(out).strip()
    if len(t) < 20:
        raise ValueError("PDF ini tidak punya lapisan teks (mungkin hasil pindai); OCR belum tersedia di aplikasi")
    return t


def describe_image(data):
    """Tanpa model penglihatan: hanya jujur melaporkan yang bisa diukur."""
    info = {}
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24]); info = {"format": "PNG", "lebar": w, "tinggi": h}
    elif data[:3] == b"\xff\xd8\xff":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1; continue
            mk = data[i + 1]
            if 0xC0 <= mk <= 0xC3:
                h, w = struct.unpack(">HH", data[i + 5:i + 9]); info = {"format": "JPEG", "lebar": w, "tinggi": h}; break
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return ("[Gambar" + (f" {info['format']} {info['lebar']}x{info['tinggi']}" if info else "") +
            "] Weets belum punya penglihatan: isi gambar tidak bisa dibaca. Ketik apa yang ada di gambar agar bisa dibahas.")


# ---------------- buat berkas ----------------
def _docx(title, text):
    paras = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(p)}</w:t></w:r></w:p>" for p in ([title, ""] if title else []) + text.split("\n"))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + paras + "</w:body></w:document>")
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", doc)
    return bio.getvalue()


def _pdf(title, text):
    def esc(s):
        return s.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = []
    for para in ([title, ""] if title else []) + text.split("\n"):
        while len(para) > 92:
            cut = para.rfind(" ", 0, 92); cut = cut if cut > 20 else 92
            lines.append(para[:cut]); para = para[cut:].lstrip()
        lines.append(para)
    pages = [lines[i:i + 52] for i in range(0, max(len(lines), 1), 52)]
    objs, kids = [], []
    for pi, pl in enumerate(pages):
        body = "BT /F1 11 Tf 56 790 Td 14 TL\n" + "\n".join(f"({esc(l)}) '" for l in pl) + "\nET"
        objs.append(f"<< /Length {len(body.encode('latin-1', 'replace'))} >>\nstream\n{body}\nendstream")
        kids.append(4 + 2 * pi)
    out = [b"%PDF-1.4\n"]
    offs = []
    def add(b):
        offs.append(sum(len(x) for x in out)); out.append(b)
    add(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add(f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>\nendobj\n".encode())
    add(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n")
    for pi, o in enumerate(objs):
        n = 4 + 2 * pi
        add(f"{n} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {n + 1} 0 R /Resources << /Font << /F1 3 0 R >> >> >>\nendobj\n".encode())
        add(f"{n + 1} 0 obj\n{o}\nendobj\n".encode("latin-1", "replace"))
    xref = sum(len(x) for x in out)
    out.append(f"xref\n0 {len(offs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode())
    out.append(f"trailer\n<< /Size {len(offs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return b"".join(out)


def make_file(kind, title, content):
    kind = kind.lower().lstrip(".")
    title = (title or "weets")[:80]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "weets"
    if kind == "docx":
        return f"{slug}.docx", _docx(title, content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if kind == "pdf":
        return f"{slug}.pdf", _pdf(title, content), "application/pdf"
    if kind == "html":
        return f"{slug}.html", (f"<!doctype html><meta charset=utf-8><title>{escape(title)}</title><body style='font:16px/1.6 system-ui;max-width:42em;margin:2em auto;padding:0 1em'><h1>{escape(title)}</h1>"
                                + "".join(f"<p>{escape(p)}</p>" for p in content.split("\n") if p.strip())).encode(), "text/html"
    if kind == "csv":
        rows = [re.split(r"\t|;|,(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", l) for l in content.split("\n") if l.strip()]
        bio = io.StringIO(); csv.writer(bio).writerows(rows)
        return f"{slug}.csv", bio.getvalue().encode("utf-8-sig"), "text/csv"
    if kind == "json":
        return f"{slug}.json", content.encode(), "application/json"
    if kind == "md":
        return f"{slug}.md", (f"# {title}\n\n{content}\n").encode(), "text/markdown"
    return f"{slug}.txt", content.encode("utf-8"), "text/plain"


def save_download(name, data):
    """Simpan ke folder aplikasi yang bisa diakses pengguna (tanpa izin tambahan di Android 11+)."""
    base = None
    if is_android():
        try:
            base = str(_ctx().getExternalFilesDir(None).getAbsolutePath())
        except Exception:
            base = None
    base = os.path.join(base or os.path.expanduser("~"), "Weets")
    os.makedirs(base, exist_ok=True)
    p = os.path.join(base, os.path.basename(name))
    with open(p, "wb") as f:
        f.write(data)
    return p


# ---------------- gambar generatif (tanpa API, tanpa model gambar) ----------------
def make_image(prompt, size=768):
    h = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
    r = random.Random(h)
    hue = r.randrange(360)
    pal = [f"hsl({(hue + d) % 360},{r.randint(35, 70)}%,{r.randint(35, 70)}%)" for d in (0, 28, 150, 200, 330)]
    bg = f"hsl({hue},{r.randint(10, 25)}%,{r.randint(92, 96)}%)"
    el = [f'<rect width="{size}" height="{size}" fill="{bg}"/>']
    for i in range(r.randint(7, 12)):
        c = r.choice(pal); x, y = r.randint(0, size), r.randint(0, size); s = r.randint(40, 300)
        k = r.choice(["circle", "ring", "rect", "arc"])
        if k == "circle":
            el.append(f'<circle cx="{x}" cy="{y}" r="{s // 2}" fill="{c}" fill-opacity=".{r.randint(35, 80)}"/>')
        elif k == "ring":
            el.append(f'<circle cx="{x}" cy="{y}" r="{s // 2}" fill="none" stroke="{c}" stroke-width="{r.randint(2, 9)}"/>')
        elif k == "rect":
            el.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s // 3}" rx="{r.randint(0, 24)}" fill="{c}" fill-opacity=".{r.randint(30, 70)}" transform="rotate({r.randint(-30, 30)} {x} {y})"/>')
        else:
            el.append(f'<path d="M{x} {y} q{s // 2} {-s // 2} {s} 0" fill="none" stroke="{c}" stroke-width="{r.randint(3, 10)}" stroke-linecap="round"/>')
    cap = escape(prompt[:60])
    el.append(f'<text x="{size // 2}" y="{size - 36}" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#222" fill-opacity=".7">{cap}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">' + "".join(el) + "</svg>"


# ---------------- jalankan kode (sandbox ringan) ----------------
def run_code(code, timeout=6):
    import subprocess
    exe = sys.executable
    if not exe or not os.path.exists(exe):
        return {"ok": False, "out": "", "err": "penerjemah tidak tersedia di perangkat ini"}
    pre = "import resource,sys;resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)\n" if os.name == "posix" else ""
    try:
        p = subprocess.run([exe, "-I", "-c", pre + code], capture_output=True, text=True, timeout=timeout, cwd="/tmp" if os.name == "posix" else None)
        return {"ok": p.returncode == 0, "out": p.stdout[-4000:], "err": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "out": "", "err": f"melewati batas waktu {timeout} detik"}
    except Exception as e:
        return {"ok": False, "out": "", "err": str(e)[:200]}
