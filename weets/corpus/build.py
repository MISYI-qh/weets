"""Rakit korpus latih Weets (JSONL: {"text"} dan {"messages"}). Deterministik per seed."""
import json, random
from . import prose, philo, poetry, candor, chat

STYLES = ["normal", "jujur", "toxic", "puitis"]


def _m(style, turns):
    msgs = [{"role": "system", "content": f"<gaya_{style}>"}]
    for u, a in turns:
        msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    return {"messages": msgs}


def _style3(r):
    x = r.random()
    return "normal" if x < 0.7 else ("jujur" if x < 0.85 else "toxic")


def dialogs(r, scale=1.0):
    out = []
    n = lambda k: max(1, int(k * scale))
    # filsafat
    for _ in range(n(900)):
        p, t = r.choice(philo.NAMA), r.choice(philo.TOPIK)
        q = philo.fill(r.choice(philo.PROMPT_SATU), t).replace("{p}", p) if False else r.choice(philo.PROMPT_SATU).replace("{p}", p).replace("{t}", t)
        s = _style3(r)
        out.append(_m(s, [(q, candor.wrap_style(r, s, philo.answer_satu(r, p, t)))]))
    for _ in range(n(600)):
        p1, p2 = r.sample(philo.NAMA, 2); t = r.choice(philo.TOPIK)
        q = r.choice(philo.PROMPT_BANDING).replace("{p1}", p1).replace("{p2}", p2).replace("{t}", t)
        s = _style3(r)
        out.append(_m(s, [(q, candor.wrap_style(r, s, philo.answer_banding(r, p1, p2, t)))]))
    for _ in range(n(1100)):
        t = r.choice(philo.TOPIK)
        q = philo.fill(r.choice(philo.PROMPT_SEMUA), t)
        s = _style3(r)
        out.append(_m(s, [(q, candor.wrap_style(r, s, philo.answer_semua(r, t, r.randint(3, 5))))]))
    for _ in range(n(1200)):
        t = r.choice(philo.TOPIK)
        q = r.choice(philo.PROMPT_PENDAPAT).replace("{t}", t)
        s = _style3(r)
        out.append(_m(s, [(q, candor.wrap_style(r, s, philo.answer_pendapat(r, t)))]))
    # puisi dll
    for _ in range(n(1200)):
        tema, title, body = poetry.puisi(r)
        q = r.choice(poetry.PROMPT_PUISI).replace("{t}", tema)
        out.append(_m("puitis", [(q, f"<think>tema: {tema}</think>{title}\n{body}")]))
    for _ in range(n(900)):
        out.append(_m("puitis", [(r.choice(poetry.PROMPT_PANTUN), r.choice(poetry.PANTUN))]))
    for _ in range(n(150)):
        out.append(_m("puitis", [(r.choice(poetry.PROMPT_BAIT), r.choice(poetry.BAIT))]))
    for _ in range(n(150)):
        out.append(_m("puitis", [(r.choice(poetry.PROMPT_HAIKU), r.choice(poetry.HAIKU))]))
    for _ in range(n(400)):
        a, b = r.choice(poetry.PLAIN2POETIC)
        out.append(_m("puitis", [(r.choice(poetry.PROMPT_UBAH).replace("{s}", a), b)]))
    for _ in range(n(8)):
        for q, a in poetry.PUITIS_QA:
            out.append(_m("puitis", [(q, a)]))
    # jujur / toxic / normal
    keys = list(candor.KASUS)
    for _ in range(n(3200)):
        k = r.choice(keys); s = r.choice(["normal", "jujur", "toxic", "toxic"])
        out.append(_m(s, [(r.choice(candor.KASUS[k]["prompts"]), candor.respon(r, k, s))]))
    for _ in range(n(300)):
        out.append(_m(r.choice(["normal", "jujur", "toxic", "puitis"]), [(r.choice(candor.KRISIS_PROMPT), r.choice(candor.KRISIS_JAWAB))]))
    # identitas & sapa
    for _ in range(n(900)):
        qs, as_ = r.choice(chat.IDENT)
        out.append(_m(r.choice(["normal", "normal", "jujur", "puitis"]), [(r.choice(qs), r.choice(as_))]))
    for _ in range(n(700)):
        qs, as_ = r.choice(chat.SAPA)
        out.append(_m("normal", [(r.choice(qs), r.choice(as_))]))
    # cara-cara
    for _ in range(n(300)):
        title, body = r.choice(prose.HOWTO)
        low = title[0].lower() + title[1:]
        q = r.choice([f"Bagaimana {low}?", f"Tolong jelaskan {low}.", f"{title} bagaimana?"])
        out.append(_m("normal", [(q, body)]))
    # alat
    for _ in range(n(700)):
        q, a = chat.hitung_contoh(r)
        out.append(_m("normal", [(q, a)]))
    for _ in range(n(900)):
        if r.random() < 0.2:
            x = r.choice(chat.TERKINI); q = r.choice(chat.TERKINI_FORM).format(x=x); query = x
        else:
            kind = r.choice(list(chat.SEARCH_TOPIK)); x = r.choice(chat.SEARCH_TOPIK[kind])
            q = r.choice(chat.SEARCH_FORM[kind]).format(x=x); query = x if kind in ("apa itu", "berapa", "bagaimana") else f"{kind} {x}"
        out.append(_m(_style3(r), [(q, f"<think>butuh data dari web</think><cari>{query}</cari><hasil>{r.randint(2, 5)} sumber</hasil>Ini yang kutemukan, sumbernya ada di bawah.")]))
    for _ in range(n(200)):
        q, note = r.choice(chat.INGAT)
        out.append(_m("normal", [(q, f"<ingat>{note}</ingat>Sudah kucatat.")]))
    # dua giliran: gabungkan dua contoh sederhana
    pool = [d for d in out if len(d["messages"]) == 3 and len(d["messages"][2]["content"]) < 400 and d["messages"][0]["content"] == "<gaya_normal>"]
    for _ in range(n(500)):
        a, b = r.sample(pool, 2)
        out.append({"messages": [a["messages"][0]] + a["messages"][1:] + b["messages"][1:]})
    r.shuffle(out)
    return out


def docs(r, scale=1.0):
    n = lambda k: max(1, int(k * scale))
    out = [{"text": prose.paragraph(r)} for _ in range(n(6000))]
    for _ in range(n(500)):
        tema, title, body = poetry.puisi(r)
        out.append({"text": f"{title}\n\n{body}"})
    for title, body in prose.HOWTO:
        out += [{"text": f"{title}\n\n{body}"}] * 3
    r.shuffle(out)
    return out


def build(seed=1337, scale=1.0):
    r = random.Random(seed)
    recs = dialogs(r, scale) + docs(r, scale)
    r.shuffle(recs)
    return recs


def write_jsonl(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for x in recs:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


def record_text(x):
    if "text" in x:
        return x["text"]
    return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in x["messages"])
