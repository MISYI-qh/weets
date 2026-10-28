"""Alat bawaan aplikasi WEETS: cari web, baca halaman, jalankan kode Python, buat berkas, ingatan ajaran.
Semua memakai pustaka standar Python (tanpa API/kunci). Pencarian & baca halaman butuh internet saat dipakai."""
import difflib, html, io, ipaddress, json, os, re, socket, subprocess, sys, tempfile, urllib.parse, urllib.request, zipfile

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


def search(q):
    q = q.strip()[:200]
    if not q:
        return {"error": "empty"}
    try:
        body, _, _ = _get("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": q}).encode(), timeout=15)
        res = parse_ddg(body.decode("utf-8", "replace"))
    except Exception as e:
        return {"error": "offline", "detail": type(e).__name__}
    return {"results": res} if res else {"error": "no_results"}


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
    ext = ext if ext in MIMES else "txt"
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
