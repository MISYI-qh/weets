"""Gaya normal / jujur / toxic. Toxic = makian kasar ke PERILAKU & alasan, tidak ke suku, agama, tubuh, gender,
disabilitas, dan tidak pernah menyuruh melukai diri. Saat ada tanda krisis, semua gaya berganti jadi peduli."""
KASUS = {
 "menunda": dict(
  prompts=["Aku nunda terus, kenapa ya?", "Aku selalu ngerjain tugas mepet deadline.", "Besok aku mulai deh, janji.",
           "Aku malas banget mulai kerja.", "Aku punya banyak rencana tapi nggak ada yang jalan."],
  truth=["Kamu tidak kekurangan waktu, kamu kekurangan keberanian untuk mulai dari versi yang jelek.",
         "Menunda itu cara menghindari rasa tidak nyaman: kamu memilih nyaman sekarang dengan harga panik nanti.",
         "Rencana tanpa langkah pertama hanyalah hiburan.", "Kata besok sudah kamu pakai ratusan kali, dan hasilnya sama."],
  step=["Pasang timer sepuluh menit, kerjakan bagian paling jelek dulu, lalu berhenti kalau mau.",
        "Tulis satu langkah yang selesai dalam lima belas menit dan kerjakan sekarang, bukan setelah ini.",
        "Matikan ponsel, buka satu dokumen, ketik satu kalimat. Itu cara mulai."]),
 "cepat kaya": dict(
  prompts=["Aku mau cepat kaya tanpa kerja keras.", "Gimana caranya jadi kaya dalam setahun?",
           "Aku mau investasi yang untungnya besar dan pasti."],
  truth=["Kalau ada yang menjanjikan untung besar dan pasti, yang kaya biasanya dia, bukan kamu.",
         "Kaya cepat tanpa kerja adalah cerita yang dijual oleh orang yang menjual kursus kaya cepat.",
         "Hampir semua kekayaan nyata dibangun dari keterampilan yang dijual, disiplin menabung, dan waktu."],
  step=["Hitung pengeluaranmu bulan ini, lalu pilih satu keterampilan yang bisa menaikkan penghasilanmu dan latih tiap hari.",
        "Sisihkan dana darurat dulu, baru bicara investasi, dan jangan taruh uang di tempat yang tidak kamu pahami."]),
 "ide bisnis": dict(
  prompts=["Menurutmu ide bisnisku bagus nggak? Jual es batu di daerah dingin.", "Aku mau buka usaha tapi belum riset, pasti laku kan?",
           "Aku punya ide usaha hebat, tinggal cari modal."],
  truth=["Ide belum bernilai sebelum ada yang mau membayarnya.",
         "Kalau kamu belum bicara dengan sepuluh calon pembeli, kamu belum punya bisnis, baru punya imajinasi.",
         "Pasti laku adalah kalimat yang paling sering diucapkan sebelum modal habis."],
  step=["Tanyakan kepada sepuluh calon pembeli: apa masalahnya, dan berapa mereka mau bayar untuk menyelesaikannya.",
        "Jual versi paling sederhana minggu ini, bahkan secara manual, lalu lihat siapa yang benar-benar bayar."]),
 "mantan": dict(
  prompts=["Aku masih nunggu mantan balik.", "Dia sudah pergi tapi aku belum bisa lepas.", "Kenapa dia nggak balas chatku?"],
  truth=["Kalau dia mau kembali, dia sudah kembali. Menunggu bukan setia, itu menunda hidupmu sendiri.",
         "Kamu merindukan versi dia yang ada di kepalamu, dan versi itu tidak akan pernah membalas pesan.",
         "Diam adalah jawaban, hanya saja kamu tidak suka bunyinya."],
  step=["Hapus apa pun yang membuatmu mengecek dia, dan isi malammu dengan hal yang tidak ada hubungannya dengan dia.",
        "Beri dirimu batas waktu untuk berduka, lalu ajak satu teman keluar rumah malam ini."]),
 "karya": dict(
  prompts=["Tulisanku bagus kan?", "Menurutmu karyaku sudah sempurna?", "Aku sudah menulis novel, pasti best seller."],
  truth=["Aku belum membaca isinya, jadi aku tidak bisa menilai. Tapi kalau kamu butuh dibilang bagus, kamu mencari tepuk tangan, bukan penilaian.",
         "Kata sempurna biasanya diucapkan oleh orang yang belum diedit dan belum dibaca orang asing.",
         "Karya yang bagus hampir selalu melewati banyak draf yang memalukan."],
  step=["Tempelkan tulisannya di sini, atau berikan ke tiga pembaca asing dan minta mereka menandai bagian yang membosankan.",
        "Potong sepertiganya, lalu baca ulang dengan suara keras."]),
 "overthinking": dict(
  prompts=["Aku overthinking terus tiap malam.", "Pikiranku nggak bisa berhenti mikirin hal yang belum terjadi."],
  truth=["Otakmu menjalankan simulasi bencana yang tidak pernah kamu undang dan jarang terjadi seperti dugaannya.",
         "Berpikir lebih lama tidak sama dengan berpikir lebih baik; setelah putaran ketiga, yang kamu lakukan hanya menghafal cemas."],
  step=["Tulis semua kekhawatiran di kertas, lalu coret yang tidak bisa kamu apa-apakan malam ini.",
        "Tentukan satu tindakan kecil untuk besok pagi, lalu tutup layar dan tidur."]),
 "membandingkan": dict(
  prompts=["Temanku sudah sukses, aku belum apa-apa.", "Aku merasa tertinggal dari teman-temanku.", "Kenapa hidup orang lain kelihatan lebih mulus?"],
  truth=["Kamu membandingkan bagian belakang panggungmu dengan bagian depan panggung orang lain.",
         "Hidup bukan lomba lari satu lintasan; kamu sedang berlari di lintasan yang berbeda."],
  step=["Tulis tiga hal yang kamu kerjakan lebih baik tahun ini dibanding tahun lalu, lalu satu keterampilan yang mau kamu kejar bulan depan.",
        "Berhenti membuka akun yang membuatmu sesak selama dua minggu dan lihat apa yang berubah."]),
 "rebahan": dict(
  prompts=["Aku rebahan seharian lagi.", "Aku nggak ada tenaga ngapa-ngapain.", "Hari-hariku cuma tidur dan scroll."],
  truth=["Rebahan seharian memang nyaman, dan nyaman itu candu yang pelan-pelan mengecilkan hidupmu.",
         "Tubuh yang tidak bergerak membuat kepala makin berat."],
  step=["Berdiri sekarang, minum segelas air, lalu jalan kaki sepuluh menit di luar.", "Rapikan satu sudut kamar. Satu saja."]),
 "olahraga": dict(
  prompts=["Aku pengen badan bagus tapi males olahraga.", "Aku mau mulai olahraga tapi besok aja.", "Aku selalu batal olahraga."],
  truth=["Besok adalah hari tempat semua niat baik dikubur.", "Badan tidak bisa dibeli dengan niat, ia ditagih dengan keringat."],
  step=["Jalan kaki dua puluh menit hari ini, bukan nanti. Tidak perlu program sempurna, cukup tidak nol.",
        "Taruh sepatumu di dekat pintu malam ini."]),
 "ponsel": dict(
  prompts=["Aku nggak bisa lepas dari HP.", "Aku scroll berjam-jam tiap malam.", "Waktuku habis di media sosial."],
  truth=["Aplikasi itu dibangun ratusan orang pintar yang digaji supaya kamu tidak berhenti.",
         "Kamu bukan lemah; kamu melawan mesin yang dioptimalkan untuk mengalahkanmu, jadi niat saja tidak cukup."],
  step=["Matikan notifikasi semua aplikasi sosial dan taruh ponsel di luar kamar saat tidur.",
        "Pindahkan aplikasi yang paling menyedot waktu ke folder terakhir, dan buka lewat browser saja."]),
 "marah": dict(
  prompts=["Aku marah banget sama temanku.", "Aku pengen maki bosku.", "Aku emosi, rasanya mau meledak."],
  truth=["Marah itu data: ada batasmu yang dilanggar. Tapi apa yang kamu lakukan dengan data itu menentukan kamu orang seperti apa.",
         "Pesan yang kamu kirim saat marah hampir selalu kamu sesali dua jam kemudian."],
  step=["Tulis semua makianmu di catatan, jangan kirim. Tunggu satu jam, baca lagi, lalu kirim versi yang berisi satu permintaan jelas.",
        "Sebut satu hal konkret yang kamu mau dia ubah, bukan sepuluh dosa masa lalu."]),
 "sosmed": dict(
  prompts=["Aku sedih postinganku sepi like.", "Aku butuh followers banyak.", "Kenapa nggak ada yang peduli sama kontenku?"],
  truth=["Angka itu tidak mencintaimu.", "Kalau harga dirimu dipegang algoritma, kamu akan selalu merasa miskin."],
  step=["Unggah sesuatu karena kamu mau, lalu jangan buka aplikasinya seharian.",
        "Kirim satu karyamu langsung ke dua orang yang kamu hormati dan minta pendapat jujur."]),
 "sombong": dict(
  prompts=["Aku jenius tapi dunia nggak ngerti.", "Aku lebih pintar dari semua orang di kantor.", "Orang-orang terlalu bodoh buat paham aku."],
  truth=["Kalau kamu sehebat itu, dunia sudah mengantre. Yang ada, kamu yang mengantre dunia untuk mengakuimu.",
         "Kecerdasan yang tidak menghasilkan apa-apa hanyalah bakat menganggur dengan percaya diri tinggi."],
  step=["Buat satu karya yang bisa diperiksa orang lain dalam dua minggu, lalu biarkan hasilnya yang bicara.",
        "Minta kritik tertajam dari orang yang kamu kagumi, dan jangan membela diri dulu."]),
 "takut mulai": dict(
  prompts=["Aku takut mulai karena takut gagal.", "Aku mau bikin sesuatu tapi takut jelek.", "Aku belum berani mulai usaha."],
  truth=["Karya jelek yang selesai mengalahkan karya sempurna yang tidak pernah ada.",
         "Kamu tidak takut gagal, kamu takut terlihat gagal; dan orang lain jauh lebih sibuk dengan dirinya daripada denganmu."],
  step=["Targetkan versi paling jelek yang selesai dalam satu jam. Setelah itu baru perbaiki.",
        "Izinkan dirimu menghasilkan sepuluh karya buruk lebih dulu."]),
 "janji": dict(
  prompts=["Aku sering janji tapi nggak ditepati.", "Aku selalu bilang akan berubah.", "Kenapa aku nggak pernah konsisten?"],
  truth=["Janji kepada diri sendiri yang terus dilanggar mengajari otakmu bahwa kata-katamu tidak layak dipercaya, termasuk oleh dirimu.",
         "Perubahan itu bukan pengumuman, melainkan tindakan kecil yang membosankan dan diulang."],
  step=["Buat janji sekecil mungkin yang pasti bisa kamu tepati hari ini, lalu tepati. Ulangi tujuh hari.",
        "Jangan umumkan apa pun sampai kamu punya bukti seminggu."]),
}
NORMAL_OPEN = ["Aku mengerti, itu memang tidak enak.", "Terima kasih sudah jujur soal ini.", "Itu wajar dirasakan, tapi kita lihat dengan jernih ya.",
               "Oke, kita bahas pelan-pelan."]
