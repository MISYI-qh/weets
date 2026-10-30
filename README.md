# Weets (Misyi)

Jalankan: `python main.py` lalu buka http://localhost:8765 (web dan aplikasi memakai kode yang sama).
APK: push ke GitHub (branch main/master) → Actions → "Build APK (Weets)" → unduh artifact `weets-apk`.

## Model
- `model/weets-starter.wt`: model bawaan ±600 ribu parameter (598.912), dilatih dari nol dalam Bahasa Indonesia, tokenizer BPE yang tumbuh.
- Ekspor/impor `.wt` di halaman Model (bobot, tokenizer, konfigurasi, status optimizer).
- **Tumbuh**: kosakata bertambah otomatis saat kamu melatihnya (hanya bila terbukti memperpendek teksmu);
  kapasitas (tambah lapis / lebarkan MLP) hanya dipakai bila eksperimen kontrol-vs-kandidat membuktikan lebih baik.
- **Belajar dari like/dislike**: like = pasangan (pertanyaan, jawaban) dilatih; dislike = bisa memberi jawaban benar, dilatih.
  Tiap 5 feedback baru, Weets berlatih sendiri di latar belakang (bisa dimatikan di Pengaturan).

## Alat bawaan (tanpa API)
Cari web (DuckDuckGo, cadangan Wikipedia Indonesia), browser dalam aplikasi (tautan di chat dibuka di pembaca; ada tampilan web),
buat berkas (format pilihan sendiri, isi ditulis model) dengan pratinjau, analisis berkas & gambar, hitung, waktu,
contoh kode + tombol Jalankan, dikte suara (hanya suara → tulisan).

## Otonomi (belajar sendiri, tanpa membuka aplikasi)
`autolearn.py` memilih sendiri aksi berikutnya tiap menit: (1) latih pelajaran/ketikan baru → (2) bila online: cari topik dari daftar tujuan
(`weets.curiosity.Curriculum`: topik dasar, koreksi pengguna, rasa ingin tahu), baca halaman berbahasa Indonesia, pelajari (maks 40 halaman/hari)
→ (3) bila offline atau tak ada yang baru: konsolidasi (ulang pelajaran lama) dan uji pertumbuhan dengan data lokal.
Aktivitasnya terlihat di halaman Model → Aktivitas mandiri. Pemilihnya penjadwal berbasis aturan + statistik nyata, bukan model neural.

## Latar belakang (Android)
`service.py` = layanan latar depan (notifikasi tetap "Weets"): terus melatih pelajaran/ketikan baru dan menguji pertumbuhan
walau layar mati atau aplikasi di latar belakang. Aplikasi dan layanan berbagi kunci berkas (`job.lock`) agar tidak melatih bersamaan.
Notifikasi: selesai berlatih, jawaban selesai (saat aplikasi tidak terlihat), eksperimen pertumbuhan selesai.
Auto-start setelah HP menyala: ambil artifact `weets-apk-autostart` dari GitHub Actions (BootReceiver ditambahkan setelah build pertama; bila gagal pakai `weets-apk`).
Tombol "Izinkan berjalan di latar belakang" di Pengaturan meminta pengecualian hemat baterai.
Diagnostik kecepatan: halaman Model → Diagnostik. Bila WebView gagal memuat, layar menampilkan galatnya (bisa difoto).
