#!/bin/sh
# Mengulang pembuatan model starter (CPU saja, NumPy). Jalankan dari folder app/.
set -e
python3 - <<'PY'
import json, sys
sys.path.insert(0, ".")
from weets.corpus import build
from weets.wordtok import WordTokenizer
recs = build.build(2024, 1.0)                       # korpus Indonesia sintetis: prosa, filsafat, puisi, jujur/toxic, alat
build.write_jsonl("korpus.jsonl", recs)
tok = WordTokenizer(); tok.learn_words([build.record_text(x) for x in recs], 5000, min_freq=2)
tok.save("tok.json")
PY
# Tahap 1: dari nol (sekitar 2.200 langkah, loss val ~0,24); tahap 2-3: lanjutkan dengan --resume + korpus seed lain
python3 -m weets.train --mode sft --data korpus.jsonl --tokenizer tok.json --out-dir run \
  --steps 2200 --batch-size 16 --block-size 256 --layers 5 --heads 4 --kv-heads 2 --width 128 \
  --warmup-steps 200 --lr 2e-3 --min-lr 1e-4 --eval-interval 500 --save-interval 100
# Ekspor ke .wt:  python3 -c "import wt;open('model/weets-starter.wt','wb').write(wt.export_checkpoint('run/best.npz',False))"
