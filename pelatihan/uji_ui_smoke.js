// Uji asap tanpa peramban: eksekusi skrip UI dengan DOM tiruan (Proxy) + fetch tiruan, tangkap ReferenceError/TypeError.
const fs = require("fs");
const html = fs.readFileSync("/home/claude/app/weets_app/index.html", "utf8");
const js = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
const logs = [];
function mk(name) {
  const store = { classList: { add() { }, remove() { }, toggle() { }, contains() { return false; } }, style: {}, dataset: {}, value: "", scrollHeight: 100, scrollTop: 0, clientHeight: 50, files: [], textContent: "", innerHTML: "", parentElement: null, children: [] };
  return new Proxy(function () { }, {
    get(t, k) { if (k in store) return store[k]; if (k === Symbol.toPrimitive) return () => ""; if (k === "closest") return () => null; if (k === "querySelector") return () => mk(name + ">q"); if (k === "querySelectorAll") return () => []; if (k === "getAttribute") return () => null; return typeof k === "string" ? (...a) => { if (k === "getReader") return undefined; return mk(name + "." + k); } : undefined; },
    set(t, k, v) { store[k] = v; return true; }, apply() { return mk(name + "()"); }
  });
}
const doc = mk("document"); doc.documentElement = mk("html");
doc.addEventListener = (e, f) => { (global.__listeners = global.__listeners || []).push([e, f]); };
doc.querySelector = () => mk("q"); doc.querySelectorAll = () => []; doc.createElement = () => mk("el"); doc.head = mk("head"); doc.body = mk("body"); doc.activeElement = null;
const ls = {}; global.localStorage = { getItem: k => ls[k] ?? null, setItem: (k, v) => { ls[k] = v; } };
global.document = doc; global.window = global; global.history = { pushState() { }, replaceState() { }, back() { } };
global.matchMedia = () => ({ matches: false }); global.addEventListener = () => { }; global.navigator = { clipboard: { writeText: async () => { } } };
global.requestAnimationFrame = f => { f(); return 1; }; global.confirm = () => true; global.alert = () => { };
global.speechSynthesis = { cancel() { }, speak() { }, getVoices() { return []; } }; global.SpeechSynthesisUtterance = function () { };
global.URL = URL; global.TextDecoder = TextDecoder; global.AbortController = AbortController;
const ev = [{ t: "stage", stage: "cari", pool: [["Mencari", 11], ["Menjelajah", 12]] }, { t: "think", text: "x" }, { t: "delta", text: "Halo [1] dunia **tebal** https://a.id/x" }, { t: "sources", items: [{ title: "T", url: "https://a.id", host: "a.id", snippet: "s" }] }, { t: "done", ms: 5 }];
global.fetch = async (u, o) => {
  if (u === "/api/chat") { const body = ev.map(e => JSON.stringify(e)).join("\n") + "\n"; let done = false; return { ok: true, body: { getReader: () => ({ read: async () => done ? { done: true } : (done = true, { done: false, value: new TextEncoder().encode(body) }) }) } }; }
  const J = { "/api/status": { versi_app: "2", model: { ready: true, params: 1, vocab: 2, layers: 3, width: 4, mlp: 5, step: 6 }, belajar: {} }, "/api/learn/status": { version: "0.0.1", cycles: 1, accepted: 1, rejected: 0, running: false, enabled: true, only_charging: false, idle_seconds: 45, budget_seconds: 90, last: "x", lessons: 0, web: 0, riwayat: [{ t: 1, kind: "diterima", langkah: 3, sebelum: { base: 1, web: 2 }, sesudah: { base: .9, web: 1.9 }, perubahan: ["+3 kata"] }] }, "/api/diag": { jaringan: [{ situs: "x", ok: true, ms: 3 }], baterai: { level: 5 } }, "/api/page": { title: "T", url: "https://a.id", text: "## H\n\npara", links: [{ text: "l", url: "https://a.id/l" }] }, "/api/notes": [] }[u.split("?")[0]] || {};
  return { ok: true, status: 200, json: async () => J, blob: async () => ({}) };
};
global.setTimeout = (f, t) => { if (t < 5000) try { f(); } catch (e) { logs.push("timeout-callback: " + e.stack); } return 1; };
global.setInterval = () => 1; global.clearInterval = () => { }; global.clearTimeout = () => { };
process.on("unhandledRejection", e => logs.push("unhandledRejection: " + (e && e.stack || e)));
(async () => {
  try {
    (0, eval)(js + `\n;globalThis.__T={md,glyph,GEN,go,send,openReader,renderLearn,renderModel,renderSettings,renderChat,get cur(){return cur}};`);
  } catch (e) { logs.push("EVAL: " + e.stack); }
  const T = global.__T;
  if (T) {
    try {
      for (let i = 0; i < 50; i++) { const g = T.glyph(i); if (!/^<svg[\s\S]*<\/svg>$/.test(g) || g.length < 120) logs.push("glyph " + i + " aneh"); }
      const set = new Set(); for (let i = 0; i < 50; i++) set.add(T.glyph(i).replace(/g\d+/g, "G")); if (set.size !== 50) logs.push("animasi tidak unik: " + set.size);
      const m = T.md("Halo **a** `b` [1]\n\n- satu\n- dua\n\n```python\nprint(1)\n```\n<script>alert(1)</script> https://x.id/a?b=1", [{ url: "https://s.id" }]);
      if (/<script/i.test(m)) logs.push("XSS di md"); if (!m.includes('class="cite"') || !m.includes("<ul>") || !m.includes("<pre>")) logs.push("md kurang: " + m);
      await T.send("Halo"); await new Promise(r => setImmediate(r));
      const last = T.cur.msgs[T.cur.msgs.length - 1]; if (!last.content.includes("Halo [1]") || !last.sources.length) logs.push("stream gagal " + JSON.stringify(last));
      T.openReader("https://a.id"); await T.renderLearn(); await T.renderModel(); await T.renderSettings();
    } catch (e) { logs.push("FLOW: " + e.stack); }
  }
  console.log(logs.length ? "MASALAH:\n" + logs.join("\n") : "SMOKE_OK (50 animasi unik, markdown aman, stream, halaman)");
  process.exit(logs.length ? 1 : 0);
})();
