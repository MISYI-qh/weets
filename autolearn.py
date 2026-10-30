"""Otonomi Weets: memilih sendiri apa yang dikerjakan di latar belakang.

Urutan pilihan (tiap siklus, dihitung dari keadaan nyata):
 1. Ada pelajaran / ketikan baru dari pengguna      -> latih (prioritas tertinggi)
 2. Online + ada tujuan belajar + anggaran harian   -> cari di web, baca halaman, pelajari teks berbahasa Indonesia
 3. Offline atau tidak ada yang baru                -> konsolidasi (ulang pelajaran lama agar tidak lupa) dan
                                                       uji pertumbuhan model dengan data lokal
Tujuan belajar (goals) berasal dari: daftar topik dasar, koreksi/ketikan pengguna, dan rasa ingin tahu (kata sering muncul
dari halaman yang baru dibaca). Tujuan yang berulang kali tak menghasilkan hal baru dipensiunkan (jenuh).
Yang memilih adalah penjadwal berbasis aturan + statistik nyata; modelnya sendiri belajar dari teks yang dipilih."""
import hashlib, json, os, random, re, threading, time

SEED_TOPICS = ["Indonesia", "Pancasila", "Sumpah Pemuda", "Proklamasi Kemerdekaan Indonesia", "Bahasa Indonesia", "Matahari", "Bumi", "Bulan",
               "Air", "Siklus air", "Hutan", "Laut", "Gunung berapi", "Listrik", "Internet", "Komputer", "Kecerdasan buatan", "Kesehatan",
               "Olahraga", "Gizi", "Sampah", "Daur ulang", "Pertanian", "Padi", "Pasar", "Uang", "Transportasi", "Pendidikan", "Perpustakaan",
               "Gotong royong", "Musim", "Gempa bumi", "Hewan", "Tumbuhan", "Fotosintesis", "Tata surya", "Batik", "Wayang", "Sungai", "Cuaca"]
_ID = set("yang dan di ke dari untuk dengan pada adalah ini itu tidak akan juga atau oleh dalam sebagai dapat karena sudah telah mereka kami kita saya".split())
DAILY_PAGES, DAILY_CHARS = 40, 600_000


def is_indonesian(text):
    w = re.findall(r"[a-zA-Z]+", text.lower())
    return len(w) >= 20 and sum(x in _ID for x in w) / len(w) >= 0.12


