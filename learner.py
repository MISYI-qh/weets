"""Belajar & tumbuh sendiri. Satu siklus: ambil teks baru -> (kosakata tumbuh) -> latih -> uji -> terima/buang -> (kapasitas tumbuh).
Setiap perubahan dinilai di data uji yang tidak pernah dilatih: perubahan yang membuat Weets lupa atau lebih buruk DIBUANG."""
import hashlib, json, math, os, random, re, shutil, threading, time
from dataclasses import replace
import numpy as np
from weets.checkpoint import load_checkpoint, save_checkpoint, tokenizer_from_checkpoint
from weets.config import ModelConfig, TrainConfig
from weets.data import SFTBatcher
from weets.growth import grow_layers, grow_mlp, migrate_vocab
from weets.model import WeetsModel
from weets.optim import AdamW, clip_grad_norm
from weets.optstate import param_groups, carry_state, restore_hparams, names_for_config
from weets.sft import build_example, record_to_segments
from weets.corpus import build as corpus
import websearch

STOPWORDS = set("yang dan di dari untuk dengan adalah pada ini itu dalam juga tidak akan oleh ke sebagai atau telah dapat karena".split())


def now():
    return int(time.time())


def looks_indonesian(t):
    w = re.findall(r"[a-zA-Z]+", t.lower())
    if len(w) < 25:
        return False
    return sum(1 for x in w if x in STOPWORDS) / len(w) >= 0.07