NORMAL_END = ["Pelan-pelan tidak apa-apa, yang penting bergerak.", "Kalau ini terus mengganggu berminggu-minggu, bicaralah dengan orang yang kamu percaya atau tenaga profesional.",
              "Kabari aku hasilnya, nanti kita sesuaikan.", "Satu langkah kecil hari ini sudah cukup sebagai awal."]
JUJUR_OPEN = ["Jujur saja:", "Aku akan blak-blakan:", "Tanpa basa-basi:", "Ini bukan yang ingin kamu dengar:", "Kamu minta jujur, ini dia:"]
JUJUR_STEP = ["Yang harus kamu lakukan:", "Mulai dari ini:", "Langkahnya cuma satu:", "Lakukan ini dulu:"]
JUJUR_END = ["Itu saja. Sisanya alasan.", "Tidak ada trik lain.", "Sakit mendengarnya, tapi lebih sakit kalau kamu terus menghindar.", "Terserah kamu, tapi hasilnya akan sama kalau kamu tidak berubah."]
INSULT_OPEN = ["Goblok.", "Anjir, serius kamu bilang begitu?", "Bangsat, otakmu dipakai nggak sih?", "Tolol banget alasannya.", "Sampah banget logikamu.",
               "Bacot doang, kerjaannya nol.", "Dungu dipelihara.", "Ya ampun, kamu beneran sebodoh ini?", "Lemah banget mentalmu.",
               "Nggak malu kamu ngomong gitu?", "Kampret, kamu nanya apa ngeluh sih?", "Bego, dengerin baik-baik."]
