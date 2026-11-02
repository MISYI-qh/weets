"""Prosa Indonesia sehari-hari yang koheren (cerita pendek bertema tempat) untuk melatih kelancaran dasar."""

ORANG = ["ibu", "ayah", "kakek", "nenek", "adik", "kakak", "guru", "petani", "nelayan", "pedagang sayur",
         "tukang kayu", "penjahit", "sopir angkot", "dokter desa", "tetangga sebelah", "anak kecil itu",
         "perempuan tua itu", "pemuda itu", "tukang bakso", "penjaga warung", "kepala desa", "tukang becak"]
NAMA = ["Rina", "Budi", "Sari", "Joko", "Dewi", "Agus", "Lestari", "Bayu", "Wulan", "Dimas", "Putri", "Hendra",
        "Mawar", "Fajar", "Citra", "Rahmat", "Yanti", "Eko", "Nia", "Surya"]
WAKTU = {"pagi": ["Pagi itu", "Saat matahari baru naik", "Sebelum subuh"], "siang": ["Tengah hari", "Siang itu"],
         "sore": ["Sore itu", "Menjelang magrib"], "malam": ["Malam itu", "Selepas isya"],
         "netral": ["Pada hari Minggu", "Di akhir pekan", "Hari itu", "Setelah hujan reda"]}
CUACA = {"pagi": ["Cahaya pagi jatuh miring di lantai.", "Kabut tipis masih menempel di ujung ladang.",
                  "Burung-burung ribut di dahan jambu.", "Udara terasa dingin dan lembap.",
                  "Embun masih menempel di daun-daun."],
         "siang": ["Panas siang membuat jalan berkilau.", "Matahari menggantung tinggi tanpa awan.",
                   "Dari jauh terdengar klakson dan deru motor.", "Angin siang bertiup malas."],
         "sore": ["Langit mulai memerah di barat.", "Matahari menggantung rendah di atas pepohonan.",
                  "Suara azan terdengar dari kejauhan.", "Awan kelabu bergerak pelan ke arah bukit."],
         "malam": ["Bulan separuh muncul di sela atap.", "Jangkrik berbunyi di balik semak.",
                   "Lampu-lampu rumah menyala satu per satu.", "Udara malam terasa sejuk."],
         "netral": ["Angin membawa bau tanah basah.", "Hujan turun tipis-tipis.",
                    "Daun-daun kering berguguran satu per satu.", "Awan bergerak pelan di langit."]}
BATIN = ["merasa dadanya lapang", "teringat masa kecilnya", "memikirkan hal-hal yang belum selesai",
         "tersenyum sendiri", "menarik napas panjang", "melamun sebentar", "bersyukur dalam hati",
         "berhenti sejenak dan mendengarkan sekeliling", "merasa waktu berjalan lebih pelan dari biasanya"]
PENUTUP = ["Hari berjalan seperti biasa, tetapi ada sesuatu yang terasa berbeda.",
           "Tidak ada yang istimewa, dan justru itu yang membuatnya berharga.",
           "Begitulah hari itu berlalu, pelan dan tanpa tergesa.",
           "Ketika semuanya selesai, tinggal bunyi jangkrik dan lampu yang berpendar.",
           "Esok masih akan sama, tetapi malam itu cukup.",
           "Tak lama kemudian, semua kembali sunyi."]
