"""Penumbuhan model di aplikasi (memakai mesin `weets.growth` / `weets.autotokenizer`).

1) Kosakata: token BARU ditambahkan (BPE) hanya bila terbukti memperpendek teks pada data uji tersimpan (tokens/byte turun).
   Token lama tidak berubah; baris embedding token baru dimulai dari rata-rata bagian pembentuknya.
2) Kapasitas: tambah lapis / lebarkan MLP dengan fungsi awal yang sama, lalu eksperimen kontrol: model induk dilatih sama
   lama (kontrol) vs model tumbuh (kandidat). Hanya dipakai bila kandidat lebih baik dari kontrol; jika tidak ditolak."""
import json, os, shutil, time


def grow_vocab(cur_path, texts, out_path, max_vocab=2048):
    from weets.autotokenizer import grow_tokenizer, TokenizerPolicy
    from weets.checkpoint import load_checkpoint, tokenizer_from_checkpoint
    from weets.config import ModelConfig
    from weets.growth import migrate_vocab, fresh_checkpoint
    ck = load_checkpoint(cur_path)
    mc = ModelConfig(**ck["model_config"])
    tok = tokenizer_from_checkpoint(ck)
    new, rep = grow_tokenizer(tok, texts, TokenizerPolicy(round_size=48, min_gain=0.004, min_freq=3, max_rounds=6,
                                                           sample_chars=40000 if os.environ.get("ANDROID_ARGUMENT") else 120000,
                                                           time_budget_s=8 if os.environ.get("ANDROID_ARGUMENT") else 20, max_vocab=max_vocab))
    if rep["added"] <= 0:
        return None, rep
    model, nmc = migrate_vocab(ck["model"], mc, new)
    fresh_checkpoint(out_path, model, nmc, new, carry_from=ck)
    return out_path, rep


def capacity_experiment(cur_path, corpus_path, workdir, kind, steps=120, max_params=6_000_000, min_improvement=0.01):
    from weets.growth import run_experiment
    args = ["--batch-size", "4", "--grad-accum", "1", "--lr", "6e-4", "--min-lr", "6e-5", "--warmup-steps", "10",
            "--eval-interval", str(max(20, steps // 3)), "--eval-batches", "3", "--save-interval", str(steps), "--mode", "pretrain"]
    return run_experiment(cur_path, corpus_path, workdir, kind, amount=0, steps=steps, train_args=args,
                          min_improvement=min_improvement, max_params=max_params, device="cpu")


def corpus_text(rows):
    return "".join("User: %s\nAssistant: %s\n\n" % (r["prompt"], r["response"]) for r in rows)
