# WEETS (Misyi) — aplikasi + web

Jalankan: `python main.py` lalu buka http://localhost:8765 (web dan aplikasi memakai kode yang sama).
Android: `buildozer android debug` (server di port 5000, dibuka WebView).

## Alat bawaan (tanpa API/kunci)
- **Buat gambar** — pelukis ilustrasi lokal (matahari, laut, gunung, kota, hutan, rumah, kucing, roket, dll.) atau seni abstrak.
- **Buat berkas** — txt, md, csv, json, html, py, **pdf, docx** (ditulis lokal).
- **Cari web** & **browser dalam aplikasi** — ketuk tautan di chat untuk membuka pembaca halaman (ringkas, tautan, pelajari halaman).
- **Analisis** gambar (warna, orientasi, OCR bila ada tesseract) dan berkas (pdf/docx/xlsx/csv/json/teks: ringkasan, kata kunci).
- **Hitung**, **waktu**, **contoh kode** + tombol **Jalankan** (Python di perangkat, JavaScript/HTML di kotak aman).
- **Suara**: dikte saja — bicara lalu teks muncul di kolom chat. Tidak ada suara dari model.
- Markdown: **tebal**, *miring*, ~~coret~~, `kode`, daftar, kutipan, tabel, tautan.

Alat dipicu dari kalimat ("gambarkan…", "buat file pdf berisi…", "cari …", "buka https://…", "berapa 12*7") atau dari tombol +.

## Model & pelatihan
`model/weets-starter.wt` dipasang otomatis (1,6 juta parameter, konteks 160 token). Ekspor/impor `.wt` di halaman Model.
Tanya-jawab yang kamu ajarkan dijawab seketika (ingatan ajaran) dan dilatih ke model dalam hitungan detik. Pelatihan selalu melanjutkan model aktif.