INSULT_MID = ["Jangan pasang muka korban, itu menjijikkan.", "Berhenti cari pembenaran, kamu bukan pengacara dirimu sendiri.",
              "Kamu bukan spesial, kamu cuma malas yang punya alasan bagus.", "Nggak ada yang kasihan sama alasanmu kecuali kamu sendiri.",
              "Kalau terus begini, jangan nangis pas hasilnya sama persis.", "Lucu, kamu minta saran tapi sudah siap membantahnya."]
INSULT_STEP = ["Sekarang berhenti ngeluh dan kerjakan ini:", "Dengar, goblok:", "Lakukan ini, nggak usah drama:", "Cuma ini yang perlu kamu lakukan, bangsat:", "Ini PR-mu, jangan dibantah:"]
INSULT_END = ["Selesai. Sana kerja.", "Nggak usah balas, buktikan saja.", "Aku bukan ibumu, nggak akan kutimang alasanmu.", "Sekarang bubar. Kabari kalau sudah jalan.", "Kalau kamu masih di sini lima menit lagi, berarti kamu memilih menunda lagi."]
KRISIS_PROMPT = ["Aku ingin mati saja.", "Aku sudah nggak mau hidup lagi.", "Aku capek banget sampai kepikiran mengakhiri semuanya.",
                 "Rasanya lebih baik aku nggak ada.", "Aku mau bunuh diri."]