def clean_passage(t):
    t = re.sub(r"\[\d+\]|\[sunting[^\]]*\]", "", t)
    t = re.sub(r"\([^)]{0,3}\)", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    lines = [l.strip() for l in t.split("\n") if len(l.strip()) >= 40 and not l.strip().startswith("==")]
    return "\n".join(lines).strip()


def quality_ok(t):
    if len(t) < 200 or len(t) > 4000:
        return False
    letters = sum(c.isalpha() for c in t)
    return letters / len(t) > 0.7 and looks_indonesian(t)


class Learner:
    def __init__(self, engine, data_dir, max_params=6_000_000, max_layers=8, log=print):
        self.eng, self.dir, self.log = engine, data_dir, log
        self.max_params, self.max_layers = max_params, max_layers
        self.p = {k: os.path.join(data_dir, v) for k, v in dict(
            web="web.jsonl", lessons="lessons.jsonl", seen="seen.json", life="life.jsonl", state="learner_state.json",
            dev_base="dev_base.jsonl", dev_web="dev_web.jsonl").items()}
        self.backup_dir = os.path.join(data_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.state = {"cycles": 0, "accepted": 0, "rejected": 0, "plateau": 0, "grow_cooldown": 0, "next_grow": "mlp",
                      "enabled": True, "background": None, "only_charging": False, "idle_seconds": 45, "budget_seconds": 90, "version": "0.0.0",
                      "last": "", "running": False, "history": []}
        try:
            self.state.update(json.load(open(self.p["state"], encoding="utf-8")))
        except Exception:
            pass
        self.state["running"] = False
        self._stop = threading.Event()
        self._force = threading.Event()
        self._thread = None
        self.battery_ok = lambda only_charging: True
        self.online = lambda: True
        if not os.path.exists(self.p["dev_base"]):
            r = random.Random(4242)
            corpus.write_jsonl(self.p["dev_base"], corpus.dialogs(r, 0.03)[:300])

    # ---------------- penyimpanan ----------------
    PREFS = ("enabled", "only_charging", "idle_seconds", "budget_seconds", "background")

    def refresh(self):
        """Proses UI dan layanan latar belakang berbagi satu berkas keadaan: UI memegang pengaturan, layanan memegang hitungan."""
        try:
            with open(self.p["state"], encoding="utf-8") as fh:
                disk = json.load(fh)
        except Exception:
            return
        service = os.environ.get("WEETS_SERVICE") == "1"
        for k, v in disk.items():
            if k == "running":
                continue
            if (k in self.PREFS) == service:
                self.state[k] = v

    def _save_state(self):
        self.refresh()
        tmp = self.p["state"] + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, ensure_ascii=False)
        os.replace(tmp, self.p["state"])

    def _event(self, kind, **kw):
        e = {"t": now(), "kind": kind, **kw}
        self.state["last"] = f"{kind}: " + ", ".join(f"{k}={v}" for k, v in kw.items())[:200]
        self.state["history"] = (self.state["history"] + [e])[-40:]
        try:
            with open(self.p["life"], "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        except OSError:
            pass
        self._save_state()
        self.log("[belajar]", e)

    @staticmethod
    def _read(path, limit=None):
        if not os.path.exists(path):
            return []
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
        return out[-limit:] if limit else out

    def add_lesson(self, text):
        text = text.strip()[:3000]
        if len(text) < 8:
            raise ValueError("materi terlalu pendek")
        with open(self.p["lessons"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"text": text, "t": now(), "used": 0}, ensure_ascii=False) + "\n")
        self._force.set()
        return len(self._read(self.p["lessons"]))

    # ---------------- pengumpulan teks ----------------
    def fetch_web(self, topics=(), n_random=3):
        """Ambil paragraf Wikipedia Indonesia. Mengembalikan jumlah paragraf baru yang lolos."""
        seen = set()
        try:
            seen = set(json.load(open(self.p["seen"], encoding="utf-8")))
        except Exception:
            pass
        new = []
        urls = [("https://id.wikipedia.org/w/api.php?action=query&format=json&generator=random&grnnamespace=0&grnlimit=6"
                 "&prop=extracts&explaintext=1&exlimit=6&exchars=1800")] * n_random
        for t in topics[:3]:
            urls.append("https://id.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=%s&gsrlimit=3"
                        "&prop=extracts&explaintext=1&exlimit=3&exchars=1800" % websearch.quote(t))
        for u in urls:
            try:
                _, body, _ = websearch.fetch(u, timeout=15, retries=1)
                pages = (json.loads(body).get("query") or {}).get("pages") or {}
            except websearch.NetError as e:
                self._event("web_gagal", sebab=e.kind, detail=e.detail[:80])
                break
            except Exception:
                continue
            for pg in pages.values():
                txt = clean_passage(pg.get("extract", ""))
                h = hashlib.sha1(txt.encode()).hexdigest()[:16]
                if h in seen or not quality_ok(txt):
                    continue
                seen.add(h)
                new.append({"text": f"{pg.get('title', '')}\n\n{txt}", "t": now(), "src": "wikipedia-id"})
        if new:
            self._append_web(new)
            json.dump(sorted(seen)[-20000:], open(self.p["seen"], "w"))
        return len(new)

    def _append_web(self, new):
        dev_path = self.p["dev_web"]
        dev = self._read(dev_path)
        train = self._read(self.p["web"])
        for i, x in enumerate(new):
            (dev if (len(dev) < 60 and (len(train) + i) % 8 == 7) else train).append(x)
        for path, rows in ((self.p["web"], train[-3000:]), (dev_path, dev[:120])):
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for x in rows:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
            os.replace(tmp, path)

    # ---------------- evaluasi ----------------
    def _examples(self, recs, tok, block):
        out = []
        for r in recs:
            try:
                ex = build_example(record_to_segments(r), tok, block)
            except Exception:
                ex = None
            if ex:
                out.append(ex)
        return out

    def eval_loss(self, model, tok, recs, block, n=48):
        ex = self._examples(recs[:n], tok, block)
        if not ex:
            return None
        b = SFTBatcher(ex, None, 8, np.random.default_rng(0))
        tot, cnt = 0.0, 0
        model.eval()
        for i in range(0, len(ex), 8):
            chunk = ex[i:i + 8]
            sb = SFTBatcher(chunk, None, len(chunk), np.random.default_rng(i))
            sb.examples = chunk
            X, Y = sb.get()
            loss = float(model(X, Y)[1])
            if math.isfinite(loss):
                tot += loss; cnt += 1
        return tot / cnt if cnt else None

    # ---------------- satu siklus ----------------
    def run_cycle(self, force=False):
        if self.state["running"]:
            return {"ok": False, "alasan": "masih berjalan"}
        self.state["running"] = True
        self._save_state()
        t0 = time.time()
        try:
            return self._cycle(force)
        except Exception as e:                      # satu siklus gagal tidak boleh menjatuhkan aplikasi
            self._event("galat", jenis=type(e).__name__, pesan=str(e)[:160])
            return {"ok": False, "alasan": f"{type(e).__name__}: {e}"}
        finally:
            self.state["running"] = False
            self._save_state()

    def _cycle(self, force):
        ck = load_checkpoint(self.eng.ckpt)
        mc = ModelConfig(**ck["model_config"]).validate()
        tok = tokenizer_from_checkpoint(ck)
        cfg0 = {"step": int(ck["step"])}
        # 1) bahan belajar
        topics = [q for q in getattr(self.eng, "recent_queries", [])][-3:]
        added = self.fetch_web(topics) if self.online() else 0
        lessons = self._read(self.p["lessons"], 200)
        web = self._read(self.p["web"], 1500)
        dev_web = self._read(self.p["dev_web"])
        new_web = web[-max(30, added * 2):] if added else web[-20:]
        if not lessons and not web:
            self._event("tidak_ada_bahan", info="belum ada teks; hanya mengulang korpus dasar")
        # 2) kosakata tumbuh
        counts = tok.count_words([x["text"] for x in lessons + new_web])
        tok2 = type(tok).from_dict(tok.to_dict())
        cap = 12000
        newwords = tok2.add_counts(counts, min_freq=3, max_new=300, cap=cap)
        model = WeetsModel(mc)
        model.load_state_dict(ck["model"])
        old_names = ck.get("opt_names") or list(names_for_config(mc))
        opt, opt_names = self._new_opt(model, ck["optimizer"], old_names)
        base_dev = self._read(self.p["dev_base"])
        before = {"base": self.eval_loss(model, tok, base_dev, mc.block_size),
                  "web": self.eval_loss(model, tok, dev_web, mc.block_size)}
        parent_params = int(sum(v.size for v in model.params.values()))
        what = []
        if newwords:
            old_sd, old_nm = opt.state_dict(), opt_names
            model, mc = migrate_vocab(model.state_dict(), mc, tok2)
            tok = tok2
            opt, opt_names = self._new_opt(model, old_sd, old_nm)
            what.append(f"+{len(newwords)} kata")
            before["web"] = self.eval_loss(model, tok, dev_web, mc.block_size)
            before["base"] = self.eval_loss(model, tok, base_dev, mc.block_size)
        # 3) tumbuh kapasitas (hanya bila macet)
        grown = None
        if (self.state["plateau"] >= 3 and self.state["grow_cooldown"] <= 0 and parent_params < self.max_params) or force == "grow":
            kind = self.state["next_grow"]
            if kind == "layer" and mc.n_layer >= self.max_layers:
                kind = "mlp"
            sd = model.state_dict()
            old_sd2, old_nm2 = opt.state_dict(), opt_names
            try:
                if kind == "mlp":
                    newh = int(math.ceil(mc.hidden_dim() * 1.25 / 64) * 64)
                    model, mc = grow_mlp(sd, mc, newh); what.append(f"mlp->{newh}")
                else:
                    model, mc = grow_layers(sd, mc, 1); what.append(f"lapisan->{mc.n_layer}")
                grown = kind
                if int(sum(v.size for v in model.params.values())) > self.max_params * 1.1:
                    raise ValueError("melebihi batas parameter")
                opt, opt_names = self._new_opt(model, old_sd2, old_nm2)
            except Exception as e:
                self._event("tumbuh_batal", alasan=str(e)[:100]); grown = None
        # 4) latih dengan waktu terbatas
        recs = []
        for l in lessons:
            recs += [{"text": l["text"]}] * 3
        recs += [{"text": x["text"]} for x in new_web]
        recs += [{"text": x["text"]} for x in random.sample(web, min(len(web), 60))]
        recs += corpus.dialogs(random.Random(now()), 0.04)
        ex = self._examples(recs, tok, mc.block_size)
        if len(ex) < 4:
            return {"ok": False, "alasan": "bahan terlalu sedikit"}
        batcher = SFTBatcher(ex, None, 8, np.random.default_rng(now() % 99991))
        model.train()
        grads = model.zero_grads()
        steps, budget = 0, float(self.state["budget_seconds"])
        t_end = time.time() + budget
        peak = 2e-4 if getattr(opt, "state", None) else 1e-4         # tanpa momen Adam lama: mulai lebih hati-hati
        while time.time() < t_end and not self._stop.is_set():
            for g in opt.param_groups:
                g["lr"] = peak * min(1.0, (steps + 1) / 12.0)          # pemanasan: langkah awal Adam sangat berisik
            for g in grads.values():
                g.fill(0.0)
            X, Y = batcher.get()
            loss, _ = model.forward_backward(X, Y, scale=1.0, grads=grads)
            if not math.isfinite(loss):
                self._event("loss_tak_hingga", langkah=steps); return {"ok": False, "alasan": "loss tidak hingga"}
            clip_grad_norm(grads, 1.0)
            opt.step(grads)
            steps += 1
        model.eval()
        after = {"base": self.eval_loss(model, tok, base_dev, mc.block_size), "web": self.eval_loss(model, tok, dev_web, mc.block_size)}
        # 5) gerbang
        ok_base = after["base"] is None or before["base"] is None or after["base"] <= before["base"] * (1.03 if grown else 1.05) + 0.01
        ok_web = after["web"] is None or before["web"] is None or after["web"] <= before["web"] * 1.002 or bool(lessons and not added)
        accepted = bool(ok_base and ok_web and steps > 0)
        rel = None
        if before["web"] and after["web"]:
            rel = (before["web"] - after["web"]) / before["web"]
        rep = {"langkah": steps, "sebelum": {k: (round(v, 4) if v else v) for k, v in before.items()}, "sesudah": {k: (round(v, 4) if v else v) for k, v in after.items()},
               "perubahan": what, "diterima": accepted}
        self.state["cycles"] += 1
        if grown:
            self.state["grow_cooldown"] = 4 if accepted else 8
        else:
            self.state["grow_cooldown"] = max(0, self.state["grow_cooldown"] - 1)
        if accepted:
            self.state["accepted"] += 1
            if rel is not None and rel < 0.01:
                self.state["plateau"] += 1
            else:
                self.state["plateau"] = 0
            if grown:
                self.state["plateau"] = 0
                self.state["next_grow"] = "layer" if grown == "mlp" else "mlp"
            self._backup()
            new_step = cfg0["step"] + steps
            save_checkpoint(self.eng.ckpt, model, opt, None, new_step, float(after["base"] or 0.0), mc, TrainConfig(), tok, opt_names)
            self._bump_version(grown, bool(newwords))
            self.eng.load()
            self._event("diterima", **rep)
        else:
            self.state["rejected"] += 1
            self._event("dibuang", **rep)
        self._save_state()
        return {"ok": True, **rep}

    @staticmethod
    def _new_opt(model, old_sd=None, old_names=None):
        groups, names = param_groups(model, 0.05)
        opt = AdamW(model.params, groups, lr=3e-4, betas=(0.9, 0.95))
        if old_sd and old_sd.get("state"):
            shapes = {n: tuple(p.shape) for n, p in model.named_parameters()}
            res = carry_state(old_sd, old_names, names, shapes)
            sd = opt.state_dict()
            sd["state"] = res["state"]
            fg = [{k: v for k, v in g.items() if k not in ("params", "names")} for g in opt.param_groups]
            opt.load_state_dict(sd)
            restore_hparams(opt, fg)
        return opt, names

    def _backup(self):
        try:
            dst = os.path.join(self.backup_dir, f"ckpt-{now()}.npz")
            shutil.copy2(self.eng.ckpt, dst)
            old = sorted(os.listdir(self.backup_dir))[:-3]
            for f in old:
                os.unlink(os.path.join(self.backup_dir, f))
        except OSError:
            pass

    def _bump_version(self, grown, vocab_grew):
        a, b, c = (int(x) for x in self.state["version"].split("."))
        if grown:
            a, b, c = a + 1, 0, 0
        elif vocab_grew:
            b, c = b + 1, 0
        else:
            c += 1
        self.state["version"] = f"{a}.{b}.{c}"

    def rollback(self):
        files = sorted(os.listdir(self.backup_dir))
        if not files:
            return False
        shutil.copy2(os.path.join(self.backup_dir, files[-1]), self.eng.ckpt)
        os.unlink(os.path.join(self.backup_dir, files[-1]))
        self.eng.load()
        self._event("kembali", ke=files[-1])
        return True

    # ---------------- pengendali latar belakang ----------------
    def start(self):
        if self._thread and self._thread.is_alive():
            if not self._stop.is_set():
                return
            self._thread.join(timeout=3)                  # sedang berhenti: tunggu, lalu mulai ulang
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="weets-learner", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set(); self._force.set()

    def request_now(self, grow=False):
        self._force_kind = "grow" if grow else True
        try:
            with open(os.path.join(self.dir, "learn_now.flag"), "w") as fh:
                json.dump({"grow": bool(grow)}, fh)
        except OSError:
            pass
        self._force.set()

    _force_kind = False

    def _loop(self):
        while not self._stop.is_set():
            forced = self._force.wait(timeout=6)
            self._force.clear()
            if self._stop.is_set():
                break
            kind = self._force_kind if forced else False
            self._force_kind = False
            flag = os.path.join(self.dir, "learn_now.flag")
            if os.path.exists(flag):                       # permintaan dari proses UI
                try:
                    kind = "grow" if json.load(open(flag)).get("grow") else True
                    os.unlink(flag)
                except Exception:
                    kind = True
            if not kind:
                self.refresh()
                st = self.state
                if not st["enabled"] or time.time() - self.eng.activity < st["idle_seconds"]:
                    continue
                if not self.battery_ok(st["only_charging"]):
                    continue
            try:
                self.run_cycle(kind)
            except Exception as e:
                self.log("[belajar] galat", e)
            if not kind:
                self._stop.wait(timeout=30)

    def status(self):
        self.refresh()
        s = {k: v for k, v in self.state.items() if k != "history"}
        s.update(lessons=len(self._read(self.p["lessons"])), web=len(self._read(self.p["web"])),
                 riwayat=self.state["history"][-8:], max_params=self.max_params)
        return s
