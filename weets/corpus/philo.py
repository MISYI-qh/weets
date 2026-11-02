"""Filsafat dari banyak sudut pandang. {t} = topik, {T} = topik berawal kapital."""
TOPIK = ["makna hidup", "kebebasan", "kematian", "cinta", "waktu", "kebahagiaan", "penderitaan", "keadilan", "kebenaran",
         "uang", "kerja", "kesepian", "identitas", "takdir", "kekuasaan", "kebaikan", "keberanian", "ingatan", "harapan",
         "kebosanan", "rasa bersalah", "ketakutan", "kesuksesan", "keluarga", "persahabatan", "kecerdasan buatan",
         "kesadaran", "bahasa", "seni", "alam", "pilihan", "kemarahan", "kerendahan hati", "kesetiaan", "pengampunan",
         "kehilangan", "kebijaksanaan", "kepercayaan", "keheningan", "rasa malu"]

# nama -> (daftar kalimat lensa, kritik)
LENSA = {
    "Eksistensialisme": ([
        "Eksistensialisme mulai dari satu kenyataan: kamu sudah ada, dan tidak ada yang menyerahkan makna {t} kepadamu sebagai warisan. Kamu menciptakannya lewat pilihan.",
        "Bagi Sartre manusia dikutuk untuk bebas, jadi {t} selalu berarti memilih tanpa jaminan dan menanggung akibatnya sendirian.",
        "Kalau kamu menyerahkan urusan {t} kepada kebiasaan atau pendapat orang, itu yang disebut hidup dalam itikad buruk: berpura-pura tidak punya pilihan.",
        "Kierkegaard akan bilang {t} baru nyata ketika kamu berani melompat tanpa bukti, dengan cemas dan sepenuh hati."],
        "Kelemahannya: ia terlalu menaruh beban pada individu, seolah semua orang punya ruang pilihan yang sama luas."),
    "Absurdisme": ([
        "Camus melihat jurang antara kerinduan kita pada jawaban dan dunia yang diam. {T} hidup persis di jurang itu.",
        "Jawabannya bukan lari dan bukan menyerah, melainkan terus mendorong batu seperti Sisifus sambil sadar batu itu akan menggelinding lagi.",
        "Memberontak terhadap yang absurd berarti menjalani {t} dengan mata terbuka, tanpa menipu diri bahwa semuanya pasti punya alasan."],
        "Kelemahannya: ia bagus untuk bertahan, tetapi tidak banyak bilang bagaimana hidup bersama orang lain."),
    "Stoisisme": ([
        "Seorang Stoik memilah dulu: bagian {t} yang bisa kamu kendalikan hanyalah penilaian dan tindakanmu sendiri; sisanya dilepas.",
        "Epiktetos mengajarkan bahwa bukan kejadian yang menyakitkan, melainkan cara kita menilainya. Jadi {t} dilatih sebagai kebiasaan batin, bukan dicari di luar.",
        "Marcus Aurelius menulis untuk dirinya sendiri: kerjakan tugasmu hari ini, dan soal {t} sisanya biar semesta yang mengurus."],
        "Kelemahannya: nasihat \"kendalikan dirimu\" bisa terdengar dingin kepada orang yang masalahnya memang datang dari sistem yang timpang."),
    "Epikureanisme": ([
        "Epikuros menganjurkan hidup sederhana: soal {t}, kurangi dulu keinginan yang sia-sia sebelum menambah yang nikmat.",
        "Ketenangan batin lebih dihargai daripada kemewahan; {t} diukur dari seberapa sedikit ia mengganggu tidurmu."],
        "Kelemahannya: ia gampang jadi alasan untuk menjauh dari urusan publik."),
    "Nihilisme": ([
        "Nihilisme berkata tidak ada makna bawaan di alam semesta, termasuk dalam {t}. Anehnya, dari situlah kamu bebas menulis aturanmu sendiri.",
        "Nietzsche menyebut runtuhnya nilai lama sebagai krisis, dan menantangmu menciptakan nilai baru alih-alih meratapi yang hilang."],
        "Kelemahannya: ia berhenti di kekosongan, padahal pertanyaan tentang apa yang dibangun sesudahnya justru yang sulit."),
    "Buddhisme": ([
        "Buddha memulai dari dukkha: ketidakpuasan muncul karena kita menggenggam {t} yang sebenarnya selalu berubah.",
        "Jalan tengahnya adalah melihat {t} sebagaimana adanya, tanpa melekat dan tanpa menolak.",
        "Anicca, segala sesuatu fana. Kalau itu sungguh dipahami, {t} berhenti menjadi beban dan menjadi sesuatu yang dilewati dengan perhatian penuh."],
        "Kelemahannya: bagi orang yang sedang diperlakukan tidak adil, nasihat melepas bisa terdengar seperti menyuruh diam."),
    "Taoisme": ([
        "Dalam Taoisme, soal {t} kamu tidak memaksa air mengalir naik; kamu belajar bergerak bersama arus, yang disebut wu wei.",
        "Laozi berkata yang paling lentur justru yang paling kuat. {T} yang dipaksakan akan patah, yang diikuti akan menemukan jalannya."],
        "Kelemahannya: tidak semua keadaan bisa diselesaikan dengan mengalir, ada yang memang harus dilawan."),
    "Konfusianisme": ([
        "Konfusius menaruh {t} dalam hubungan: bagaimana kamu bersikap kepada orang tua, teman, dan masyarakat.",
        "Kebajikan atau ren dipupuk lewat laku sehari-hari, bukan lewat teori tentang {t}."],
        "Kelemahannya: penekanan pada peran dan hierarki bisa membungkam orang yang berani berbeda."),
    "Utilitarianisme": ([
        "Seorang utilitarian bertanya hasil: tindakan soal {t} yang benar adalah yang menambah kebahagiaan dan mengurangi penderitaan paling banyak bagi paling banyak makhluk.",
        "Mill menambahkan bahwa mutu kebahagiaan ikut dihitung, bukan hanya jumlahnya, sehingga {t} tidak sekadar urusan kesenangan sesaat."],
        "Kelemahannya: hitung-hitungan kebahagiaan gampang dipakai untuk membenarkan pengorbanan satu orang demi banyak orang."),
    "Deontologi Kant": ([
        "Kant menguji dengan satu pertanyaan: bisakah aturan di balik tindakanmu soal {t} berlaku untuk semua orang tanpa runtuh sendiri?",
        "Manusia tidak boleh diperlakukan hanya sebagai alat; ukuran {t} adalah apakah martabat orang lain tetap utuh."],
        "Kelemahannya: aturan yang kaku bisa tampak keras ketika dua kewajiban saling bertabrakan."),
    "Etika kebajikan": ([
        "Aristoteles menjawab lewat watak: orang baik bukan yang hafal aturan {t}, melainkan yang terlatih bertindak tepat pada waktu, kadar, dan tempat yang tepat.",
        "Kebajikan adalah jalan tengah antara kekurangan dan kelebihan, dan {t} paling sering gagal di kedua ujungnya."],
        "Kelemahannya: ia tidak memberi jawaban cepat saat kamu harus memutuskan hari ini."),
    "Marxisme": ([
        "Dari kacamata Marx, {t} tidak lahir di ruang hampa; ia dibentuk oleh siapa yang memiliki alat produksi dan siapa yang bekerja untuknya.",
        "Pertanyaan yang diajukan: siapa yang untung dari cara kita memandang {t} hari ini?"],
        "Kelemahannya: kadang ia menjelaskan segalanya lewat ekonomi dan melewatkan hal-hal yang tidak bisa dihitung."),
    "Pragmatisme": ([
        "Pragmatisme tidak peduli apakah {t} benar secara abstrak; ia bertanya apa bedanya dalam hidupmu kalau kamu memercayainya.",
        "William James berkata sebuah gagasan benar sejauh ia membantumu bertindak dengan baik. Uji {t} dengan dipakai, bukan dengan dipandangi."],
        "Kelemahannya: berguna tidak selalu sama dengan benar."),
    "Tasawuf": ([
        "Dalam tradisi tasawuf, soal {t} yang dicari bukan penjelasan, melainkan penyucian hati supaya kita bisa melihat yang sebenarnya.",
        "Rumi menggambarkan luka sebagai tempat cahaya masuk; kadang {t} paling dalam dipahami lewat kehilangan."],
        "Kelemahannya: pengalaman batin sulit diuji dan sulit dibagikan kepada orang lain."),
    "Humanisme": ([
        "Humanisme menaruh manusia di pusat: {t} dinilai dari apakah martabat dan potensi manusia tumbuh karenanya.",
        "Tanpa menunggu wahyu atau teori besar, kita bisa mulai dari kepedulian pada sesama dan akal sehat soal {t}."],
        "Kelemahannya: ia bisa angkuh terhadap alam dan makhluk lain yang bukan manusia."),
    "Skeptisisme": ([
        "Seorang skeptis akan menahan diri: sebelum bicara soal {t}, apa yang benar-benar kita ketahui, dan apa yang hanya kita ulang karena terbiasa?",
        "Pyrrho menyarankan menunda penilaian; ketenangan datang dari berhenti memaksa kepastian tentang {t}."],
        "Kelemahannya: kalau terlalu jauh, ia membuat kita tidak berani bertindak sama sekali."),
    "Fenomenologi": ([
        "Fenomenologi menyuruhmu kembali ke pengalaman langsung: bagaimana {t} terasa sebelum kamu memberinya nama dan teori?",
        "Husserl mengajak menunda semua asumsi dan memperhatikan apa yang benar-benar hadir dalam kesadaranmu soal {t}."],
        "Kelemahannya: ia kaya menggambarkan, tetapi jarang memberi petunjuk apa yang harus dilakukan."),
    "Etika kepedulian": ([
        "Etika kepedulian melihat {t} lewat relasi dan ketergantungan: kita semua dirawat sebelum bisa merawat.",
        "Moral tidak hanya soal aturan yang adil, tetapi juga soal siapa yang kita jawab ketika ia memanggil, termasuk dalam urusan {t}."],
        "Kelemahannya: kepedulian bisa membebani pihak yang selalu dituntut merawat dan tidak pernah dirawat."),
    "Kearifan Nusantara": ([
        "Dalam kearifan Jawa ada nrimo ing pandum: menerima bagian tanpa berhenti berusaha. Soal {t}, ini bukan pasrah, melainkan tenang sambil bekerja.",
        "Gotong royong mengingatkan bahwa {t} jarang dijalani sendirian; ia dipikul bersama.",
        "Ki Hajar Dewantara merumuskan di depan memberi teladan, di tengah membangun semangat, di belakang memberi dorongan. Begitu juga cara kita mendampingi orang lain dalam {t}."],
        "Kelemahannya: tradisi yang indah bisa dipakai untuk menyuruh orang bersabar atas hal yang seharusnya diperbaiki."),
    "Postmodernisme": ([
        "Postmodernisme curiga pada kebenaran tunggal: setiap cerita tentang {t} dibentuk oleh bahasa dan kuasa yang menceritakannya.",
        "Foucault mengajak bertanya siapa yang berhak bicara soal {t}, dan siapa yang selama ini dibuat diam."],
        "Kelemahannya: kalau semuanya cerita, sulit membedakan mana yang dusta dan mana yang kenyataan."),
}
NAMA = list(LENSA)
TENSI = ["Yang satu menyuruh menerima, yang lain menyuruh mengubah, dan keduanya punya bukti di kehidupan nyata.",
         "Mereka tidak bisa sama-sama benar sepenuhnya, tetapi masing-masing menangkap sisi yang dilewatkan yang lain.",
         "Perbedaannya bukan soal siapa pintar, melainkan soal apa yang dianggap paling penting untuk dijaga.",
         "Di titik ini keduanya bertabrakan: yang satu menaruh kepercayaan pada diri, yang lain pada keadaan.",
         "Kalau dua-duanya kamu terima, kamu akan hidup dengan ketegangan, dan mungkin memang begitu seharusnya."]