class Autonomy:
    def __init__(self, engine, home, apptools, load_settings):
        self.e, self.home, self.at, self.settings = engine, home, apptools, load_settings
        self.log_path = os.path.join(home, "activity.json")
        self.seen_path = os.path.join(home, "web_seen.json")
        self.web_path = os.path.join(home, "web_corpus.jsonl")
        self.cur = None
        self.t_web = self.t_cons = self.t_user = 0.0
        self.t_grow = time.time()
        self.pending_web = []        # teks web yang sudah dikumpulkan tapi belum dilatih
        self.last_action = ""

    # ---------------------------------------------------------------- util
    def curriculum(self):
        if self.cur is None:
            from weets.curiosity import Curriculum
            self.cur = Curriculum(os.path.join(self.home, "curriculum.db"))
            if not self.cur.goals():
                for t in SEED_TOPICS:
                    self.cur.add_goal(t, 0.5, "seed")
        return self.cur

    def log(self, kind, detail=""):
        try:
            try:
                with open(self.log_path, encoding="utf-8") as f:
                    a = json.load(f)
            except Exception:
                a = []
            a.append({"ts": int(time.time()), "kind": kind, "detail": detail[:140]})
            tmp = self.log_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(a[-60:], f, ensure_ascii=False)
            os.replace(tmp, self.log_path)
        except Exception:
            pass
        self.last_action = kind

    def _seen(self):
        try:
            with open(self.seen_path, encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()

    def _save_seen(self, s):
        with open(self.seen_path, "w", encoding="utf-8") as f:
            json.dump(sorted(s)[-8000:], f)

    def status(self):
        try:
            with open(self.log_path, encoding="utf-8") as f:
                acts = json.load(f)
        except Exception:
            acts = []
        c = self.curriculum()
        _, pages, chars = c.day_usage()
        gs = c.goals()
        return {"online": self.at.online(), "activity": acts[-12:][::-1], "goals": sum(g["status"] == "active" for g in gs),
                "saturated": sum(g["status"] == "saturated" for g in gs), "pages_today": pages, "chars_today": chars,
                "pending_web": sum(len(x) for x in self.pending_web)}

    # ---------------------------------------------------------------- tujuan dari pengguna
    def seed_user_goals(self, d):
        try:
            c = self.curriculum()
            for t in d.get("topics", [])[:40]:
                c.add_goal(str(t)[:120], 1.5, "failure")
            for t in d.get("texts", [])[-20:]:
                c.seed_from_text(str(t), k=2, min_count=1)
        except Exception:
            pass

    # ---------------------------------------------------------------- aksi
    def learn_from_web(self):
        c = self.curriculum()
        _, pages, chars = c.day_usage()
        if pages >= DAILY_PAGES or chars >= DAILY_CHARS:
            return False
        g = c.next_goal(cooldown=1800)
        if not g:
            return False
        res = self.at.search(g["topic"])
        if res.get("error") == "offline":          # koneksi putus / DNS gagal: bukan "tidak ada yang baru", jangan hitung sebagai jenuh
            self.at._online[0], self.at._online[1] = time.time() + 240, False      # anggap offline 5 menit
            self.log("offline", "pencarian gagal; lanjut dengan data lokal")
            return False
        accepted = got = 0
        text_all = ""
        if res.get("results"):
            order = sorted(res["results"], key=lambda r: 0 if re.search(r"wikipedia\.org|\.go\.id|\.ac\.id|\.edu", r["url"]) else 1)
            seen = self._seen()
            for r in order[:3]:
                h = hashlib.sha1(r["url"].encode()).hexdigest()[:16]
                if h in seen:
                    continue
                pg = self.at.page(r["url"])
                seen.add(h)
                if pg.get("error"):
                    continue
                paras = [p.strip() for p in pg["text"].split("\n\n") if len(p.strip()) >= 80 and is_indonesian(p)]
                text = "\n\n".join(paras)[:6000]
                if len(text) >= 300:
                    self.pending_web.append(text)
                    accepted += 1
                    got += len(text)
                    text_all += "\n" + text
                    with open(self.web_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"url": r["url"], "text": text}, ensure_ascii=False) + "\n")
                    break
            self._save_seen(seen)
        c.record(g["id"], accepted, got)
        c.add_usage(1 if res.get("results") else 0, got)
        if text_all:
            c.seed_from_text(text_all, k=2, min_count=3)
        self.log("web", ("%s: +%d huruf" % (g["topic"], got)) if got else ("%s: tidak ada yang baru" % g["topic"]))
        return True

    def flush_web(self):
        """Latih teks web yang terkumpul (dengan pengulangan materi dasar agar gaya jawab tidak berubah)."""
        if sum(len(x) for x in self.pending_web) < 3000 or self.e.st["running"]:
            return False
        texts, self.pending_web = self.pending_web[:6], self.pending_web[6:]
        r = self.e.train_start({"qa": [], "texts": texts, "preset": "quick"})
        self.log("train-web" if r.get("ok") else "skip", "%d halaman web dilatih" % len(texts))
        return bool(r.get("ok"))

    def consolidate(self):
        d = self.e.lessons()
        qa = d.get("qa", [])
        web = []
        try:
            with open(self.web_path, encoding="utf-8") as f:
                web = [json.loads(l)["text"] for l in f if l.strip()][-30:]
        except Exception:
            pass
        if len(qa) < 5 and len(web) < 3:
            return False
        sample = random.sample(qa, min(len(qa), 40))
        texts = random.sample(web, min(len(web), 2))
        r = self.e.train_start({"qa": [{"q": x["q"], "a": x["a"]} for x in sample], "texts": texts, "preset": "quick"})
        self.log("konsolidasi" if r.get("ok") else "skip", "ulang %d pelajaran, %d teks web" % (len(sample), len(texts)))
        return bool(r.get("ok"))

    # ---------------------------------------------------------------- satu siklus keputusan
    def step(self):
        e = self.e
        if not e.ok or not e.ready() or e.st["running"] or e._lock_busy():
            return "sibuk"
        s = self.settings()
        if not s.get("auto_learn", True):
            return "mati"
        now = time.time()
        d = e.lessons()
        self.seed_user_goals(d)
        ks = set(d.get("learned", []))
        qa = [(x["q"], x["a"]) for x in d.get("qa", []) if e._key(x["q"], x["a"]) not in ks]
        tx = [t for t in d.get("texts", []) if e._key(t) not in ks]
        # 1) pelajaran baru dari pengguna
        if now - self.t_user > 300 and (len(qa) >= 3 or sum(len(t) for t in tx) >= 600):
            self.t_user = now
            r = e.train_start({"qa": [{"q": q, "a": a} for q, a in qa[:200]], "texts": tx[:20], "preset": "quick"})
            self.log("train-user", "%d pelajaran, %d teks" % (len(qa), len(tx)))
            return "user" if r.get("ok") else "gagal"
        # 2) online: belajar dari web
        if s.get("web_learn", True) and self.at.online():
            if self.flush_web():
                return "flush"
            if now - self.t_web > 600:
                self.t_web = now
                if self.learn_from_web():
                    return "web"
        # 3) lokal: konsolidasi + tumbuh
        if now - self.t_cons > 7200:
            self.t_cons = now
            if self.consolidate():
                return "konsolidasi"
        if s.get("auto_grow", True) and now - self.t_grow > 6 * 3600 and len(d.get("qa", [])) >= 20:
            self.t_grow = now
            hist = [g for g in e.growth_log() if g.get("kind") in ("add_layers", "grow_mlp")]
            r = e.grow_start("grow_mlp" if len(hist) % 2 else "add_layers", [{"prompt": x["q"], "response": x["a"]} for x in d["qa"][-200:]])
            self.log("tumbuh", "uji kapasitas" if r.get("ok") else "skip")
            return "tumbuh"
        return "diam"

    def run(self):
        while True:
            time.sleep(60)
            try:
                self.step()
            except Exception as ex:
                self.log("galat", type(ex).__name__ + ": " + str(ex)[:80])
