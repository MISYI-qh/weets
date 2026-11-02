"""Mesin obrolan Weets: sampling anti-slop, gaya, alat (cari/baca/hitung/ingat), dan status yang jujur."""
import ast, json, math, operator, os, random, re, threading, time
import numpy as np
from weets.checkpoint import load_checkpoint, tokenizer_from_checkpoint
from weets.config import ModelConfig
from weets.model import WeetsModel
from weets.sft import messages_to_prompt_ids
from weets.tokenizer import EOS, BOS, BASE_VOCAB
from weets.wordtok import TAGS, CONTROL, PUNCT, DIGITS
from weets.corpus import candor, philo
import websearch

STYLES = ("normal", "jujur", "toxic", "puitis")
TEMP = {"normal": 0.7, "jujur": 0.7, "toxic": 0.8, "puitis": 0.9}

# 50 kata status: (kata, tahap). Indeks = nomor animasi di UI (tiap kata animasinya berbeda).
STATUS = [
 ("Membaca", "baca"), ("Menyimak", "baca"), ("Mencerna", "baca"), ("Memahami", "baca"), ("Menelaah", "baca"), ("Mengamati", "baca"), ("Meresapi", "baca"),
 ("Mengingat", "ingat"), ("Menggali ingatan", "ingat"), ("Mengumpulkan", "ingat"), ("Mengenang", "ingat"),
 ("Mencari", "cari"), ("Menjelajah", "cari"), ("Menyisir web", "cari"), ("Menelusuri", "cari"), ("Memburu sumber", "cari"), ("Menyaring hasil", "cari"), ("Membandingkan sumber", "cari"),
 ("Membuka tautan", "buka"), ("Memasuki halaman", "buka"), ("Membaca halaman", "buka"), ("Mengekstrak isi", "buka"), ("Merangkum halaman", "buka"),
 ("Menghitung", "hitung"), ("Menakar", "hitung"), ("Menjumlah", "hitung"), ("Mengukur", "hitung"), ("Memverifikasi angka", "hitung"),
 ("Berpikir", "pikir"), ("Merenung", "pikir"), ("Mempertimbangkan", "pikir"), ("Menalar", "pikir"), ("Mengurai", "pikir"), ("Merumuskan", "pikir"), ("Menyusun gagasan", "pikir"), ("Menimbang", "pikir"),
 ("Menyusun", "susun"), ("Menulis", "susun"), ("Merangkai kata", "susun"), ("Memilih kata", "susun"), ("Menganyam kalimat", "susun"), ("Meracik", "susun"), ("Memoles", "susun"), ("Menyelaraskan nada", "susun"),
 ("Memeriksa", "periksa"), ("Memastikan", "periksa"), ("Menyaring klise", "periksa"), ("Menguji ulang", "periksa"), ("Meninjau", "periksa"), ("Menutup", "periksa"),
]
assert len(STATUS) == 50 and len({w for w, _ in STATUS}) == 50
POOL = {}
for _i, (_w, _s) in enumerate(STATUS):
    POOL.setdefault(_s, []).append([_w, _i])

SLOP = ["sebagai ai", "sebagai model bahasa", "sebagai asisten", "tentu saja", "tentu!", "semoga membantu", "saya di sini untuk membantu",
        "dengan senang hati", "perlu diingat bahwa", "pada dasarnya", "di era digital", "tidak dapat dipungkiri", "kesimpulannya",
        "jangan ragu untuk", "senang bisa membantu", "itu pertanyaan yang bagus", "pertanyaan bagus"]
