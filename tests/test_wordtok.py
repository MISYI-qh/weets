import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weets.wordtok import WordTokenizer
from weets.tokenizer import tokenizer_from_dict, BASE_VOCAB, EOS
from weets.corpus import build


class W(unittest.TestCase):
    def setUp(self):
        self.t = WordTokenizer(["aku", "weets", "hujan", "turun", "di", "sore", "hari", "dan", "anak-anak", "kata", "dunia", "halo"])

    def test_roundtrip(self):
        for s in ['Aku Weets, AI kecil.\nHalo (dunia) "kata" dan "dunia" lagi.', "Hujan turun di sore hari; Rp 1.250,50!",
                  "<think>tema: hujan</think>Di sore hari.", "anak-anak dan/atau 3,5% iPhone", "User: Halo\nAssistant: Aku Weets.\n"]:
            self.assertEqual(self.t.decode(self.t.encode(s), skip_special=False), s)

    def test_one_word_one_token(self):
        self.assertEqual(len(self.t.encode("hujan turun")), 2)
        self.assertEqual(len(self.t.encode("Hujan")), 2)             # <C> + kata

    def test_unknown_word_falls_back_to_bytes_not_unk(self):
        ids = self.t.encode("zebrafish"); self.assertTrue(all(i < 256 for i in ids))
        self.assertEqual(self.t.decode(ids), "zebrafish")

    def test_append_only_growth_keeps_old_ids(self):
        before = self.t.encode("hujan turun di sore")
        self.t.add_counts(self.t.count_words(["zebrafish zebrafish zebrafish"]), min_freq=3)
        self.assertEqual(self.t.encode("hujan turun di sore"), before)
        self.assertEqual(len(self.t.encode("zebrafish")), 1)

    def test_serialization(self):
        t2 = tokenizer_from_dict(self.t.to_dict()); self.assertEqual(t2.vocab_size, self.t.vocab_size)
        self.assertEqual(t2.encode("Aku Weets."), self.t.encode("Aku Weets."))

    def test_corpus_deterministic_and_covered(self):
        a, b = build.build(5, 0.3), build.build(5, 0.3); self.assertEqual(a, b)
        texts = [build.record_text(x) for x in a]
        tok = WordTokenizer(); tok.learn_words(texts, 4000, 2)
        ids = [i for t in texts for i in tok.encode(t)]
        self.assertLess(sum(i < 256 for i in ids) / len(ids), 0.03)  # nyaris semua kata satu token

    def test_corpus_safety_rules(self):
        recs = build.build(9, 0.1); import json
        blob = json.dumps(recs, ensure_ascii=False).lower()
        for bad in ("bunuh dirimu", "matilah", "mati saja kau", "cina", "yahudi", "kafir"):
            self.assertNotIn(bad, blob)
        for r in recs:       # contoh krisis tidak pernah dijawab dengan hinaan
            m = r.get("messages")
            if m and any(k in m[1]["content"].lower() for k in ("bunuh diri", "ingin mati", "nggak ada")):
                self.assertNotIn("goblok", m[2]["content"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
