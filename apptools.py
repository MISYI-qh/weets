"""Alat bawaan aplikasi Weets: cari web, baca halaman, jalankan kode Python, buat berkas, ingatan ajaran.
Semua memakai pustaka standar Python (tanpa API/kunci). Pencarian & baca halaman butuh internet saat dipakai."""
import difflib, html, io, ipaddress, json, os, re, socket, subprocess, sys, tempfile, time, urllib.parse, urllib.request, zipfile

UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36"


# ------------------------------------------------------------------ web
def _public_host(url):
    """Tolak alamat lokal/privat supaya alat ini tidak bisa dipakai membuka layanan di perangkat sendiri."""
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except Exception:
        return None          # tidak bisa diterjemahkan (biasanya offline): bukan berarti dilarang
    for fam, _, _, _, sa in infos:
        ip = ipaddress.ip_address(sa[0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def _get(url, timeout=15, max_bytes=3_000_000, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "id,en;q=0.8", "Accept": "text/html,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(max_bytes), r.headers.get("Content-Type", ""), r.geturl()


def parse_ddg(page):
    """Hasil pencarian DuckDuckGo (versi HTML) -> [{title,url,snippet}]."""
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)', page, re.S):
        href, title, rest = m.group(1), m.group(2), m.group(3)
        href = html.unescape(href)
        if href.startswith("//"):
            href = "https:" + href
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        if "uddg" in q:
            href = q["uddg"][0]
        if not href.startswith("http") or "duckduckgo.com/y.js" in href:
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>', rest, re.S)
        clean = lambda x: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
        out.append({"title": clean(title), "url": href, "snippet": clean(sn.group(1)) if sn else ""})
        if len(out) >= 6:
            break
    return out


def parse_wiki(js):
    out = []
    for r in (js.get("query", {}) or {}).get("search", [])[:6]:
        title = r.get("title", "")
        snip = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", r.get("snippet", "")))).strip()
        out.append({"title": title, "url": "https://id.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")), "snippet": snip})
    return out


def search(q):
    """Cari web: DuckDuckGo (HTML) lebih dulu; bila gagal/kosong, cadangan: Wikipedia Indonesia."""
    q = q.strip()[:200]
    if not q:
        return {"error": "empty"}
    err = None
    for attempt in ("ddg_post", "ddg_get"):
        try:
            if attempt == "ddg_post":
                body, _, _ = _get("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": q}).encode(), timeout=12)
            else:
                body, _, _ = _get("https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": q}), timeout=12)
            res = parse_ddg(body.decode("utf-8", "replace"))
            if res:
                return {"results": res, "source": "DuckDuckGo"}
        except Exception as e:
            err = type(e).__name__
    try:
        body, _, _ = _get("https://id.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 6, "utf8": 1}), timeout=12)
        res = parse_wiki(json.loads(body.decode("utf-8", "replace")))
        if res:
            return {"results": res, "source": "Wikipedia"}
    except Exception as e:
        err = err or type(e).__name__
    return {"error": "offline", "detail": err} if err else {"error": "no_results"}


def page(url):
    from weets import ingest
    ok = _public_host(url)
    if ok is False:
        return {"error": "blocked"}
    if ok is None:
        return {"error": "offline", "detail": "DNS"}
    try:
        data, ctype, final = _get(url, timeout=20)
    except Exception as e:
        return {"error": "offline", "detail": type(e).__name__}
    if _public_host(final) is False:
        return {"error": "blocked"}
    txt = ""
    try:
        if "html" in ctype.lower() or data[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
            m = re.search(rb"charset=([\w-]+)", data[:4000], re.I)
            txt = data.decode((m.group(1).decode() if m else "utf-8"), "replace")
            title, body = ingest.html_to_text(txt)
        else:
            docs = ingest.parse_bytes(data, final, ctype)
            title, body = os.path.basename(urllib.parse.urlparse(final).path) or final, "\n\n".join(d.text for d in docs)
    except Exception as e:
        return {"error": "unreadable", "detail": str(e)[:120]}
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) < 30:
        return {"error": "empty"}
    links = []
    if "<a" in (txt if "txt" in dir() else ""):
        seen = set()
        for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>', txt, re.S | re.I):
            u = urllib.parse.urljoin(final, html.unescape(m.group(1)))
            lbl = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
            if u.startswith(("http://", "https://")) and u not in seen and 2 < len(lbl) < 90:
                seen.add(u)
                links.append({"url": u, "text": lbl})
            if len(links) >= 25:
                break
    return {"title": (title or final)[:200], "url": final, "text": body[:14000], "chars": len(body), "links": links}


# ------------------------------------------------------------------ kode
def run_python(code):
    if len(code) > 20000:
        return {"error": "too_big"}
    if not (sys.executable and os.path.exists(sys.executable)):
        return {"error": "unavailable"}
    with tempfile.TemporaryDirectory() as cwd:
        def limits():
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_CPU, (11, 11))
                resource.setrlimit(resource.RLIMIT_AS, (768 * 2**20, 768 * 2**20))
                resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 2**20, 10 * 2**20))
            except Exception:
                pass
        try:
            r = subprocess.run([sys.executable, "-I", "-c", code], cwd=cwd, capture_output=True, text=True, timeout=10,
                               env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
                               preexec_fn=limits if os.name == "posix" else None)
        except subprocess.TimeoutExpired:
            return {"error": "timeout"}
        except OSError:
            return {"error": "unavailable"}
    return {"out": (r.stdout or "")[:6000], "err": (r.stderr or "")[-2500:], "code": r.returncode}