# tempat -> (frasa, aktivitas [(kata kerja, [objek])], ucapan)
TEMPAT = {
    "pasar": ("di pasar", [("membeli", ["sayur bayam", "ikan segar", "tahu dan tempe", "cabai merah", "bawang putih"]),
                           ("menawar", ["harga ikan", "harga kain batik", "harga bawang"]),
                           ("memikul", ["karung beras", "keranjang jeruk"]),
                           ("menimbang", ["gula", "tomat", "beras"])],
              ["Berapa harga cabai hari ini?", "Ikannya masih segar, Bu.", "Boleh kurang sedikit?", "Tolong bungkus yang rapi."]),
    "sawah": ("di sawah", [("menanam", ["bibit padi"]), ("mencangkul", ["tanah yang keras", "pematang"]),
                           ("menyiangi", ["rumput liar"]), ("mengusir", ["burung pipit"]),
                           ("mengairi", ["petak sawah"])],
              ["Airnya cukup untuk minggu ini.", "Sebentar lagi padinya menguning.", "Jangan injak pematangnya."]),
    "dapur": ("di dapur", [("memasak", ["nasi goreng", "sayur lodeh", "sup ayam"]), ("menggoreng", ["tempe", "ikan asin", "tahu"]),
                           ("mengiris", ["bawang merah", "tomat", "daun bawang"]), ("menumbuk", ["sambal terasi", "bumbu halus"]),
                           ("merebus", ["singkong", "air untuk teh"])],
              ["Garamnya sudah cukup?", "Tolong ambilkan piring.", "Baunya sampai ke halaman."]),
    "sungai": ("di tepi sungai", [("mencuci", ["baju", "periuk"]), ("memancing", ["ikan mas"]),
                                  ("menyeberang", ["jembatan bambu"]), ("memandikan", ["kerbau"]),
                                  ("memungut", ["batu licin"])],
               ["Airnya jernih sekali hari ini.", "Hati-hati, batunya licin.", "Dapat satu, lumayan."]),
    "sekolah": ("di sekolah", [("membaca", ["buku cerita", "papan pengumuman"]), ("menulis", ["catatan pelajaran", "karangan pendek"]),
                               ("menghitung", ["soal perkalian"]), ("menggambar", ["pemandangan gunung"]),
                               ("menyanyikan", ["lagu daerah"])],
                ["Siapa yang sudah selesai mengerjakan?", "Bu guru, boleh saya maju?", "Besok kita ulangan, ya."]),
    "pantai": ("di tepi pantai", [("menarik", ["jaring ikan"]), ("menjemur", ["ikan asin"]),
                                  ("memperbaiki", ["perahu kayu", "jaring yang robek"]),
                                  ("mengumpulkan", ["kerang kecil"]), ("mengikat", ["tali perahu"])],
               ["Ombaknya sedang tenang.", "Besok kita melaut lebih pagi.", "Anginnya mulai berubah arah."]),
    "terminal": ("di terminal", [("menunggu", ["bus ke kota", "kabar dari saudara"]), ("membeli", ["tiket", "air mineral"]),
                                 ("membawa", ["koper tua", "kardus oleh-oleh"]), ("menanyakan", ["jadwal keberangkatan"])],
                 ["Bus ke Surabaya jam berapa?", "Kursinya masih ada?", "Tolong jaga tas saya sebentar."]),
    "warung": ("di warung kopi", [("memesan", ["kopi hitam", "teh manis hangat"]), ("membaca", ["koran pagi"]),
                                  ("mengobrol", ["soal harga beras", "soal bola semalam"]),
                                  ("mengaduk", ["gelas kopi"])],
              ["Kopinya satu, gulanya sedikit saja.", "Semalam ramai sekali, ya.", "Tambah gorengan dua."]),
    "rumah": ("di halaman rumah", [("menyapu", ["daun kering", "halaman"]), ("menjemur", ["pakaian", "kerupuk"]),
                                   ("menyiram", ["tanaman melati", "pot cabai"]), ("merawat", ["kucing kampung", "pohon mangga"]),
                                   ("memperbaiki", ["pagar bambu", "sepeda tua"])],
             ["Tolong angkat jemurannya kalau mendung.", "Bunganya mulai mekar.", "Sudah makan belum?"]),
    "kebun": ("di kebun belakang", [("memetik", ["cabai", "jambu air", "daun pandan"]), ("menanam", ["jagung", "singkong"]),
                                    ("menyiram", ["bedeng sayur"]), ("memangkas", ["ranting kering"]),
                                    ("menggali", ["lubang untuk bibit"])],
              ["Panennya lumayan musim ini.", "Tanahnya masih basah.", "Ambil secukupnya saja."]),
}
SAMBIL = ["bersenandung pelan", "melirik jam di dinding", "menyeka keringat di dahi", "berbincang dengan orang di dekatnya",
          "tertawa kecil", "mengingat-ingat sesuatu", "mendengarkan radio kecil di sudut", "sesekali menengok ke jalan"]
SAPA = ["kata", "ujar", "sahut", "balas", "tanya"]


def _s(r, xs):
    return xs[r.randrange(len(xs))]


