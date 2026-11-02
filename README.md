# Weets 2.1

AI kecil berbahasa Indonesia yang berjalan penuh di ponsel (Python + NumPy murni, tanpa model orang lain), belajar dan tumbuh sendiri.

## Pakai
1. Ekstrak zip ini, salin **seluruh isinya** ke akar repo GitHub `weets` (ganti file lama), lalu `git add -A && git commit && git push`.
2. Workflow `.github/workflows/build-apk.yml` menjalankan uji lalu membangun APK (artifact `weets-apk`).
   - `buildozer.spec` dan workflow ini disusun dari metadata APK lamamu (id.misyi.weets, minSdk 24, arm64-v8a, bootstrap webview, port 5000, layanan `weets`). Karena aku tidak bisa membangunnya di sini, **jika build lamamu sudah jalan, pertahankan spec/workflow lamamu** dan hanya samakan: `source.include_exts` memuat `py,png,svg,html,json,wt`, `services = weets:service.py:foreground`, dan izin INTERNET, FOREGROUND_SERVICE, WAKE_LOCK, POST_NOTIFICATIONS, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS.
3. Di komputer: `python3 server.py` lalu buka http://127.0.0.1:8765 . Uji: `python3 tests/test_wordtok.py && python3 tests/test_app.py`.

## Isi
- `main.py`, `service.py`, `server.py`: titik masuk Android, layanan latar belakang, server lokal 127.0.0.1.
- `engine.py`: obrolan, gaya (normal / jujur / kasar / puitis), alat (cari web, buka tautan, hitung, catatan), sampling anti-slop.
- `learner.py`: belajar dan tumbuh sendiri (kosakata, MLP, lapisan); tiap perubahan diuji dan dibuang bila lebih buruk.
- `websearch.py`: pencarian tanpa kunci (DuckDuckGo lalu Wikipedia) + mode baca untuk peramban dalam aplikasi; sebab kegagalan dilaporkan jelas.
- `weets/`: inti model (NumPy), tokenizer per kata `wordtok.py`, generator korpus Indonesia `corpus/`.
- `model/weets-starter.wt`: model awal 1,32 juta parameter (6.399 langkah, loss uji ~0,10 pada data sintetis).
- `index.html`: antarmuka (splash "Weets", animasi logo, 50 status berpikir dengan 50 animasi).
- `pelatihan/`: cara mengulang pelatihan dan uji UI.

## Belajar di latar belakang
Ditanya sekali saat pertama dibuka. Saklarnya ada di Belajar dan Pengaturan; dimatikan kapan saja, layanan berhenti sendiri.

## Batas yang jujur
- Suara tiruan rekamanmu (99%) tidak ada. Weets memakai suara Indonesia bawaan ponsel; dikte lewat layar bicara Google.
- Model kecil: fasih pada gaya yang dilatih, fakta dunia harus dari web dan bisa salah. Jawaban "semua sudut pandang" kadang memakai kalimat yang kurang pas topik.
- Kode Android (notifikasi, baterai, dikte, layanan, unggah berkas di WebView) dan build spec belum diuji di perangkat. UI diuji dengan DOM tiruan.
- Gambar tidak dibaca (tanpa model penglihatan); PDF hasil pindai tidak dibaca (tanpa OCR).
- Mode Kasar mengumpat pada kebiasaan dan alasan, bukan identitas, dan berganti peduli saat ada tanda krisis.