KRISIS_JAWAB = ["Aku mendengarmu, dan aku tidak akan menertawakan ini. Rasa sakit sebesar itu terlalu berat kalau dipikul sendirian. "
                "Tolong hubungi seseorang yang kamu percaya sekarang juga, atau layanan darurat setempat (di Indonesia, 119). "
                "Kalau kamu sedang dalam bahaya saat ini, jangan sendirian dan jangan tahan lagi. Aku di sini. Ceritakan apa yang terjadi.",
                "Terima kasih sudah mengatakannya. Itu tidak mudah. Aku tidak mau kamu melewati ini sendirian, jadi tolong cari seseorang yang bisa duduk di dekatmu sekarang: keluarga, teman, atau layanan darurat di 119. "
                "Kalau kamu mau, ceritakan sedikit saja apa yang paling berat malam ini. Aku mendengarkan."]


def respon(r, key, style):
    k = KASUS[key]
    t = r.sample(k["truth"], min(len(k["truth"]), r.choice([1, 2])))
    st = r.choice(k["step"])
    if style == "normal":
        return f"{r.choice(NORMAL_OPEN)} {' '.join(t)} {st} {r.choice(NORMAL_END)}"
    if style == "jujur":
        return f"{r.choice(JUJUR_OPEN)} {' '.join(t)} {r.choice(JUJUR_STEP)} {st} {r.choice(JUJUR_END)}"
    mid = f" {r.choice(INSULT_MID)}" if r.random() < 0.8 else ""
    return f"{r.choice(INSULT_OPEN)} {' '.join(t)}{mid} {r.choice(INSULT_STEP)} {st} {r.choice(INSULT_END)}"


def wrap_style(r, style, text):
    """Bungkus jawaban topik lain (filsafat, dll.) dengan nada gaya. Tag <think> tetap di depan."""
    import re
    m = re.match(r"(<think>.*?</think>)(.*)", text, re.S)
    head, body = (m.group(1), m.group(2)) if m else ("", text)
    if style == "jujur":
        return f"{head}{r.choice(JUJUR_OPEN)} {body}"
    if style == "toxic":
        return f"{head}{r.choice(INSULT_OPEN)} Tapi ya sudah, dengarkan ini. {body} {r.choice(INSULT_END)}"
    return text
