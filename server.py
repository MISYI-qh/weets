#!/usr/bin/env python3
"""Server lokal Weets (di bawah naungan Misyi). Obrolan, pelatihan, dan ekspor/impor model memakai paket `weets` (NumPy).
Semua berjalan di perangkat sendiri: server hanya mendengarkan 127.0.0.1."""
import apptools, autolearn, growapp, io, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def _home():
    want = os.environ.get("WEETS_HOME") or os.path.join(ROOT, "weets_home")
    try:
        os.makedirs(want, exist_ok=True)
        t = os.path.join(want, ".w")
        open(t, "w").close()
        os.remove(t)
        return want
    except OSError:
        alt = os.path.join(tempfile.gettempdir(), "weets_home")
        os.makedirs(alt, exist_ok=True)
        return alt


HOME = _home()
MODEL_DIR = os.path.join(HOME, "model")
CUR = os.path.join(MODEL_DIR, "current.npz")
PREV = os.path.join(MODEL_DIR, "previous.npz")
JOBS = os.path.join(HOME, "jobs")
SETTINGS = os.path.join(HOME, "settings.json")
GROWLOG = os.path.join(HOME, "growth.json")
LESSONS = os.path.join(HOME, "lessons.json")
LOCK = os.path.join(HOME, "job.lock")
MAX_PARAMS = int(os.environ.get("WEETS_MAX_PARAMS", 6_000_000))
STARTER = os.path.join(ROOT, "model", "weets-starter.wt")
SEED = os.path.join(ROOT, "model", "seed.jsonl")
STATIC = {"/": "index.html", "/index.html": "index.html", "/manifest.json": "manifest.json", "/icon.png": "icon.png",
          "/icon-1024.png": "icon-1024.png", "/icon.svg": "icon.svg", "/favicon.ico": "icon.png"}
MIME = {".html": "text/html; charset=utf-8", ".json": "application/manifest+json", ".png": "image/png", ".svg": "image/svg+xml"}
MAX_UPLOAD = 800 * 1024 * 1024
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(JOBS, exist_ok=True)


def ensure_numpy():
    import importlib.util as u
    if u.find_spec("numpy") is None and not os.environ.get("ANDROID_ARGUMENT"):
        print("Mengunduh NumPy…")
        subprocess.call([sys.executable, "-m", "pip", "install", "-q", "numpy"])


ensure_numpy()


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(s):
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f)
    os.replace(tmp, SETTINGS)


def export_dir():
    """Folder tujuan ekspor di perangkat (Download di Android bila bisa ditulis)."""
    for d in ("/storage/emulated/0/Download", os.path.expanduser("~/Downloads"), os.path.expanduser("~/Download")):
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
    d = os.path.join(HOME, "exports")
    os.makedirs(d, exist_ok=True)
    return d


def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