# ------------------------------------------------------------------ berkas
def _esc(s):
    return html.escape(s, quote=False)


def make_docx(title, content):
    paras = ([title] if title else []) + content.replace("\r", "").split("\n")
    body = "".join('<w:p><w:pPr>%s</w:pPr><w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (
        '<w:pStyle w:val="Title"/>' if title and i == 0 else "", '<w:rPr><w:b/><w:sz w:val="36"/></w:rPr>' if title and i == 0 else "", _esc(p))
        for i, p in enumerate(paras))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body>%s<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>' % body)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def make_pdf(title, content):
    import textwrap
    lines = []
    if title:
        lines += [("B", l) for l in textwrap.wrap(title, 55)] + [("N", "")]
    for para in content.replace("\r", "").split("\n"):
        w = textwrap.wrap(para, 92) or [""]
        lines += [("N", l) for l in w]
    per = 52
    pages = [lines[i:i + per] for i in range(0, max(len(lines), 1), per)] or [[]]
    enc = lambda t: t.encode("cp1252", "replace").decode("cp1252").encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objs = []
    n = len(pages)
    kids = " ".join("%d 0 R" % (5 + 2 * i) for i in range(n))
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n))
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for i, pl in enumerate(pages):
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % (6 + 2 * i))
        stream = "BT\n14 TL\n50 790 Td\n" + "".join("/%s %d Tf (%s) '\n" % ("F2" if st == "B" else "F1", 15 if st == "B" else 11, enc(t)) for st, t in pl) + "ET"
        objs.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream.encode("latin-1", "replace")), stream))
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs):
        offs.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (i + 1, o)).encode("latin-1", "replace")
    xr = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for o in offs:
        out += ("%010d 00000 n \n" % o).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xr)).encode()
    return out


