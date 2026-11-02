"""Format .wt Weets: kepala JSON + payload .npz (checkpoint tanpa pickle).
  8 byte  : b"WEETSWT\\x02"
  4 byte  : panjang kepala (big-endian)
  kepala  : JSON {format, version, name, step, params, vocab, layers, heads, width, block, optimizer, sha256, sig, created}
  payload : .npz (np.load(allow_pickle=False))
`sig` = HMAC-SHA256 atas sha256 payload; hanya menjaga dari file rusak/salah jenis, BUKAN rahasia (kunci ada di kode)."""
import hashlib, hmac, io, json, os, struct, time
import numpy as np

MAGIC = b"WEETSWT\x02"
_KEY = b"weets-wt/2"


class WtError(ValueError):
    pass


def _sig(sha_hex):
    return hmac.new(_KEY, sha_hex.encode(), hashlib.sha256).hexdigest()


def pack(npz_bytes, meta, name="weets"):
    sha = hashlib.sha256(npz_bytes).hexdigest()
    head = {"format": "weets-wt", "version": 2, "name": name, "created": int(time.time()), "sha256": sha, "sig": _sig(sha), **meta}
    hb = json.dumps(head, ensure_ascii=False).encode("utf-8")
    return MAGIC + struct.pack(">I", len(hb)) + hb + npz_bytes


def unpack(blob):
    if len(blob) < 16 or blob[:7] != MAGIC[:7]:
        raise WtError("bukan berkas .wt Weets")
    if blob[7:8] != MAGIC[7:8]:
        raise WtError(f"versi .wt {blob[7]} tidak didukung (butuh {MAGIC[7]}); model lama dengan tokenizer per huruf tidak bisa dipakai")
    n = struct.unpack(">I", blob[8:12])[0]
    if n > 1_000_000 or 12 + n > len(blob):
        raise WtError("kepala .wt rusak")
    try:
        head = json.loads(blob[12:12 + n].decode("utf-8"))
    except Exception as e:
        raise WtError("kepala .wt tidak terbaca") from e
    pay = blob[12 + n:]
    sha = hashlib.sha256(pay).hexdigest()
    if sha != head.get("sha256") or not hmac.compare_digest(str(head.get("sig", "")), _sig(sha)):
        raise WtError("checksum/tanda tangan .wt tidak cocok (berkas rusak atau bukan dari Weets)")
    return head, pay


def export_checkpoint(npz_path, with_optimizer=True, name="weets"):
    """Baca checkpoint .npz -> bytes .wt. with_optimizer=False membuang momen Adam (berkas ~3x lebih kecil)."""
    from weets.checkpoint import load_checkpoint
    ck = load_checkpoint(npz_path)
    mc = ck["model_config"]
    meta = {"step": ck["step"], "vocab": mc["vocab_size"], "layers": mc["n_layer"], "heads": mc["n_head"], "width": mc["n_embd"],
            "block": mc["block_size"], "optimizer": bool(with_optimizer and ck["optimizer"]["state"]),
            "params": int(sum(v.size for v in ck["model"].values()))}
    with open(npz_path, "rb") as f:
        raw = f.read()
    if not with_optimizer:
        z = np.load(io.BytesIO(raw), allow_pickle=False)
        arrays = {k: z[k] for k in z.files if not k.startswith("opt/")}
        m = json.loads(bytes(arrays["meta"]).decode("utf-8"))
        m.update(opt_steps={}, opt_groups=[], opt_names=None)
        arrays["meta"] = np.frombuffer(json.dumps(m).encode("utf-8"), dtype=np.uint8)
        bio = io.BytesIO(); np.savez(bio, **arrays); raw = bio.getvalue()
    return pack(raw, meta, name)


def import_blob(blob, dest_npz):
    """Verifikasi, lalu tulis ke dest_npz secara atomik. Mengembalikan kepala .wt."""
    head, pay = unpack(blob)
    tmp = dest_npz + ".incoming"
    with open(tmp, "wb") as f:
        f.write(pay)
    try:
        from weets.checkpoint import load_checkpoint, tokenizer_from_checkpoint
        ck = load_checkpoint(tmp)
        tok = tokenizer_from_checkpoint(ck)
        if getattr(tok, "kind", "") != "word":
            raise WtError("model ini memakai tokenizer per huruf; Weets sekarang hanya menerima tokenizer per kata")
        if tok.vocab_size != ck["model_config"]["vocab_size"]:
            raise WtError("ukuran kosakata tidak cocok dengan model")
    except Exception:
        os.unlink(tmp)
        raise
    os.replace(tmp, dest_npz)
    return head