class Engine:
    def __init__(self):
        import importlib.util as u
        self.np = u.find_spec("numpy") is not None
        self.pkg = u.find_spec("weets") is not None
        self.ok = self.np and self.pkg
        self.gen, self.gen_key = None, None
        self.lock = threading.RLock()
        self.proc, self.cancel = None, False
        self.st = self._idle()
        self._info, self._info_key = None, None
        if self.ok:
            self._seed_model()
            if not os.environ.get("WEETS_SERVICE"):
                threading.Thread(target=self._warm, daemon=True).start()

    def _warm(self):
        """Muat model di latar belakang supaya pesan pertama tidak menunggu."""
        try:
            if self.ready():
                self._gen()
        except Exception:
            pass

    @staticmethod
    def _idle():
        return dict(running=False, phase="", step=0, total=0, loss=[], log=[], eta=None, done=False, error="", id=0)

    # ------------------------------------------------------------------ model files
    def _seed_model(self):
        """Pasang model bawaan pada jalan pertama (kalau belum ada model)."""
        if os.path.exists(CUR) or not os.path.exists(STARTER):
            return
        try:
            from weets import wt
            with open(STARTER, "rb") as f:
                _, payload = wt.verify_and_extract(f.read())
            atomic_write(CUR, payload)
        except Exception as e:
            print("Model bawaan gagal dipasang:", e)

    def ready(self):
        return os.path.exists(CUR)

    # kunci lintas-proses: aplikasi dan layanan latar belakang tidak boleh melatih bersamaan
    def _lock_acquire(self):
        for _ in range(2):
            try:
                fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                apptools.wake(True)
                return True
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(LOCK) > 1800:      # kunci basi (proses mati)
                        os.remove(LOCK)
                        continue
                except OSError:
                    continue
                return False
            except OSError:
                return True      # tidak bisa membuat kunci: jangan blokir
        return False

    def _lock_release(self):
        apptools.wake(False)
        try:
            os.remove(LOCK)
        except OSError:
            pass

    def _lock_touch(self):
        try:
            os.utime(LOCK, None)
        except OSError:
            pass

    def _lock_busy(self):
        try:
            return time.time() - os.path.getmtime(LOCK) < 1800
        except OSError:
            return False

    def status(self):
        return {"engine": self.ok, "numpy": self.np, "model": self.pkg, "ready": self.ready(), "training": self.st["running"] or (self._lock_busy() and not self.st["running"]), "phase": self.st.get("phase", "") or ("train" if self._lock_busy() else "")}

    def info(self):
        if not self.ok or not self.ready():
            return {"ready": False}
        key = (os.path.getmtime(CUR), os.path.exists(PREV))
        if self._info_key == key:
            return self._info
        from weets.checkpoint import load_checkpoint
        from weets.config import ModelConfig
        ck = load_checkpoint(CUR)
        c = ModelConfig(**ck["model_config"])
        n = int(sum(int(v.size) for v in ck["model"].values()))
        tr = ck.get("train_config") or {}
        self._info = {"ready": True, "params": n, "layers": c.n_layer, "width": c.n_embd, "heads": c.n_head, "block": c.block_size,
                      "vocab": c.vocab_size, "step": int(ck["step"]), "bytes": os.path.getsize(CUR),
                      "updated": int(os.path.getmtime(CUR)), "has_prev": os.path.exists(PREV),
                      "tokenizer": (ck.get("tokenizer") or {}).get("type", "utf8-byte"), "mode": tr.get("mode", ""),
                      "merges": len((ck.get("tokenizer") or {}).get("merges", []) or []), "growth": self.growth_log()[-6:]}
        self._info_key = key
        return self._info

    def growth_log(self):
        try:
            with open(GROWLOG, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _glog(self, entry):
        g = self.growth_log() + [dict(entry, ts=int(time.time()))]
        tmp = GROWLOG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(g[-40:], f)
        os.replace(tmp, GROWLOG)
        self._info_key = None

    def _install(self, payload):
        """Pasang checkpoint .npz baru jadi model aktif; yang lama disimpan sebagai 'previous'."""
        with self.lock:
            if os.path.exists(CUR):
                shutil.copy2(CUR, PREV)
            atomic_write(CUR, payload)
            self.gen, self._info_key = None, None

    def export_bytes(self, with_opt=False, name="Weets"):
        from weets import wt
        if not self.ready():
            raise wt.WtError("no_model", "belum ada model")
        return wt.pack(CUR, include_optimizer=with_opt, name=name)

    def import_bytes(self, data):
        from weets import wt
        if self.st["running"]:
            raise wt.WtError("busy", "sedang melatih")
        h, payload = wt.verify_and_extract(data)
        self._install(payload)
        return wt.info_of(h)

    def revert(self):
        with self.lock:
            if self.st["running"] or not os.path.exists(PREV):
                return False
            tmp = CUR + ".swap"
            shutil.copy2(CUR, tmp)
            shutil.copy2(PREV, CUR)
            os.replace(tmp, PREV)
            self.gen, self._info_key = None, None
        return True

    def reset(self):
        from weets import wt
        if self.st["running"] or not os.path.exists(STARTER):
            return False
        with open(STARTER, "rb") as f:
            _, payload = wt.verify_and_extract(f.read())
        self._install(payload)
        return True

    # ------------------------------------------------------------------ chat
    def _gen(self):
        with self.lock:
            key = os.path.getmtime(CUR)
            if self.gen is None or self.gen_key != key:
                from weets.inference import WeetsGenerator
                self.gen = WeetsGenerator(CUR, "cpu")
                self.gen_key = key
            return self.gen

    def chat(self, messages, style="seimbang", instructions="", taught=()):
        """Hasilkan potongan teks demi potongan (benar-benar streaming)."""
        last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if last and taught:        # ajaran pengguna dijawab seketika, tanpa menunggu pelatihan
            q = str(last.get("content", "")).split("\n\n")[-1]
            hit = apptools.match_taught(q, taught)
            if hit:
                for i in range(0, len(hit), 24):
                    yield {"token": hit[i:i + 24]}
                return
        if not self.ok:
            yield {"err": "no_engine"}
            return
        if not self.ready():
            yield {"err": "no_model"}
            return
        yield {"st": "read"}
        import numpy as np
        from weets.reasoning import split_thinking
        from weets.sft import messages_to_prompt_ids
        from weets.stopping import is_looping
        from weets.tokenizer import EOS
        g = self._gen()
        msgs = [{"role": m["role"], "content": str(m["content"])} for m in messages if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()]
        if instructions.strip():
            msgs.insert(0, {"role": "system", "content": instructions.strip()[:400]})
        ctx = g.model.config.block_size
        while True:   # potong riwayat dari depan sampai muat konteks (menyisakan ruang untuk jawaban)
            ids = messages_to_prompt_ids(msgs, g.tokenizer)
            if len(ids) <= ctx - 48 or len(msgs) <= 1:
                break
            msgs = msgs[1:] if msgs[0]["role"] != "system" or len(msgs) == 2 else [msgs[0]] + msgs[2:]
        if len(ids) > ctx - 16:                          # satu pesan saja sudah terlalu panjang: ambil ujung belakangnya
            ids = ids[:1] + ids[-(ctx - 16):]
        yield {"st": "compose"}
        limit = {"ringkas": 120, "seimbang": 320, "rinci": 700}.get(style, 320)
        said_think = False
        rng = np.random.default_rng()
        all_ids, start, t0, sent = list(ids), len(ids), time.time(), ""
        g.touch()
        thinking = False
        while len(all_ids) - start < limit and time.time() - t0 < 180:
            idx = np.asarray([all_ids[-ctx:]], dtype=np.int64)
            out = g.model.generate(idx, 6 if len(all_ids) == start else 16, 0.2, 10, EOS, 1.0, 1.0, True, rng=rng)   # suhu rendah: model kecil jauh lebih rapi
            new = out[0].tolist()[idx.shape[1]:]
            if not new:
                break
            ended = new[-1] == EOS
            all_ids.extend(new)
            text = g.tokenizer.decode(all_ids[start:])
            cut = text.find("\nUser:")
            if cut >= 0:
                text, ended = text[:cut], True
            thinking = "<think>" in text
            if thinking and not said_think:
                said_think = True
                yield {"st": "think"}
            if not thinking and not (text.endswith("\ufffd") and not ended) and len(text) > len(sent):
                yield {"token": text[len(sent):]}
                sent = text
            if ended or is_looping(all_ids[start:]):
                break
        yield {"st": "check"}
        text = g.tokenizer.decode(all_ids[start:])
        cut = text.find("\nUser:")
        text = text[:cut] if cut >= 0 else text
        if "<think>" in text:
            think, vis = split_thinking(text)
            if think:
                yield {"think": think}
            yield {"token": vis} if vis else {"err": "empty"}
        elif len(text) > len(sent):
            yield {"token": text[len(sent):]}
        elif not text.strip():
            yield {"err": "empty"}

    # ------------------------------------------------------------------ files
    def extract(self, data, name):
        """Berkas (pdf/docx/xlsx/pptx/html/gambar/audio/teks) -> teks. Memakai weets.ingest."""
        from weets import ingest
        try:
            docs = ingest.parse_bytes(data, name or "")
        except ingest.IngestError as e:
            return {"error": "unreadable", "detail": str(e)[:300]}
        text = "\n\n".join(d.text for d in docs if getattr(d, "text", "")).strip()
        if not text:
            return {"error": "empty", "detail": ""}
        return {"text": text[:300000], "chars": len(text), "ocr": any("ocr" in (getattr(d, "notes", []) or []) for d in docs)}

    def fetch_link(self, url):
        from weets import ingest
        try:
            data, ctype, final = ingest.fetch_url(url, timeout=15.0, max_bytes=5_000_000)
            docs = ingest.parse_bytes(data, final, ctype)
        except ingest.IngestError as e:
            return {"error": "unreadable", "detail": str(e)[:300]}
        text = "\n\n".join(d.text for d in docs if getattr(d, "text", "")).strip()
        return {"text": text[:300000]} if text else {"error": "empty"}

    # ------------------------------------------------------------------ training
    def train_start(self, c):
        if not self.ok:
            return {"error": "no_engine"}
        if not self.ready():
            return {"error": "no_model"}
        with self.lock:
            if self.st["running"] or not self._lock_acquire():
                return {"error": "already_running"}
            qa = [(str(x.get("q", "")).strip(), str(x.get("a", "")).strip()) for x in c.get("qa", [])]
            qa = [(q, a) for q, a in qa if q and a]
            texts = [str(t).strip() for t in c.get("texts", []) if str(t).strip()]
            links = [str(u) for u in c.get("links", []) if str(u).startswith(("http://", "https://"))][:10]
            if not qa and not texts and not links:
                self._lock_release()
                return {"error": "no_data"}
            preset = c.get("preset", "balanced")
            adv = c.get("advanced") or {}
            jid = int(time.time())
            self.st = dict(self._idle(), running=True, phase="prepare", log=["…"], id=jid)
            self.cancel = False
        threading.Thread(target=self._job, args=(jid, qa, texts, links, preset, adv), daemon=True).start()
        return {"ok": True}

    def _log(self, line):
        self.st["log"] = (self.st["log"] + [line])[-200:]
        self.st["ts"] = time.time()
        self._lock_touch()

    def _job(self, jid, qa, texts, links, preset, adv):
        job = os.path.join(JOBS, str(jid))
        try:
            os.makedirs(job, exist_ok=True)
            for u in links:
                if self.cancel:
                    raise InterruptedError
                r = self.fetch_link(u)
                if r.get("text"):
                    texts.append(r["text"])
                    self._log("OK link: " + u[:70])
                else:
                    self._log("SKIP link: " + u[:70])
            phases = []
            tx = "\n\n".join(texts)
            raw_tx = tx           # teks asli (tanpa pengulangan) untuk belajar kosakata
            if len(tx.encode("utf-8")) >= 32:
                p = os.path.join(job, "train.txt")
                base = tx
                while len(tx.encode("utf-8")) < 8000:      # teks pendek diulang supaya cukup untuk dilatih
                    tx += "\n\n" + base
                with open(p, "w", encoding="utf-8") as f:
                    f.write(tx)
                phases.append(("pretrain", p, len(tx.encode("utf-8")) + 2))
            if qa:
                rows = [{"prompt": q, "response": a} for q, a in qa] * 10     # materi baru diulang agar benar-benar melekat
                if os.path.exists(SEED):            # ulangi materi dasar supaya kemampuan lama tidak hilang
                    with open(SEED, encoding="utf-8") as f:
                        seed = [json.loads(l) for l in f if l.strip()]
                    import random
                    random.Random(5).shuffle(seed)
                    rows += seed            # seluruh materi dasar diulang tiap latihan agar kemampuan lama tidak luntur
                while len(rows) < 4:
                    rows += rows
                p = os.path.join(job, "train.jsonl")
                with open(p, "w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                phases.append(("sft", p, len(rows)))
                self._rows = rows
            if phases and not qa and os.path.exists(SEED):     # hanya teks: ulangi materi dasar sesudahnya supaya gaya jawab tidak berubah
                with open(SEED, encoding="utf-8") as f:
                    rows = [json.loads(l) for l in f if l.strip()]
                p = os.path.join(job, "replay.jsonl")
                with open(p, "w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                phases.append(("sft", p, len(rows)))
            if not phases:
                raise ValueError("no_data")
            from weets.checkpoint import load_checkpoint
            block = int(load_checkpoint(CUR)["model_config"]["block_size"])
            grown = None
            try:        # 1) kosakata tumbuh bila terbukti memperpendek teksmu (token baru ditambahkan, yang lama tetap)
                self.st["phase"] = "grow"
                sample = [raw_tx] if raw_tx else []
                sample += ["User: %s\nAssistant: %s\n" % (q, a) for q, a in qa]
                if os.path.exists(SEED):
                    with open(SEED, encoding="utf-8") as f:
                        sample += ["User: %s\nAssistant: %s\n" % (d["prompt"], d["response"]) for d in (json.loads(l) for l in f if l.strip())]
                grown, rep = growapp.grow_vocab(CUR, sample, os.path.join(job, "grown.npz"))
                if grown:
                    self._glog({"kind": "vocab", "decision": "promoted", "vocab_before": rep["vocab_before"], "vocab_after": rep["vocab_after"],
                                "tpb_before": round(rep["tpb_before"], 3), "tpb_after": round(rep["tpb_after"], 3)})
                    self._log("Kosakata tumbuh: %d -> %d token" % (rep["vocab_before"], rep["vocab_after"]))
            except Exception as e:
                grown = None
                self._log("Kosakata tidak ditumbuhkan: %s" % str(e)[:120])
            self.st["phase"] = "train"
            epochs = {"quick": (1, 20), "balanced": (3, 50), "deep": (6, 120)}.get(preset, (3, 50))
            min_sft = {"quick": 80, "balanced": 150, "deep": 300}.get(preset, 80)
            src, total_steps, plans = (grown or CUR), 0, []
            vocab_grew = bool(grown)
            for kind, path, size in phases:
                batch = int(adv.get("batch") or 4)
                if kind == "sft":
                    steps = max(min_sft, min(2000, min_sft + 3 * len(qa)))
                    if vocab_grew:
                        steps = max(steps, 500)
                else:
                    steps = max(20, min(800, int(epochs[0] * size / (batch * block) + 0.999)))
                if adv.get("steps"):
                    steps = max(1, min(20000, int(adv["steps"])))
                plans.append((kind, path, steps, batch))
                total_steps += steps
            self.st.update(total=total_steps, step=0, phase="train", log=self.st["log"] + ["Mulai: %d langkah" % total_steps])
            done = 0
            trained_any = False
            for n, (kind, path, steps, batch) in enumerate(plans):
                out = os.path.join(job, "p%d" % n)
                lr = float(adv.get("lr") or (3e-4 if kind == "pretrain" else 6e-4))
                budget = {"quick": 45, "balanced": 110, "deep": 280}.get(preset, 110)
                args = ["--max-seconds", str(adv.get("max_seconds") or budget), "--data", path, "--out-dir", out, "--steps", str(steps), "--batch-size", str(batch), "--grad-accum", "1",
                        "--lr", str(lr), "--min-lr", str(lr / 10), "--warmup-steps", str(max(1, steps // 10)),
                        "--eval-interval", str(steps), "--eval-batches", "3", "--save-interval", str(steps),
                        "--mode", kind, "--device", "cpu", "--init-from", src]
                if not self._run(args, done, steps):
                    if self.cancel:
                        raise InterruptedError
                    if "Dataset too small" in (self.st.get("error") or "") and len(plans) > 1:     # teks terlalu sedikit: lewati tahap ini saja
                        self._log("Tahap dilewati: bahan terlalu sedikit")
                        self.st["error"] = ""
                        done += steps
                        continue
                    raise RuntimeError("train_failed")
                last = os.path.join(out, "last.npz")
                if not os.path.exists(last):
                    raise RuntimeError("train_failed")
                src, done = last, done + steps
                trained_any = True
            if not trained_any:
                raise RuntimeError("Bahan terlalu sedikit untuk dilatih")
            with open(src, "rb") as f:
                payload = f.read()
            self._install(payload)
            self.st.update(step=total_steps, done=True, phase="done", eta=0)
            self._log("OK")
            self._mark_learned(qa, texts)
            self.notify("Weets", "Selesai berlatih")
            self._pending_after = (len(qa) + len(texts), list(getattr(self, "_rows", [])[:400]))
        except InterruptedError:
            self.st.update(phase="cancelled")
        except Exception as e:
            msg = self.st.get("error") or str(e)
            self.st.update(error=msg[:300], phase="error")
            self._log("ERROR: " + msg[:300])
        finally:
            self.st["running"] = False
            self.proc = None
            self._lock_release()
            shutil.rmtree(job, ignore_errors=True)
            pend, self._pending_after = getattr(self, "_pending_after", None), None
            if pend:
                try:
                    self._after_job(*pend)
                except Exception:
                    pass

    def _line(self, line, base, steps, t0):
        line = line.rstrip()
        if not line:
            return
        self._log(line)
        m = re.search(r"step\s+(\d+) \| train_loss ([\d.]+)", line)
        if m:
            s = int(m.group(1)) + 1
            self.st["step"] = base + min(s, steps)
            self.st["loss"].append(float(m.group(2)))
            if s > 3:
                self.st["eta"] = int((time.time() - t0) / s * max(0, steps - s))

    def _run_inproc(self, args, base, steps):
        """Android (APK): tidak ada interpreter terpisah, jadi pelatihan dijalankan di thread yang sama proses."""
        import io, contextlib
        from weets import train as wtrain
        eng, t0 = self, time.time()

        class W(io.TextIOBase):
            buf = ""

            def write(s, x):
                s.buf += x
                while "\n" in s.buf:
                    ln, s.buf = s.buf.split("\n", 1)
                    eng._line(ln, base, steps, t0)
                if eng.cancel:
                    raise InterruptedError
                return len(x)
        try:
            with contextlib.redirect_stdout(W()), contextlib.redirect_stderr(W()):
                wtrain.train(args)
            return True
        except InterruptedError:
            return False
        except SystemExit as e:
            return not e.code
        except Exception as e:
            self.st["error"] = str(e)[:300]
            return False

    def _run(self, args, base, steps):
        if os.environ.get("ANDROID_ARGUMENT") or os.environ.get("PYTHON_SERVICE_ARGUMENT") or not (sys.executable and os.path.exists(sys.executable)):
            return self._run_inproc(args, base, steps)
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONPATH=ROOT)
        t0 = time.time()
        self.proc = subprocess.Popen([sys.executable, "-m", "weets", "train"] + args, cwd=ROOT, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        tail = []
        for line in self.proc.stdout:
            line = line.rstrip()
            tail = (tail + [line])[-6:]
            self._log(line)
            m = re.search(r"step\s+(\d+) \| train_loss ([\d.]+)", line)
            if m:
                s = int(m.group(1)) + 1
                self.st["step"] = base + min(s, steps)
                self.st["loss"].append(float(m.group(2)))
                el = time.time() - t0
                if s > 3:
                    self.st["eta"] = int(el / s * max(0, steps - s))
            if self.cancel:
                self.proc.terminate()
        self.proc.wait()
        if self.proc.returncode != 0 and not self.cancel:
            self.st["error"] = " ".join(tail[-2:])[:300]
        return self.proc.returncode == 0 and not self.cancel

    # ------------------------------------------------------------------ penumbuhan kapasitas (eksperimen kontrol vs kandidat)
    def grow_start(self, kind="add_layers", rows=None):
        if not self.ok or not self.ready():
            return {"error": "no_model"}
        if kind not in ("add_layers", "grow_mlp"):
            return {"error": "bad_kind"}
        with self.lock:
            if self.st["running"] or not self._lock_acquire():
                return {"error": "already_running"}
            jid = int(time.time())
            self.st = dict(self._idle(), running=True, phase="grow", log=["Eksperimen tumbuh: " + kind], id=jid, total=1)
            self.cancel = False
        threading.Thread(target=self._grow_job, args=(jid, kind, rows or []), daemon=True).start()
        return {"ok": True}

    def _grow_job(self, jid, kind, rows):
        job = os.path.join(JOBS, "g%d" % jid)
        try:
            os.makedirs(job, exist_ok=True)
            base = list(rows)
            if os.path.exists(SEED):
                with open(SEED, encoding="utf-8") as f:
                    base += [json.loads(l) for l in f if l.strip()]
            text = growapp.corpus_text(base)
            while len(text.encode("utf-8")) < 12000:
                text += text
            cp = os.path.join(job, "corpus.txt")
            with open(cp, "w", encoding="utf-8") as f:
                f.write(text)
            rep = growapp.capacity_experiment(CUR, cp, job, kind, steps=120, max_params=MAX_PARAMS)
            entry = {"kind": kind, "decision": rep.get("decision"), "reason": rep.get("reason", ""),
                     "params_before": rep.get("params_before"), "params_after": rep.get("params_after"),
                     "control_loss": round(rep["control_loss"], 4) if "control_loss" in rep else None,
                     "candidate_loss": round(rep["candidate_loss"], 4) if "candidate_loss" in rep else None}
            if rep.get("decision") == "promoted" and rep.get("promoted_to"):
                with open(rep["promoted_to"], "rb") as f:
                    self._install(f.read())
            self._glog(entry)
            self.st.update(done=True, phase="done", grow=entry, step=1, total=1)
        except Exception as e:
            self.st.update(error=str(e)[:300], phase="error")
            self._log("ERROR: " + str(e)[:300])
        finally:
            self.st["running"] = False
            self._lock_release()
            shutil.rmtree(job, ignore_errors=True)
        self.notify("Weets", "Eksperimen pertumbuhan selesai")

    def notify(self, title, text):
        try:
            apptools.native_notify(title, text)
        except Exception:
            pass

    # ------------------------------------------------------------------ pelajaran tersimpan + pembelajar latar belakang
    @staticmethod
    def _key(*parts):
        import hashlib
        return hashlib.sha1("\x00".join(parts).encode("utf-8")).hexdigest()[:16]

    def lessons(self):
        try:
            with open(LESSONS, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"qa": [], "texts": [], "learned": []}

    def save_lessons(self, qa, texts, topics=()):
        d = self.lessons()
        d["topics"] = [str(t)[:120] for t in list(topics)[:60]]
        d["qa"] = [{"q": str(x.get("q", ""))[:500], "a": str(x.get("a", ""))[:1000]} for x in qa[:2000] if x.get("q") and x.get("a")]
        d["texts"] = [str(t)[:20000] for t in texts[:500] if str(t).strip()]
        tmp = LESSONS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, LESSONS)

    def _mark_learned(self, qa, texts):
        d = self.lessons()
        ks = set(d.get("learned", []))
        ks.update(self._key(q, a) for q, a in qa)
        ks.update(self._key(t) for t in texts)
        d["learned"] = sorted(ks)[-5000:]
        tmp = LESSONS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, LESSONS)

    def autonomy(self):
        if getattr(self, "_auto", None) is None:
            self._auto = autolearn.Autonomy(self, HOME, apptools, load_settings)
        return self._auto

    def _learner(self):
        """Pembelajar mandiri (lihat autolearn.py): dijalankan layanan latar depan di Android, atau thread server di desktop."""
        self.autonomy().run()

    def diag(self, bench=False):
        info = {"python": sys.version.split()[0], "android": bool(os.environ.get("ANDROID_ARGUMENT")), "exe": sys.executable or "", "exe_ok": bool(sys.executable and os.path.exists(sys.executable)),
                "home": HOME, "model": self.ready(), "engine": self.ok}
        try:
            import numpy as np
            info["numpy"] = np.__version__
            if bench:
                a = np.random.rand(256, 256).astype(np.float32)
                t0 = time.time()
                for _ in range(20):
                    a @ a
                dt = max(time.time() - t0, 1e-9)
                info["matmul_gflops"] = round(20 * 2 * 256 ** 3 / dt / 1e9, 2)
                if self.ready():
                    g = self._gen()
                    ids = np.random.randint(5, g.model.config.vocab_size, size=(1, min(64, g.model.config.block_size)))
                    t0 = time.time()
                    g.model.generate(ids, 8, 0.2, 10, 3, 1.0, 1.0, True, rng=np.random.default_rng(1))
                    info["gen_tok_s"] = round(8 / max(time.time() - t0, 1e-9), 1)
        except Exception as e:
            info["error"] = str(e)[:200]
        return info

    def prefs(self):
        s = load_settings()
        return {"auto_grow": bool(s.get("auto_grow", True)), "auto_learn": bool(s.get("auto_learn", True)), "web_learn": bool(s.get("web_learn", True)), "max_params": MAX_PARAMS}

    def _after_job(self, n_new, rows):
        """Tumbuh otomatis: tiap +60 bahan baru, uji penambahan kapasitas; hanya dipakai kalau terbukti lebih baik."""
        s = load_settings()
        s["since_growth"] = int(s.get("since_growth", 0)) + n_new
        go = bool(s.get("auto_grow", True)) and s["since_growth"] >= 60
        if go:
            s["since_growth"] = 0
        save_settings(s)
        if go:
            hist = [g for g in self.growth_log() if g.get("kind") in ("add_layers", "grow_mlp")]
            time.sleep(0.5)
            self.grow_start("grow_mlp" if len(hist) % 2 else "add_layers", rows)

    def train_stop(self):
        self.cancel = True
        p = self.proc
        if p and self.st["running"]:
            try:
                p.terminate()
            except Exception:
                pass


E = Engine()


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0] if not (self.headers.get("Host") or "").startswith("[") else "[::1]"
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            return False
        o = self.headers.get("Origin")
        if o and o != "null":
            oh = urllib.parse.urlparse(o).hostname or ""
            if oh not in ("127.0.0.1", "localhost", "::1"):
                return False
        return True

    def _json(self, o, code=200):
        b = json.dumps(o).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self, limit=MAX_UPLOAD):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            self.close_connection = True
            return None
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        if not self._host_ok():
            return self._json({"error": "forbidden"}, 403)
        u = urllib.parse.urlparse(self.path)
        p = u.path
        if p == "/api/status":
            return self._json(E.status())
        if p == "/api/model/info":
            try:
                return self._json(E.info())
            except Exception as e:
                return self._json({"ready": False, "error": str(e)[:200]})
        if p == "/api/train/status":
            return self._json(E.st)
        if p == "/api/prefs":
            return self._json(E.prefs())
        if p == "/api/bg":
            return self._json(E.autonomy().status())
        if p == "/api/diag":
            return self._json(E.diag(urllib.parse.parse_qs(u.query).get("bench", ["0"])[0] == "1"))
        if p == "/browse":
            tgt = (urllib.parse.parse_qs(u.query).get("u") or [""])[0]
            data, ctype, code = apptools.browse(tgt)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if p == "/api/model/export":
            q = urllib.parse.parse_qs(u.query)
            try:
                data = E.export_bytes(with_opt=q.get("opt", ["0"])[0] == "1", name=(q.get("name", ["Weets"])[0] or "Weets")[:24])
            except Exception as e:
                return self._json({"error": getattr(e, "code", "failed"), "detail": str(e)[:200]}, 400)
            fn = "weets-%s.wt" % time.strftime("%Y%m%d-%H%M")
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % fn)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if p in STATIC:
            fp = os.path.join(ROOT, STATIC[p])
            try:
                with open(fp, "rb") as f:
                    b = f.read()
            except OSError:
                return self._json({"error": "not found"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(os.path.splitext(fp)[1], "application/octet-stream"))
            if fp.endswith(".html") and "gzip" in (self.headers.get("Accept-Encoding") or ""):
                import gzip
                b = gzip.compress(b, 6)
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(b)
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._host_ok():
            return self._json({"error": "forbidden"}, 403)
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/model/import":
            data = self._body()
            if data is None:
                return self._json({"error": "too_big"}, 413)
            try:
                return self._json({"ok": True, "info": E.import_bytes(data)})
            except Exception as e:
                code = getattr(e, "code", "failed")
                return self._json({"error": code, "detail": str(e)[:200]}, 400)
        if p == "/api/extract":
            data = self._body(60 * 1024 * 1024)
            if data is None:
                return self._json({"error": "too_big"}, 413)
            name = urllib.parse.unquote(self.headers.get("X-Filename") or "")
            return self._json(E.extract(data, name))
        raw = self._body(8 * 1024 * 1024)
        if raw is None:
            return self._json({"error": "too_big"}, 413)
        try:
            b = json.loads(raw or b"{}")
        except Exception:
            return self._json({"error": "bad_json"}, 400)
        if p == "/api/chat":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                for ev in E.chat(b.get("messages", []), b.get("style", "seimbang"), b.get("instructions", ""), b.get("taught", [])):
                    self.wfile.write((json.dumps(ev) + "\n").encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self.wfile.write((json.dumps({"err": "failed", "detail": str(e)[:200]}) + "\n").encode())
                except Exception:
                    pass
            return
        if p == "/api/train/start":
            return self._json(E.train_start(b))
        if p == "/api/train/stop":
            E.train_stop()
            return self._json({"ok": True})
        if p == "/api/model/revert":
            return self._json({"ok": E.revert()})
        if p == "/api/model/reset":
            return self._json({"ok": E.reset()})
        if p == "/api/model/save":
            try:
                data = E.export_bytes(with_opt=bool(b.get("opt")), name=str(b.get("name") or "Weets")[:24])
                fp = os.path.join(export_dir(), "weets-%s.wt" % time.strftime("%Y%m%d-%H%M"))
                atomic_write(fp, data)
                return self._json({"ok": True, "path": fp, "bytes": len(data)})
            except Exception as e:
                return self._json({"error": getattr(e, "code", "failed"), "detail": str(e)[:200]}, 400)
        if p == "/api/grow":
            return self._json(E.grow_start(str(b.get("kind", "add_layers")), [{"prompt": str(x.get("q", "")), "response": str(x.get("a", ""))} for x in b.get("qa", [])[:300]]))
        if p == "/api/battery":
            return self._json(apptools.ask_battery())
        if p == "/api/notify":
            E.notify(str(b.get("title", "Weets"))[:60], str(b.get("text", ""))[:160])
            return self._json({"ok": True})
        if p == "/api/lessons":
            E.save_lessons(b.get("qa", []), b.get("texts", []), b.get("topics", []))
            return self._json({"ok": True})
        if p == "/api/prefs":
            s_ = load_settings()
            if "auto_learn" in b:
                s_["auto_learn"] = bool(b["auto_learn"])
            if "web_learn" in b:
                s_["web_learn"] = bool(b["web_learn"])
            if "auto_grow" in b:
                s_["auto_grow"] = bool(b["auto_grow"])
            save_settings(s_)
            return self._json({"ok": True})
        if p == "/api/search":
            return self._json(apptools.search(str(b.get("q", ""))))
        if p == "/api/page":
            return self._json(apptools.page(str(b.get("url", ""))))
        if p == "/api/run":
            return self._json(apptools.run_python(str(b.get("code", ""))))
        if p == "/api/makefile":
            data, mime, ext = apptools.make_file(str(b.get("ext", "txt")), str(b.get("title", ""))[:120], str(b.get("content", ""))[:400000])
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Ext", ext)
            self.end_headers()
            self.wfile.write(data)
            return
        self._json({"error": "not found"}, 404)


def serve(port, block=True):
    ThreadingHTTPServer.daemon_threads = True
    if not os.environ.get("WEETS_NO_LEARNER"):
        threading.Thread(target=E._learner, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    if block:
        srv.serve_forever()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print("Weets di http://localhost:%d" % port)
    serve(port)