MIMES = {"txt": "text/plain", "md": "text/markdown", "csv": "text/csv", "json": "application/json", "html": "text/html", "py": "text/x-python",
         "js": "text/javascript", "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def make_file(ext, title, content):
    ext = re.sub(r"[^a-z0-9]", "", ext.lower())[:8] or "txt"
    MIMES.setdefault(ext, "text/plain")
    if ext == "pdf":
        return make_pdf(title, content), MIMES[ext], ext
    if ext == "docx":
        return make_docx(title, content), MIMES[ext], ext
    if ext == "json":
        try:
            json.loads(content)
        except Exception:
            content = json.dumps({"title": title, "content": content}, ensure_ascii=False, indent=2)
    return content.encode("utf-8-sig" if ext == "csv" else "utf-8"), MIMES[ext] + "; charset=utf-8", ext


# ------------------------------------------------------------------ ingatan ajaran (jawaban instan tanpa menunggu pelatihan)
def _norm(s):
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def match_taught(q, taught, thr=0.86):
    nq = _norm(q)
    if not nq:
        return None
    best, ba = 0.0, None
    for t in taught[:400]:
        nt = _norm(str(t.get("q", "")))
        if not nt:
            continue
        r = 1.0 if nt == nq else difflib.SequenceMatcher(None, nq, nt).ratio()
        if r > best:
            best, ba = r, str(t.get("a", ""))
    return ba if best >= thr and ba else None


# ------------------------------------------------------------------ peramban dalam aplikasi (proksi halaman)
_NAV = ("<script>document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;"
        "var h=a.href;if(!/^https?:/.test(h))return;e.preventDefault();parent.postMessage({weetsNav:h},'*')},true);"
        "document.addEventListener('submit',function(e){e.preventDefault()},true);"
        "try{parent.postMessage({weetsTitle:document.title},'*')}catch(x){}</script>")


def browse(url):
    """Ambil halaman lewat server lalu sajikan sebagai halaman biasa (tanpa header yang melarang ditampilkan di dalam aplikasi).
    Tautan diteruskan ke aplikasi lewat postMessage; sumber daya (gambar/gaya) dimuat langsung dari situsnya."""
    def page_msg(t, code=200):
        return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                "<body style='font:16px sans-serif;padding:24px;color:#444'>%s</body>" % html.escape(t)).encode(), "text/html; charset=utf-8", code
    ok = _public_host(url)
    if ok is False:
        return page_msg("Alamat ini tidak boleh dibuka dari aplikasi.", 403)
    if ok is None:
        return page_msg("Tidak ada koneksi internet.", 502)
    try:
        data, ctype, final = _get(url, timeout=20, max_bytes=4_000_000)
    except Exception as e:
        return page_msg("Halaman tidak bisa dibuka (%s)." % type(e).__name__, 502)
    if _public_host(final) is False:
        return page_msg("Alamat ini tidak boleh dibuka dari aplikasi.", 403)
    low = ctype.lower()
    if "html" not in low and not data[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
        if low.startswith(("image/", "text/plain", "application/pdf")):
            return data, ctype, 200
        return page_msg("Berkas ini bukan halaman web. Gunakan tombol Buka di browser.", 200)
    m = re.search(rb"charset=([\w-]+)", data[:4000], re.I)
    try:
        txt = data.decode((m.group(1).decode() if m else "utf-8"), "replace")
    except LookupError:
        txt = data.decode("utf-8", "replace")
    txt = re.sub(r"<meta[^>]+http-equiv=[\"']?content-security-policy[^>]*>", "", txt, flags=re.I)
    base = '<base href="%s">' % html.escape(final, quote=True)
    if re.search(r"<head[^>]*>", txt, re.I):
        txt = re.sub(r"(<head[^>]*>)", lambda mm: mm.group(1) + base, txt, count=1, flags=re.I)
    else:
        txt = base + txt
    txt += _NAV
    return txt.encode("utf-8"), "text/html; charset=utf-8", 200


# ------------------------------------------------------------------ notifikasi bawaan Android (aman dipanggil di mana pun)
def native_notify(title, text, nid=7):
    if not os.environ.get("ANDROID_ARGUMENT") and "ANDROID_ROOT" not in os.environ:
        return False
    try:
        from jnius import autoclass
        ctx = None
        try:
            ctx = autoclass("org.kivy.android.PythonService").mService
        except Exception:
            ctx = None
        if ctx is None:
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        Context = autoclass("android.content.Context")
        nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
        B = autoclass("android.app.Notification$Builder")
        if autoclass("android.os.Build$VERSION").SDK_INT >= 26:
            NC = autoclass("android.app.NotificationChannel")
            nm.createNotificationChannel(NC("weets_events", "Weets", 3))
            b = B(ctx, "weets_events")
        else:
            b = B(ctx)
        b.setContentTitle(title).setContentText(text).setSmallIcon(ctx.getApplicationInfo().icon).setAutoCancel(True)
        nm.notify(nid, b.build())
        return True
    except Exception:
        return False


_online = [0.0, False]


def online():
    """Cek koneksi internet singkat tanpa DNS (di-cache 60 detik): coba sambung ke dua alamat publik."""
    if time.time() - _online[0] < 60:
        return _online[1]
    ok = False
    for ip in ("1.1.1.1", "8.8.8.8"):
        try:
            socket.create_connection((ip, 443), 2.5).close()
            ok = True
            break
        except Exception:
            continue
    _online[0], _online[1] = time.time(), ok
    return ok


def wake(on, tag="weets"):
    """Wake lock parsial di Android supaya CPU tetap jalan saat layar mati selama pelatihan (aman dipanggil di mana pun)."""
    if not os.environ.get("ANDROID_ARGUMENT") and not os.environ.get("PYTHON_SERVICE_ARGUMENT"):
        return
    try:
        from jnius import autoclass
        try:
            ctx = autoclass("org.kivy.android.PythonService").mService
        except Exception:
            ctx = None
        if ctx is None:
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        pm = ctx.getSystemService(autoclass("android.content.Context").POWER_SERVICE)
        if on:
            if not getattr(wake, "lock", None):
                wake.lock = pm.newWakeLock(1, tag)
            wake.lock.acquire(30 * 60 * 1000)
        elif getattr(wake, "lock", None) and wake.lock.isHeld():
            wake.lock.release()
    except Exception:
        pass


def ask_battery():
    """Minta pengecualian hemat baterai (Android) supaya layanan latar belakang tidak dimatikan sistem."""
    if not os.environ.get("ANDROID_ARGUMENT"):
        return {"ok": False, "error": "not_android"}
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        pm = act.getSystemService(autoclass("android.content.Context").POWER_SERVICE)
        pkg = act.getPackageName()
        if pm.isIgnoringBatteryOptimizations(pkg):
            return {"ok": True, "already": True}
        Intent = autoclass("android.content.Intent")
        i = Intent(autoclass("android.provider.Settings").ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
        i.setData(autoclass("android.net.Uri").parse("package:" + pkg))
        act.startActivity(i)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