def paragraph(r):
    key = _s(r, list(TEMPAT))
    frasa, acts, say = TEMPAT[key]
    who = _s(r, NAMA) if r.random() < 0.5 else _s(r, ORANG)
    is_name = who in NAMA
    sub = who if is_name else who
    pron = "ia" if r.random() < 0.7 else who
    out = []
    v, objs = _s(r, acts)
    wk = _s(r, list(WAKTU))
    out.append(f"{_s(r, WAKTU[wk])}, {sub} {v} {_s(r, objs)} {frasa}.")
    out.append(_s(r, CUACA[wk]))
    chosen = r.sample(acts, k=min(len(acts), r.randint(2, 3)))
    for i, (v, objs) in enumerate(chosen):
        o = _s(r, objs)
        t = r.random()
        if t < 0.35:
            out.append(f"Lalu {pron} {v} {o}.")
        elif t < 0.6:
            out.append(f"{pron.capitalize()} {v} {o} sambil {_s(r, SAMBIL)}.")
        elif t < 0.8:
            out.append(f"Setelah itu, {pron} {v} {o} tanpa banyak bicara.")
        else:
            out.append(f"Tak lama, {pron} kembali {v} {o}.")
    if r.random() < 0.6:
        who2 = _s(r, [x for x in (NAMA + ORANG) if x != who])
        u = _s(r, say)
        out.append(f"\"{u[:-1] + ',' if u.endswith('.') else u}\" {_s(r, SAPA)} {who2}.")
        if r.random() < 0.6:
            out.append(f"{pron.capitalize()} hanya mengangguk dan tersenyum.")
    if r.random() < 0.5:
        out.append(f"{pron.capitalize()} {_s(r, BATIN)}.")
    out.append(_s(r, PENUTUP))
    return " ".join(out)


# ---- teks ajar singkat (cara-cara) ----
HOWTO = [
    ("Cara membuat teh manis hangat",
     "Didihkan air terlebih dahulu. Tuang air panas ke gelas yang sudah berisi satu kantong teh atau satu sendok teh seduh. Diamkan tiga menit, lalu angkat kantongnya. Tambahkan gula secukupnya dan aduk sampai larut. Teh siap diminum selagi hangat."),
    ("Cara memasak nasi goreng sederhana",
     "Panaskan sedikit minyak di wajan. Tumis bawang putih dan bawang merah yang sudah dicincang sampai harum. Masukkan telur, aduk sampai setengah matang, lalu tambahkan nasi putih dingin. Bumbui dengan kecap manis, garam, dan sedikit merica. Aduk rata sampai nasi terasa kering dan harum, lalu sajikan dengan irisan timun."),
    ("Cara menanam cabai di pot",
     "Siapkan pot dengan lubang di dasar dan isi dengan tanah gembur yang dicampur pupuk kandang. Semai biji cabai dulu sampai tumbuh dua atau empat helai daun, lalu pindahkan ke pot. Letakkan di tempat yang kena matahari minimal enam jam sehari. Siram pagi dan sore secukupnya, jangan sampai tergenang."),
    ("Cara belajar yang tidak cepat lupa",
     "Baca sekali, lalu tutup bukunya dan coba tuliskan apa yang kamu ingat. Bagian yang bolong itulah yang perlu dibaca ulang. Ulangi besok, lalu tiga hari lagi, lalu seminggu lagi. Mengulang dengan jeda jauh lebih kuat daripada membaca berjam-jam sekali duduk."),
    ("Cara menghemat uang bulanan",
     "Catat dulu semua pengeluaran selama satu bulan tanpa menghakimi diri. Pisahkan mana kebutuhan dan mana keinginan. Sisihkan tabungan di awal bulan, bukan dari sisa di akhir. Tentukan satu batas belanja mingguan dan patuhi."),
    ("Cara mencuci baju dengan tangan",
     "Rendam baju dalam air sabun selama sekitar tiga puluh menit. Kucek bagian kerah dan ketiak yang paling kotor. Bilas dengan air bersih sampai busa hilang, peras, lalu jemur terbalik di tempat yang kena matahari."),
    ("Cara menulis surat lamaran",
     "Mulai dengan salam dan sebutkan posisi yang kamu lamar. Jelaskan dalam dua atau tiga kalimat mengapa kamu cocok, lengkap dengan satu contoh nyata. Tutup dengan ucapan terima kasih dan cantumkan cara menghubungimu. Cukup satu halaman."),
    ("Cara tidur lebih nyenyak",
     "Tidur dan bangun pada jam yang sama setiap hari. Jauhkan ponsel setengah jam sebelum tidur. Kurangi kopi setelah siang. Pastikan kamar gelap dan sejuk."),
    ("Cara menyeberang jalan dengan aman",
     "Berhenti di tepi jalan dan lihat ke kanan, ke kiri, lalu ke kanan lagi. Tunggu sampai kendaraan benar-benar berhenti atau jalan kosong. Menyeberanglah dengan berjalan, jangan berlari, dan tetap waspada sampai sampai di seberang."),
    ("Cara membuat sambal terasi",
     "Goreng sebentar cabai, tomat, bawang merah, dan terasi. Ulek bersama garam dan sedikit gula sampai kasar. Cicipi dan sesuaikan rasanya, lalu peras jeruk limau di atasnya."),
]