CRISIS = re.compile(r"(bunuh diri|mengakhiri (hidup|semuanya)|ingin mati|mau mati|pengen mati|pengin mati|(nggak|ga|gak|tidak) (mau|ingin|pengen) hidup|"
                    r"lebih baik aku (nggak|ga|gak|tidak) ada|menyakiti diri|melukai diri|self.?harm|suicide)", re.I)
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
SEARCH_EXPLICIT = re.compile(r"\b(cari|carikan|googling|telusuri|browsing|cek di web|cari tahu|search)\b", re.I)
SEARCH_FRESH = re.compile(r"\b(terbaru|hari ini|sekarang|berita|cuaca|jadwal|kurs|skor|hasil pertandingan|harga)\b", re.I)
SEARCH_Q = re.compile(r"^\s*(siapa|apa itu|apa yang dimaksud|kapan|di ?mana|berapa|bagaimana cara|bagaimana proses|tahun berapa|jelaskan)\b", re.I)
PERSONAL = re.compile(r"\b(menurutmu|kamu|aku|filsafat|puisi|pantun|sajak|makna|arti hidup|bandingkan|sudut pandang|pendapatmu)\b", re.I)
MEM_SAVE = re.compile(r"^\s*(tolong\s+)?(ingat(kan)?(\s+aku)?(\s+bahwa|\s+ini)?|catat|simpan(\s+ini)?)\s*[:,]?\s+(.+)$", re.I | re.S)
MEM_LIST = re.compile(r"(apa (yang )?(kamu )?(ingat|catat)|catatanku|daftar catatan)", re.I)
LEAD = ["Dari yang kutemukan:", "Ringkasnya:", "Menurut sumber di bawah:", "Ini yang tertulis:", "Yang kutemukan:"]


# ---------------- hitung aman ----------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos}


def safe_eval(expr):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 64 or abs(a) > 1e6):
                raise ValueError("pangkat terlalu besar")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("ekspresi tidak aman")
    return ev(ast.parse(expr, mode="eval"))


def fmt_num(x):
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        x = int(x)
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    s = f"{round(x, 6):,.6f}".rstrip("0").rstrip(".")
    a, _, b = s.partition(".")
    return a.replace(",", ".") + ("," + b if b else "")


def find_math(text):
    t = text.replace("×", "*").replace("÷", "/").replace("^", "**")
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", t)
    t = re.sub(r"(?<=\d)\.(?=\d{3}(\D|$))", "", t).replace(",", ".")
    m = re.search(r"[-+]?\(*\s*\d+(?:\.\d+)?(?:\s*(?:\*\*|//|[-+*/%])\s*\(*\s*[-+]?\d+(?:\.\d+)?\s*\)*)+", t)
    if not m:
        return None
    expr = m.group(0).strip()
    if not re.search(r"(berapa|hitung|=|\?|sama dengan)", text, re.I) and len(expr) < len(text.strip()) * 0.5:
        return None
    try:
        return expr, safe_eval(expr)
    except Exception:
        return None


def strip_tags(s):
    return re.sub(r"</?(think|cari|buka|hitung|hasil|ingat|cek|gaya_\w+)>", "", s)


