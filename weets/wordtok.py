"""Tokenizer PER KATA (word-level) untuk Weets.

Tata letak id (kompatibel dengan tokenizer lama, jadi PAD/BOS/EOS & checkpoint tetap jalan):
  0-255   byte mentah  -> cadangan untuk kata/aksara yang belum ada di kosakata (tidak pernah <unk>)
  256-259 PAD BOS EOS UNK
  260+    token kosakata (append-only: id lama tidak pernah berubah makna)

Satu kata = satu token. Aturan spasi dibuat hemat dan TANPA kehilangan info:
  * kata biasanya didahului spasi, kecuali di awal teks / setelah baris baru / setelah tag -> default tanpa spasi
  * kalau kenyataannya menyimpang dari default, ditulis penanda <ns> (flip)
  * huruf kapital: <C> (Kapital awal) atau <U> (SEMUA KAPITAL) + kata huruf kecil
  * tanda baca dan angka punya dua bentuk eksplisit (dengan/ tanpa spasi), angka dipecah per digit
Spasi ganda / tab dinormalkan menjadi satu spasi.
"""
import re, unicodedata
from collections import Counter
from .tokenizer import ByteTokenizer, BASE_VOCAB, PAD, BOS, EOS, UNK

CAP_T, UPP_T, NS_T, NL_T, URL_T = "<C>", "<U>", "<ns>", "\n", "<url>"
TAGS = ["<think>", "</think>", "<cari>", "</cari>", "<buka>", "</buka>", "<hitung>", "</hitung>",
        "<hasil>", "</hasil>", "<ingat>", "</ingat>", "<cek>", "</cek>",
        "<gaya_normal>", "<gaya_jujur>", "<gaya_toxic>", "<gaya_puitis>"]
CONTROL = [CAP_T, UPP_T, NS_T, NL_T, URL_T] + TAGS
PUNCT = list(".,;:!?()[]{}\"'-—–…/%+*=<>@#&_\\|~^$`")
DIGITS = list("0123456789")
SP = "\u2581"  # penanda "didahului spasi" pada token tanda baca / angka
_TAG_RE = "|".join(re.escape(t) for t in sorted(TAGS, key=len, reverse=True))
_UNIT = re.compile(
    r"(?P<tag>%s)|(?P<url>https?://[^\s<>\"')\]]+)|(?P<word>[^\W\d_]+(?:['\-][^\W\d_]+)*)|(?P<dig>\d)|(?P<nl>\n)|"
    r"(?P<ws>[ \t\u00a0]+)|(?P<p>.)" % _TAG_RE, re.S)


def _norm(t):
    t = unicodedata.normalize("NFC", t).replace("\r", "")
    return (t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
             .replace("\u2026", "…"))


def units(text):
    """Teks -> daftar (jenis, isi, ada_spasi_sebelum)."""
    out, sp = [], False
    for m in _UNIT.finditer(_norm(text)):
        k = m.lastgroup
        s = m.group(k)
        if k == "ws":
            sp = True; continue
        out.append((k, s, sp))
        sp = False
    return out