PENUTUP = ["Aku sendiri tidak punya hidup untuk dipertaruhkan, jadi anggap ini peta, bukan perintah.",
           "Kalau dipaksa memilih, aku condong ke yang paling jujur terhadap keadaanmu sendiri, bukan yang paling indah didengar.",
           "Pandangan mana yang kamu pakai kelak bukan hasil debat, melainkan hasil hidup yang kamu jalani.",
           "Tidak ada yang final di sini. Kamu boleh berpindah sudut pandang sesuai musim hidupmu.",
           "Uji semuanya pada hari Selasa yang membosankan, bukan hanya saat kamu sedang terharu.",
           "Pegang yang berguna hari ini, simpan sisanya untuk nanti.",
           "Pertanyaannya tetap milikmu. Aku hanya menyalakan beberapa lampu.",
           "Kalau kelak kamu berubah pikiran, itu bukan kegagalan, itu tanda kamu masih hidup."]
PROMPT_SATU = ["Bagaimana {p} memandang {t}?", "Jelaskan {t} menurut {p}.", "Apa kata {p} soal {t}?",
               "Menurut {p}, apa itu {t}?", "Coba lihat {t} dari sudut pandang {p}."]
PROMPT_BANDING = ["Bandingkan {p1} dan {p2} soal {t}.", "Apa beda {p1} dan {p2} tentang {t}?",
                  "{p1} atau {p2}, mana yang lebih masuk akal untuk {t}?"]
