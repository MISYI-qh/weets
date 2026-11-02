"""Pencarian web TANPA kunci API + pembaca halaman (mode baca untuk peramban dalam aplikasi).

Urutan: DuckDuckGo (html) -> DuckDuckGo (lite) -> Wikipedia Indonesia -> Wikipedia Inggris.
Semua kegagalan dicatat dengan sebab yang jelas (DNS, timeout, HTTP kode) supaya "kok tidak bisa internet?"
bisa dijawab dengan fakta, bukan tebakan."""
import gzip, html as _html, ipaddress, json, re, socket, time, zlib
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin, quote, unquote, parse_qs, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Mobile Safari/537.36")
MAX_BYTES = 3_000_000
STOP = set("yang dan di ke dari untuk dengan adalah itu ini apa siapa kapan berapa bagaimana cara tolong cari carikan "
           "tentang pada atau dalam saat hari terbaru sih dong ya kah lah sebuah para oleh akan sudah bisa".split())


class NetError(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind, self.detail = kind, detail


def _explain(e):
    if isinstance(e, HTTPError):
        return "http_%d" % e.code, str(e.reason)
    if isinstance(e, URLError):
        r = e.reason
        if isinstance(r, socket.gaierror):
            return "dns", "nama situs tidak bisa diterjemahkan (tidak ada internet / DNS diblokir)"
        if isinstance(r, socket.timeout) or "timed out" in str(r):
            return "timeout", "tidak ada jawaban tepat waktu"
        return "koneksi", str(r)
    if isinstance(e, socket.timeout):
        return "timeout", "tidak ada jawaban tepat waktu"
    return type(e).__name__, str(e)


def _decode(data, headers):
    enc = (headers.get("Content-Encoding") or "").lower()
    try:
        if enc == "gzip":
            data = gzip.decompress(data)
        elif enc == "deflate":
            data = zlib.decompress(data)
    except Exception:
        pass
    ctype = headers.get("Content-Type") or ""
    m = re.search(r"charset=([\w-]+)", ctype, re.I) or re.search(rb"charset=[\"']?([\w-]+)", data[:2048], re.I) and None
    cs = m.group(1) if m else None
    if not cs:
        mm = re.search(rb"charset=[\"']?([\w-]+)", data[:4096], re.I)
        cs = mm.group(1).decode("ascii", "ignore") if mm else "utf-8"
    try:
        return data.decode(cs, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def is_public_host(host):
    """Tolak alamat lokal/privat (agar fitur baca-tautan tidak bisa dipakai menyentuh server di HP sendiri)."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True       # biar kegagalan DNS dilaporkan sebagai 'dns' oleh fetch, bukan 'diblokir'
    for inf in infos:
        ip = ipaddress.ip_address(inf[4][0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch(url, timeout=12.0, data=None, headers=None, retries=2, opener=urlopen):
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise NetError("skema", "hanya http/https")
    if not is_public_host(p.hostname):
        raise NetError("diblokir", "alamat lokal/privat tidak boleh dibuka")
    h = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5",
         "Accept-Language": "id-ID,id;q=0.9,en;q=0.5", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    last = None
    for i in range(retries + 1):
        try:
            req = Request(url, data=data, headers=h)
            with opener(req, timeout=timeout) as r:
                raw = r.read(MAX_BYTES)
                return r.geturl(), _decode(raw, r.headers), (r.headers.get("Content-Type") or "")
        except Exception as e:
            kind, detail = _explain(e)
            last = NetError(kind, detail)
            if kind.startswith("http_4") and kind not in ("http_429", "http_408"):
                break
            time.sleep(0.6 * (i + 1))
    raise last


# ---------------- pencarian ----------------
def _clean(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _ddg_target(href):
    href = _html.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    q = parse_qs(urlparse(href).query)
    if "uddg" in q:
        return unquote(q["uddg"][0])
    return href


def parse_ddg_html(page):
    out = []
    blocks = re.split(r'<div[^>]+class="[^"]*result[^"]*results_links', page)
    for b in blocks[1:] if len(blocks) > 1 else [page]:
        a = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S) or \
            re.search(r'<a[^>]+href="([^"]+)"[^>]+class="result__a"[^>]*>(.*?)</a>', b, re.S)
        if not a:
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', b, re.S) or re.search(r'class="result__snippet"[^>]*>(.*?)</div>', b, re.S)
        url = _ddg_target(a.group(1))
        if urlparse(url).scheme not in ("http", "https") or "duckduckgo.com/y.js" in url:
            continue
        out.append({"title": _clean(a.group(2)), "url": url, "snippet": _clean(sn.group(1)) if sn else "", "source": "duckduckgo"})
    return out


def parse_ddg_lite(page):
    out = []
    for m in re.finditer(r"<a[^>]+rel=\"nofollow\"[^>]+href=\"([^\"]+)\"[^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", page, re.S):
        url = _ddg_target(m.group(1))
        tail = page[m.end(): m.end() + 1500]
        sn = re.search(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", tail, re.S)
        out.append({"title": _clean(m.group(2)), "url": url, "snippet": _clean(sn.group(1)) if sn else "", "source": "duckduckgo"})
    return out


def wiki_search(query, lang="id", n=5, opener=urlopen):
    u = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={quote(query)}"
         f"&gsrlimit={n}&prop=extracts%7Cinfo&exintro=1&explaintext=1&exsentences=4&inprop=url&redirects=1&exlimit={n}")
    _, body, _ = fetch(u, opener=opener)
    pages = (json.loads(body).get("query") or {}).get("pages") or {}
    res = sorted(pages.values(), key=lambda p: p.get("index", 99))
    return [{"title": p.get("title", ""), "url": p.get("fullurl") or f"https://{lang}.wikipedia.org/?curid={p.get('pageid')}",
             "snippet": _clean(p.get("extract", ""))[:700], "source": f"wikipedia-{lang}"} for p in res if p.get("extract")]


def search(query, n=6, opener=urlopen):
    """-> (hasil, log). log berisi sebab tiap kegagalan; hasil kosong hanya bila semua jalur gagal."""
    results, log = [], []
    steps = [
        ("duckduckgo", lambda: parse_ddg_html(fetch("https://html.duckduckgo.com/html/", data=urlencode({"q": query, "kl": "id-id"}).encode(),
                                                     headers={"Content-Type": "application/x-www-form-urlencoded"}, opener=opener)[1])),
        ("duckduckgo-lite", lambda: parse_ddg_lite(fetch("https://lite.duckduckgo.com/lite/", data=urlencode({"q": query, "kl": "id-id"}).encode(),
                                                          headers={"Content-Type": "application/x-www-form-urlencoded"}, opener=opener)[1])),
        ("wikipedia-id", lambda: wiki_search(query, "id", 4, opener)),
        ("wikipedia-en", lambda: wiki_search(query, "en", 3, opener)),
    ]
    for name, fn in steps:
        try:
            got = fn()
            log.append({"sumber": name, "ok": True, "jumlah": len(got)})
            for g in got:
                if g["url"] not in {r["url"] for r in results}:
                    results.append(g)
            if len(results) >= n and name.startswith("duckduckgo"):
                break
            if name == "wikipedia-id" and results:
                break
        except NetError as e:
            log.append({"sumber": name, "ok": False, "sebab": e.kind, "detail": e.detail})
            if e.kind in ("dns", "timeout", "koneksi") and name == "duckduckgo":
                continue
        except Exception as e:                      # parser/JSON rusak: lanjut ke jalur berikutnya
            log.append({"sumber": name, "ok": False, "sebab": type(e).__name__, "detail": str(e)[:120]})
    return results[:n], log


def diagnose(opener=urlopen):
    out = []
    for name, url in (("duckduckgo", "https://html.duckduckgo.com/html/?q=tes"), ("wikipedia", "https://id.wikipedia.org/w/api.php?action=query&meta=siteinfo&format=json")):
        t0 = time.time()
        try:
            fetch(url, timeout=8, retries=0, opener=opener)
            out.append({"situs": name, "ok": True, "ms": int((time.time() - t0) * 1000)})
        except NetError as e:
            out.append({"situs": name, "ok": False, "sebab": e.kind, "detail": e.detail})
    return out


# ---------------- pembaca halaman ----------------
class _Reader(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "iframe", "template", "button", "select"}
    BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "blockquote", "td", "th", "figcaption", "dd", "dt"}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.title, self.skip, self.in_title = base, "", 0, False
        self.blocks, self.cur, self.links, self.href, self.link_txt = [], [], [], None, []
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "meta" and a.get("property") in ("og:title", "og:description") and a.get("content"):
            self.meta[a["property"]] = a["content"]
        elif tag == "a" and a.get("href") and not self.skip:
            self.href, self.link_txt = a["href"], []
        if tag in self.BLOCK or tag == "br":
            self._flush(tag)

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "title":
            self.in_title = False
        elif tag == "a" and self.href:
            t = _clean(" ".join(self.link_txt))
            u = urljoin(self.base, self.href)
            if t and urlparse(u).scheme in ("http", "https") and len(self.links) < 60:
                self.links.append({"text": t[:90], "url": u.split("#")[0]})
            self.href = None
        if tag in self.BLOCK:
            self._flush(tag)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif not self.skip:
            self.cur.append(data)
            if self.href:
                self.link_txt.append(data)

    def _flush(self, tag=""):
        t = _clean(" ".join(self.cur))
        self.cur = []
        if len(t) >= (2 if tag.startswith("h") else 25):
            self.blocks.append(("h" if tag.startswith("h") else "p", t))


def read_page(url, opener=urlopen, max_chars=24000):
    final, page, ctype = fetch(url, opener=opener)
    if "html" not in ctype.lower() and not page.lstrip().startswith("<"):
        return {"url": final, "title": final, "text": page[:max_chars], "links": [], "kind": "teks"}
    r = _Reader(final)
    r.feed(page)
    r._flush()
    seen, parts = set(), []
    for kind, t in r.blocks:
        if t in seen:
            continue
        seen.add(t)
        parts.append(("## " if kind == "h" else "") + t)
    text = "\n\n".join(parts)[:max_chars]
    title = _clean(r.title) or r.meta.get("og:title", "") or urlparse(final).netloc
    if len(text) < 200 and r.meta.get("og:description"):
        text = r.meta["og:description"] + "\n\n" + text
    seen_l, links = set(), []
    for l in r.links:
        if l["url"] not in seen_l:
            seen_l.add(l["url"]); links.append(l)
    return {"url": final, "title": title[:200], "text": text, "links": links[:40], "kind": "html",
            "blocked": bool(re.search(r"captcha|access denied|enable javascript|verify you are human", page[:6000], re.I)) and len(text) < 400}


# ---------------- ekstraksi jawaban ----------------
def _sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text) if 25 <= len(s.strip()) <= 380]


def keywords(q):
    return [w for w in re.findall(r"[a-zA-Z0-9\-]{3,}", q.lower()) if w not in STOP]


def best_sentences(query, results, k=3):
    kw = set(keywords(query))
    cand = []
    for si, r in enumerate(results):
        for pos, s in enumerate(_sentences((r.get("snippet") or "") + " " + (r.get("text") or ""))):
            words = set(re.findall(r"[a-zA-Z0-9\-]{3,}", s.lower()))
            hit = len(kw & words)
            if kw and hit == 0 and pos > 0:
                continue
            score = hit * 2 + (1.0 if pos == 0 else 0) + (0.5 if si == 0 else 0) - pos * 0.05
            cand.append((score, si, s))
    cand.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for score, si, s in cand:
        key = s[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": s, "src": si + 1})
        if len(out) >= k:
            break
    return out