class WordTokenizer(ByteTokenizer):
    kind = "word"

    def __init__(self, words=None):
        self.itos = []          # id-260 -> string
        self.stoi = {}
        for t in CONTROL:
            self._add(t)
        for p in PUNCT + DIGITS:
            self._add(p); self._add(SP + p)
        for w in (words or []):
            self._add(w)

    def _add(self, t):
        if t in self.stoi:
            return False
        self.stoi[t] = BASE_VOCAB + len(self.itos)
        self.itos.append(t)
        return True

    @property
    def vocab_size(self):
        return BASE_VOCAB + len(self.itos)

    @property
    def n_words(self):
        return self.vocab_size - BASE_VOCAB - len(CONTROL) - 2 * (len(PUNCT) + len(DIGITS))

    # ---------------- encode ----------------
    def _default_space(self, prev_kind):
        return prev_kind not in ("start", "nl", "tag")

    def encode(self, text, add_bos=False, add_eos=False):
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        out = [BOS] if add_bos else []
        prev = "start"
        q = {'"': False, "'": False}
        for k, s, sp in units(text):
            if k == "tag":
                out.append(self.stoi[s]); prev = "tag"
            elif k == "nl":
                out.append(self.stoi[NL_T]); prev = "nl"
            elif k == "url":
                out.append(self.stoi[URL_T]); prev = "word"
            elif k in ("dig", "p"):
                key = (SP if sp and prev not in ("start", "nl") else "") + s
                i = self.stoi.get(key)
                if i is None:
                    out.extend((" " if sp and prev not in ("start", "nl") else "").encode() + s.encode("utf-8"))
                else:
                    out.append(i)
                prev = "p" if k == "p" else "dig"
                if k == "p" and s in "([{":
                    prev = "open"
                elif k == "p" and s in q:
                    q[s] = not q[s]
                    if q[s]:
                        prev = "open"
            else:  # word
                lw = s.lower()
                spaced = sp and prev not in ("start", "nl")
                i = self.stoi.get(lw)
                if i is None:
                    out.extend(((" " if spaced else "") + s).encode("utf-8"))   # kata asing: byte mentah, huruf asli
                    prev = "word"; continue
                if spaced != self._default_space(prev):
                    out.append(self.stoi[NS_T])
                if s != lw:
                    if s.isupper() and len(s) > 1:
                        out.append(self.stoi[UPP_T])
                    elif s == s.capitalize():
                        out.append(self.stoi[CAP_T])
                    else:      # huruf campur (iPhone): pakai byte agar tepat
                        if spaced: pass
                        out.extend(((" " if spaced else "") + s).encode("utf-8")); prev = "word"; continue
                out.append(i); prev = "word"
        if add_eos:
            out.append(EOS)
        return out

    # ---------------- decode ----------------
    def decode(self, ids, skip_special=True):
        out, buf = [], bytearray()
        prev, cap, upp, ns = "start", False, False, False
        q = {'"': False, "'": False}

        def punct_state(ch):
            if ch in "([{":
                return "open"
            if ch in q:
                q[ch] = not q[ch]
                return "open" if q[ch] else "p"
            return "dig" if ch.isdigit() else "p"

        def flush():
            if buf:
                out.append(bytes(buf).decode("utf-8", errors="replace")); buf.clear()
        for i in ids:
            i = int(i)
            if 0 <= i < 256:
                buf.append(i); prev = "word" if prev in ("start", "nl", "tag") or True else prev
                continue
            flush()
            if i in (PAD, BOS, EOS, UNK):
                continue
            j = i - BASE_VOCAB
            if j < 0 or j >= len(self.itos):
                continue
            t = self.itos[j]
            if t == CAP_T: cap = True; continue
            if t == UPP_T: upp = True; continue
            if t == NS_T: ns = True; continue
            if t == NL_T:
                out.append("\n"); prev = "nl"; ns = cap = upp = False; continue
            if t == URL_T:
                out.append((" " if self._default_space(prev) else "") + "<url>"); prev = "word"; continue
            if t in TAGS:
                if not skip_special:
                    out.append(t)
                prev = "tag"; continue
            if t[0] == SP:
                out.append(" " + t[1:] if prev not in ("start", "nl") else t[1:])
                prev = punct_state(t[1:]); continue
            if t.isdigit() or (len(t) == 1 and t in PUNCT):
                out.append(t); prev = punct_state(t); continue
            sp = self._default_space(prev)
            if ns: sp = not sp
            if prev == "open" and not ns: sp = False
            w = t.upper() if upp else (t[:1].upper() + t[1:] if cap else t)
            out.append((" " if sp else "") + w)
            prev, cap, upp, ns = "word", False, False, False
        flush()
        s = "".join(out)
        return s

    # ---------------- pertumbuhan ----------------
    def count_words(self, texts):
        c = Counter()
        for tx in texts:
            for k, s, _ in units(tx):
                if k == "word":
                    c[s.lower()] += 1
        return c

    def learn_words(self, texts, max_vocab, min_freq=2):
        """Isi kosakata dari teks (append-only). Mengembalikan jumlah kata baru."""
        return len(self.add_counts(self.count_words(texts), min_freq, max(0, max_vocab - self.vocab_size)))

    def add_counts(self, counts, min_freq=3, max_new=400, cap=0):
        room = max_new if not cap else max(0, min(max_new, cap - self.vocab_size))
        new = []
        for w, n in counts.most_common():
            if len(new) >= room or n < min_freq:
                break
            if w not in self.stoi and 1 < len(w) <= 24:
                new.append(w)
        for w in new:
            self._add(w)
        return new

    def piece_ids(self, i):
        """Id byte penyusun sebuah token (dipakai untuk inisialisasi baris embedding baru)."""
        t = self.itos[i - BASE_VOCAB].lstrip(SP)
        return list(t.encode("utf-8"))

    def to_dict(self):
        return {"type": "word", "version": 1, "vocab_size": self.vocab_size,
                "special_tokens": {"pad": PAD, "bos": BOS, "eos": EOS, "unk": UNK}, "words": list(self.itos)}

    @classmethod
    def from_dict(cls, d):
        tok = cls.__new__(cls)
        tok.itos, tok.stoi = [], {}
        for t in d["words"]:
            tok._add(t)
        if d.get("vocab_size", tok.vocab_size) != tok.vocab_size:
            raise ValueError("tokenizer vocab_size does not match its word list (corrupt file?)")
        return tok