class Engine:
    def __init__(self, data_dir, starter=None, log=print):
        self.dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.lock = threading.RLock()
        self.log = log
        self.activity = time.time()
        self.model = self.tok = self.cfg = None
        self.step = 0
        self.ckpt = os.path.join(data_dir, "current.npz")
        self.notes_path = os.path.join(data_dir, "notes.json")
        self.notes = self._load_notes()
        self.stats = {"chats": 0, "searches": 0, "search_fail": 0}
        self.starter = starter
        ok = False
        if os.path.exists(self.ckpt):
            try:
                self.load()
                ok = getattr(self.tok, "kind", "") == "word"
            except Exception as e:                       # berkas lama/rusak (mis. dari Weets versi per huruf)
                self.log("[model] checkpoint lama tidak terbaca:", e)
            if not ok:
                try:
                    os.replace(self.ckpt, self.ckpt + ".lama")
                except OSError:
                    pass
                self.model = self.tok = self.cfg = None
        if not ok and starter and os.path.exists(starter):
            from wt import import_blob
            with open(starter, "rb") as f:
                import_blob(f.read(), self.ckpt)
            self.load()
        if os.path.exists(self.ckpt):
            self._mtime = os.path.getmtime(self.ckpt)
        self._ban = None

    # ---------------- model ----------------
    def load(self):
        ck = load_checkpoint(self.ckpt)
        cfg = ModelConfig(**ck["model_config"]).validate()
        tok = tokenizer_from_checkpoint(ck)
        m = WeetsModel(cfg)
        m.load_state_dict(ck["model"])
        m.eval()
        with self.lock:
            self.model, self.tok, self.cfg, self.step = m, tok, cfg, int(ck["step"])
            self._ban = None
        return self

    @property
    def ready(self):
        return self.model is not None

    def reload_if_changed(self):
        """Layanan latar belakang bisa menulis checkpoint baru; muat bila berkas berubah."""
        try:
            m = os.path.getmtime(self.ckpt)
        except OSError:
            return False
        if m > getattr(self, "_mtime", 0) + 0.5:
            first = not hasattr(self, "_mtime")
            self._mtime = m
            if not first and self.ready:
                self.load()
                return True
        return False

    def info(self):
        if not self.ready:
            return {"ready": False}
        c = self.cfg
        return {"ready": True, "params": int(sum(v.size for v in self.model.params.values())), "vocab": self.tok.vocab_size,
                "layers": c.n_layer, "heads": c.n_head, "width": c.n_embd, "block": c.block_size, "step": self.step,
                "mlp": c.hidden_dim()}

    def touch(self):
        self.activity = time.time()

    # ---------------- catatan ----------------
    def _load_notes(self):
        try:
            with open(self.notes_path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def _save_notes(self):
        tmp = self.notes_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.notes, fh, ensure_ascii=False)
        os.replace(tmp, self.notes_path)

    def add_note(self, text):
        text = text.strip()[:500]
        self.notes.append({"id": int(time.time() * 1000), "text": text, "t": int(time.time())})
        self.notes = self.notes[-300:]
        self._save_notes()
        return text

    def del_note(self, nid):
        self.notes = [n for n in self.notes if n["id"] != nid]
        self._save_notes()

    # ---------------- sampling ----------------
    def _banned(self):
        if self._ban is None:
            seqs = set()
            for p in SLOP:
                for v in (p, p.capitalize()):
                    ids = tuple(self.tok.encode(v))
                    if len(ids) >= 2:
                        seqs.add(ids)
            self._ban = list(seqs)
            exempt = set(range(BASE_VOCAB)) | {self.tok.stoi[t] for t in CONTROL + TAGS if t in self.tok.stoi}
            for p in PUNCT + DIGITS:
                for k in (p, "\u2581" + p):
                    if k in self.tok.stoi:
                        exempt.add(self.tok.stoi[k])
            self._exempt = exempt
            self._tooltok = [self.tok.stoi[t] for t in ("<cari>", "</cari>", "<buka>", "</buka>", "<hitung>", "</hitung>", "<hasil>", "</hasil>", "<ingat>", "</ingat>", "<cek>", "</cek>") if t in self.tok.stoi]
        return self._ban

    def stream_ids(self, prompt_ids, max_new, temperature, rng, stop_ids=(), top_k=40, top_p=0.92, rep=1.12, stats=None):
        ban = self._banned()
        model, tok = self.model, self.tok
        bs = model.config.block_size
        ids = list(prompt_ids)[-(bs - 8):]
        gen, tri, lps = [], set(), []
        logits, caches = model.forward_cached(np.asarray([ids], dtype=np.int64), None)
        for _ in range(max_new):
            lg = logits[0, -1].astype(np.float64)
            if len(ids) + 1 >= bs:
                break
            counts = {}
            for t in gen[-80:]:
                if t not in self._exempt:
                    counts[t] = counts.get(t, 0) + 1
            for t, c in counts.items():
                lg[t] = lg[t] / rep if lg[t] > 0 else lg[t] * rep
            if len(gen) >= 3:                                   # larang 4-gram yang sudah pernah muncul
                a, b, c = gen[-3], gen[-2], gen[-1]
                for (w, x, y, z) in tri:
                    if w == a and x == b and y == c and z not in self._exempt:
                        lg[z] = -1e9
            for seq in ban:                                     # larang frasa klise
                k = len(seq) - 1
                if len(gen) >= k and tuple(gen[-k:]) == seq[:-1]:
                    lg[seq[-1]] = -1e9
            for tt in self._tooltok:                           # alat dijalankan oleh aplikasi, bukan ditebak model
                lg[tt] = -1e9
            lg[tok.pad_token_id] = lg[tok.bos_token_id] = -1e9
            lg[256 + 3] = -1e9
            if temperature <= 0:
                nxt = int(lg.argmax())
            else:
                lg = lg / temperature
                kth = np.partition(lg, -top_k)[-top_k]
                lg = np.where(lg < kth, -1e9, lg)
                pr = np.exp(lg - lg.max()); pr /= pr.sum()
                si = np.argsort(-pr); cs = np.cumsum(pr[si])
                keep = si[(cs - pr[si]) <= top_p]
                p2 = np.zeros_like(pr); p2[keep] = pr[keep]; p2 /= p2.sum()
                nxt = int(rng.choice(len(p2), p=p2))
                pr = p2
            if stats is not None:
                z = lg - lg.max() if temperature <= 0 else None
                lps.append(math.log(max(float(pr[nxt]) if temperature > 0 else 1.0, 1e-9)))
                stats["lp"] = sum(lps) / len(lps)
            if len(gen) >= 3:
                tri.add((gen[-3], gen[-2], gen[-1], nxt))
            gen.append(nxt)
            yield nxt
            if nxt == EOS or nxt in stop_ids:
                break
            logits, caches = model.forward_cached(np.asarray([[nxt]], dtype=np.int64), caches)

    # ---------------- bantu ----------------
    def _prompt(self, messages, style, max_new):
        msgs = [{"role": "system", "content": f"<gaya_{style}>"}]
        keep = []
        for m in messages:
            if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip():
                c = URL_RE.sub("<url>", strip_tags(str(m["content"])))
                keep.append({"role": m["role"], "content": c[:1200]})
        while keep and keep[0]["role"] != "user":
            keep.pop(0)
        budget = self.cfg.block_size - 96 if max_new > 96 else self.cfg.block_size - max_new - 8
        while True:
            ids = messages_to_prompt_ids(msgs + keep, self.tok)
            if len(ids) <= budget or len(keep) <= 1:
                return ids[-budget:] if len(ids) > budget else ids
            keep = keep[2:] if len(keep) > 2 else keep[-1:]

    def wants_search(self, text):
        if SEARCH_EXPLICIT.search(text):
            return True
        if PERSONAL.search(text) and not SEARCH_FRESH.search(text):
            return False
        if any(t in text.lower() for t in philo.TOPIK) and not SEARCH_FRESH.search(text):
            return False
        return bool(SEARCH_Q.search(text) or SEARCH_FRESH.search(text)) and len(text) < 220

    @staticmethod
    def make_query(text):
        q = URL_RE.sub(" ", text)
        q = re.sub(r"\b(tolong|dong|ya|sih|deh|cari(kan)?|cek|cari tahu|telusuri|googling|di web|di internet|jelaskan|apa itu|untukku|aku)\b", " ", q, flags=re.I)
        q = re.sub(r"[?!.]+", " ", q)
        return re.sub(r"\s+", " ", q).strip()[:120] or text[:120]

    @staticmethod
    def stage(name):
        return {"t": "stage", "stage": name, "pool": POOL[name]}

    def clean_output(self, s):
        s = strip_tags(s)
        for p in SLOP:
            s = re.sub(re.escape(p), "", s, flags=re.I)
        parts = re.split(r"(?<=[.!?])\s+", s.strip())
        seen, out = set(), []
        for p in parts:
            k = re.sub(r"\W+", " ", p.lower()).strip()
            if k and k in seen and len(k) > 12:
                continue
            seen.add(k)
            out.append(p)
        return re.sub(r"[ \t]+\n", "\n", " ".join(out) if "\n" not in s else s).strip()

    # ---------------- obrolan ----------------
    def chat(self, messages, style="normal", opts=None):
        """Generator event: stage / think / delta / sources / done / error."""
        opts = opts or {}
        style = style if style in STYLES else "normal"
        self.touch()
        t0 = time.time()
        user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user = str(m.get("content", "")); break
        yield self.stage("baca")
        self.stats["chats"] += 1
        # 1) krisis: selalu peduli, apa pun gayanya
        if CRISIS.search(user):
            yield {"t": "delta", "text": candor.KRISIS_JAWAB[0]}
            yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "krisis"}
            return
        # 2) catatan
        if MEM_LIST.search(user) and len(user) < 80:
            yield self.stage("ingat")
            txt = ("Catatanmu:\n" + "\n".join(f"- {n['text']}" for n in self.notes[-15:])) if self.notes else "Belum ada catatan yang kusimpan."
            yield {"t": "delta", "text": txt}; yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "catatan"}
            return
        m = MEM_SAVE.match(user) if not URL_RE.search(user) else None
        if m and len(m.group(7)) >= 3:
            yield self.stage("ingat")
            note = self.add_note(m.group(7))
            yield {"t": "delta", "text": f"Sudah kucatat: {note}"}
            yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "catat"}
            return
        # 3) hitung
        mm = find_math(user)
        if mm:
            yield self.stage("hitung")
            expr, val = mm
            yield {"t": "delta", "text": f"{re.sub(r'\*\*', '^', expr)} = {fmt_num(val)}"}
            yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "hitung"}
            return
        # 4) tautan -> peramban dalam aplikasi
        urls = URL_RE.findall(user)[:2]
        if urls:
            yield from self._open_urls(urls, user, t0)
            return
        # 5) cari web
        if opts.get("web", True) and self.wants_search(user):
            fresh = bool(SEARCH_FRESH.search(user) or SEARCH_EXPLICIT.search(user))
            ok = yield from self._search(user, t0, fallback=not fresh and self.ready)
            if ok is not False:
                return
            yield {"t": "delta", "text": "Web tidak terjangkau, jadi ini dari ingatan modelku dan bisa keliru:\n\n"}
        # 6) model
        if not self.ready:
            yield {"t": "error", "text": "Model belum dimuat. Buka halaman Model lalu impor .wt atau tunggu pelatihan awal."}
            return
        ids = self._prompt(messages, style, 120)
        max_new = max(24, min(int(opts.get("max_new", 230)), self.cfg.block_size - len(ids) - 6))
        rng = np.random.default_rng(opts.get("seed"))
        stop = {self.tok.stoi.get("</cari>", -1), self.tok.stoi.get("</hitung>", -1)}
        gen, stats, shown, in_think = [], {}, "", True
        yield self.stage("pikir")
        with self.lock:
            for tid in self.stream_ids(ids, max_new, TEMP[style], rng, stop, stats=stats):
                gen.append(tid)
                raw = self.tok.decode(gen, skip_special=False)
                if "</think>" in raw and in_think:
                    in_think = False
                    yield {"t": "think", "text": re.sub(r"</?think>", "", raw.split("</think>")[0])}
                    yield self.stage("susun")
                vis = raw.split("</think>", 1)[1] if "</think>" in raw else ("" if raw.lstrip().startswith("<think>") else raw)
                vis = strip_tags(vis).lstrip()
                if len(vis) > len(shown):
                    yield {"t": "delta", "text": vis[len(shown):]}; shown = vis
        raw = self.tok.decode(gen, skip_special=False)
        # model meminta alat sendiri
        mc = re.search(r"<cari>(.*?)</cari>", raw, re.S)
        if mc and opts.get("web", True):
            yield {"t": "reset"}
            yield from self._search(mc.group(1).strip() or user, t0, query_is_clean=True)
            return
        mh = re.search(r"<hitung>(.*?)</hitung>", raw, re.S)
        if mh:
            try:
                val = safe_eval(mh.group(1).strip())
                yield {"t": "reset"}
                yield self.stage("hitung")
                yield {"t": "delta", "text": f"{mh.group(1).strip()} = {fmt_num(val)}"}
                yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "hitung"}
                return
            except Exception:
                pass
        yield self.stage("periksa")
        final = self.clean_output(raw.split("</think>", 1)[1] if "</think>" in raw else raw)
        if gen and gen[-1] != EOS and len(gen) >= max_new - 1:      # terpotong di batas panjang: akhiri di kalimat utuh
            cut = max(final.rfind(". "), final.rfind(".\n"), final.rfind("!"), final.rfind("?"), final.rfind(";\n"))
            if cut > len(final) * 0.5:
                final = final[:cut + 1]
        lp = stats.get("lp", 0.0)
        if len(final) < 2:
            final = "Aku belum punya jawaban yang layak untuk itu. Mau kucarikan di web?"
        if final != shown.strip():
            yield {"t": "reset"}
            yield {"t": "delta", "text": final}
        yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "model", "tokens": len(gen), "logprob": round(lp, 3)}

    def _search(self, text, t0, query_is_clean=False, fallback=False):
        q = text if query_is_clean else self.make_query(text)
        yield self.stage("cari")
        self.stats["searches"] += 1
        res, log = websearch.search(q)
        if not res:
            self.stats["search_fail"] += 1
            why = "; ".join(f"{l['sumber']}: {l.get('sebab', 'kosong')}" for l in log if not l.get("ok")) or "tidak ada hasil"
            if fallback:
                return False
            yield {"t": "delta", "text": f"Aku sudah mencoba mencari \"{q}\" tetapi gagal ({why}). Periksa koneksi ponselmu, atau buka Pengaturan > Tes koneksi untuk melihat penyebab pastinya."}
            yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "cari", "log": log}
            return True
        top = res[:5]
        need = [r for r in top[:2] if len(r.get("snippet", "")) < 160]
        if need:
            yield self.stage("buka")
            for r in need:
                try:
                    p = websearch.read_page(r["url"])
                    r["text"] = p["text"][:6000]
                except Exception:
                    pass
        yield {"t": "sources", "items": [{"title": r["title"], "url": r["url"], "snippet": r.get("snippet", "")[:220],
                                           "host": re.sub(r"^www\.", "", re.sub(r"^https?://", "", r["url"]).split("/")[0])} for r in top]}
        yield self.stage("susun")
        sents = websearch.best_sentences(q, top, 3)
        if sents:
            body = "\n".join(f"{s['text']} [{s['src']}]" for s in sents)
            txt = f"{random.choice(LEAD)}\n\n{body}"
        else:
            txt = "Ada beberapa halaman yang relevan, tetapi tidak ada kalimat yang cukup jelas menjawabnya. Buka sumber di bawah."
        yield {"t": "delta", "text": txt}
        yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "cari", "log": log}
        return True

    def _open_urls(self, urls, user, t0):
        yield self.stage("buka")
        items, parts = [], []
        q = self.make_query(user)
        for u in urls:
            try:
                p = websearch.read_page(u)
            except websearch.NetError as e:
                parts.append(f"Gagal membuka {u}: {e.kind} ({e.detail}).")
                continue
            host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", p["url"]).split("/")[0])
            items.append({"title": p["title"], "url": p["url"], "snippet": p["text"][:200].replace("\n", " "), "host": host})
            yield self.stage("buka")
            if p.get("blocked"):
                parts.append(f"Halaman {host} menghalangi pembaca otomatis. Kamu bisa membukanya di peramban dalam aplikasi.")
                continue
            sents = websearch.best_sentences(q if len(q) > 3 else "", [{"snippet": "", "text": p["text"]}], 4) if q else []
            if not sents:
                paras = [x for x in p["text"].split("\n\n") if not x.startswith("##")][:2]
                body = "\n".join(x[:300] for x in paras)
            else:
                body = "\n".join(s["text"] for s in sents)
            parts.append(f"{p['title']} ({host})\n{body}")
        if items:
            yield {"t": "sources", "items": items}
        yield self.stage("susun")
        yield {"t": "delta", "text": "\n\n".join(parts) or "Tautannya tidak bisa kubuka."}
        yield {"t": "done", "ms": int((time.time() - t0) * 1000), "mode": "buka"}