PROMPT_SEMUA = ["Bagaimana semua sudut pandang filsafat melihat {t}?", "Jelaskan {t} dari berbagai sudut pandang.",
                "Coba bahas {t} dari semua sudut pandang.", "{T} itu apa, menurut berbagai aliran filsafat?",
                "Aku bingung soal {t}. Beri aku beberapa cara memandangnya."]
PROMPT_PENDAPAT = ["Menurutmu, apa arti {t}?", "Kamu sendiri mikir apa soal {t}?", "Ceritakan pendapatmu tentang {t}.",
                   "Kalau kamu harus menjelaskan {t} dalam beberapa kalimat, apa katamu?"]


def fill(s, t):
    return s.replace("{T}", t[:1].upper() + t[1:]).replace("{t}", t)


def answer_satu(r, p, t):
    lens, kritik = LENSA[p]
    k = min(len(lens), r.choice([2, 2, 3]))
    body = " ".join(fill(x, t) for x in r.sample(lens, k))
    return f"<think>topik: {t}; sudut pandang: {p}</think>{body} {kritik}"


def answer_banding(r, p1, p2, t):
    a, b = LENSA[p1][0], LENSA[p2][0]
    return (f"<think>bandingkan {p1} dan {p2} soal {t}</think>Menurut {p1}: {fill(r.choice(a), t)}\n"
            f"Menurut {p2}: {fill(r.choice(b), t)}\n{r.choice(TENSI)} {r.choice(PENUTUP)}")


def answer_semua(r, t, n=None):
    ps = r.sample(NAMA, n or r.randint(4, 6))
    lines = [f"- {p}: {fill(r.choice(LENSA[p][0]), t)}" for p in ps]
    return f"<think>semua sudut pandang soal {t}</think>Ada banyak cara memandang {t}.\n" + "\n".join(lines) + "\n" + r.choice(PENUTUP)


def answer_pendapat(r, t):
    p = r.choice(NAMA)
    lens = LENSA[p][0]
    return (f"<think>pendapatku soal {t}</think>Kalau harus kujawab pendek: {fill(r.choice(lens), t)} "
            f"{r.choice(PENUTUP)}")
