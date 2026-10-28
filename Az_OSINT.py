import os, sys, json, socket, ssl, ipaddress, urllib.request, urllib.error, re, io, struct, datetime
from urllib.parse import quote_plus, urlencode, urlparse, urljoin
from html.parser import HTMLParser
from pathlib import Path

R = "\033[91m"
G = "\033[92m"
C = "\033[96m"
Y = "\033[93m"
W = "\033[0m"

SITES = {
    "GitHub": "https://github.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "Instagram": "https://www.instagram.com/{}/",
    "Reddit": "https://www.reddit.com/user/{}/",
    "YouTube": "https://www.youtube.com/@{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "GitLab": "https://gitlab.com/{}",
    "Twitch": "https://www.twitch.tv/{}",
}

SEARCH_SOURCES = {
    "Google (web)": "https://www.google.com/search?q={}",
    "YouTube": "https://www.google.com/search?q={}+site%3Ayoutube.com",
    "Reddit (posts/comments indexed)": "https://www.google.com/search?q={}+site%3Areddit.com",
    "TikTok": "https://www.google.com/search?q={}+site%3Atiktok.com",
    "Instagram": "https://www.google.com/search?q={}+site%3Ainstagram.com",
    "Facebook": "https://www.google.com/search?q={}+site%3Afacebook.com",
    "X": "https://www.google.com/search?q={}+site%3Ax.com",
}

class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current = None
        self.capture_title = False
        self.capture_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")
        if tag == "a" and "result__a" in classes:
            self.current = {"title": "", "url": attrs.get("href", "")}
            self.capture_title = True
        elif self.current and tag in ("a", "div") and "result__snippet" in classes:
            self.capture_snippet = True

    def handle_data(self, data):
        if self.current and self.capture_title:
            self.current["title"] += data
        elif self.current and self.capture_snippet:
            self.current["snippet"] = self.current.get("snippet", "") + data

    def handle_endtag(self, tag):
        if tag == "a" and self.capture_title:
            self.capture_title = False
            if self.current and self.current.get("title", "").strip():
                self.results.append(self.current)
                self.current = None
        if tag == "div" and self.capture_snippet:
            self.capture_snippet = False

# ─────────────────────────────────────────────
# HELPERS — GPS & MP4 (dipakai modul 17 & 18)
# ─────────────────────────────────────────────

def _gps_to_decimal(coords, ref):
    """Konversi tuple EXIF GPS ke decimal degrees."""
    try:
        def f(v):
            return v.numerator / v.denominator if hasattr(v, "numerator") and v.denominator else float(v)
        d, m, s = coords
        deg = f(d) + f(m) / 60 + f(s) / 3600
        return -deg if str(ref) in ("S", "W") else deg
    except Exception:
        return None


def _dec_to_dms(deg, axis):
    """Decimal degrees → DMS string (contoh: 6°12'3.00\"S)."""
    dirs = {"lat": ("N", "S"), "lon": ("E", "W")}
    d = int(abs(deg))
    m_f = (abs(deg) - d) * 60
    m = int(m_f)
    s = (m_f - m) * 60
    ref = dirs[axis][0] if deg >= 0 else dirs[axis][1]
    return f"{d}\u00b0{m}'{s:.2f}\"{ref}"

# ─────────────────────────────────────────────
# DATABASE PLAT NOMOR INDONESIA
# ─────────────────────────────────────────────
PLAT_DB = {
    # ── Jawa ──
    "A":  {"wilayah": "Banten",
           "kota": "Serang, Cilegon, Pandeglang, Lebak, Tangerang Kota, Serang Kota"},
    "B":  {"wilayah": "DKI Jakarta / Jabodetabek",
           "kota": "Jakarta (semua wilayah), Bekasi Kota/Kab, Tangerang Kota/Kab, Depok"},
    "D":  {"wilayah": "Jawa Barat",
           "kota": "Bandung Kota, Cimahi, Bandung Barat, Sumedang"},
    "E":  {"wilayah": "Jawa Barat",
           "kota": "Cirebon, Indramayu, Majalengka, Kuningan"},
    "F":  {"wilayah": "Jawa Barat",
           "kota": "Bogor Kota/Kab, Sukabumi Kota/Kab, Cianjur"},
    "G":  {"wilayah": "Jawa Tengah",
           "kota": "Pekalongan, Batang, Pemalang, Tegal, Brebes"},
    "H":  {"wilayah": "Jawa Tengah",
           "kota": "Semarang, Kendal, Demak, Salatiga, Ungaran"},
    "K":  {"wilayah": "Jawa Tengah",
           "kota": "Pati, Kudus, Jepara, Rembang, Blora, Grobogan, Purwodadi"},
    "R":  {"wilayah": "Jawa Tengah",
           "kota": "Banyumas, Cilacap, Purbalingga, Banjarnegara"},
    "T":  {"wilayah": "Jawa Barat",
           "kota": "Purwakarta, Karawang, Subang"},
    "Z":  {"wilayah": "Jawa Barat",
           "kota": "Garut, Tasikmalaya, Ciamis, Kota Banjar, Pangandaran"},
    "L":  {"wilayah": "Jawa Timur",
           "kota": "Surabaya"},
    "M":  {"wilayah": "Jawa Timur",
           "kota": "Madura — Bangkalan, Sampang, Pamekasan, Sumenep"},
    "N":  {"wilayah": "Jawa Timur",
           "kota": "Malang, Batu, Pasuruan, Probolinggo, Lumajang"},
    "P":  {"wilayah": "Jawa Timur",
           "kota": "Jember, Banyuwangi, Bondowoso, Situbondo"},
    "S":  {"wilayah": "Jawa Timur",
           "kota": "Bojonegoro, Tuban, Lamongan"},
    "W":  {"wilayah": "Jawa Timur",
           "kota": "Sidoarjo, Gresik"},
    "AA": {"wilayah": "Jawa Tengah",
           "kota": "Magelang, Temanggung, Wonosobo, Purworejo, Kebumen"},
    "AB": {"wilayah": "DI Yogyakarta",
           "kota": "Yogyakarta, Sleman, Bantul, Kulon Progo, Gunung Kidul"},
    "AD": {"wilayah": "Jawa Tengah",
           "kota": "Solo, Sukoharjo, Boyolali, Sragen, Karanganyar, Wonogiri, Klaten"},
    "AE": {"wilayah": "Jawa Timur",
           "kota": "Madiun, Ngawi, Magetan, Ponorogo, Pacitan"},
    "AG": {"wilayah": "Jawa Timur",
           "kota": "Kediri, Tulungagung, Blitar, Trenggalek, Nganjuk"},
    # ── Sumatera ──
    "BA": {"wilayah": "Sumatera Barat",
           "kota": "Padang, Bukittinggi, Payakumbuh, dan seluruh kab/kota Sumbar"},
    "BB": {"wilayah": "Sumatera Utara",
           "kota": "Tapanuli — Sibolga, Tapanuli Tengah, Tapanuli Selatan, Padang Sidempuan"},
    "BD": {"wilayah": "Bengkulu",
           "kota": "Bengkulu dan seluruh kabupaten Bengkulu"},
    "BE": {"wilayah": "Lampung",
           "kota": "Bandar Lampung dan seluruh Lampung"},
    "BG": {"wilayah": "Sumatera Selatan",
           "kota": "Palembang, Prabumulih, Pagaralam, Lubuklinggau, dan kab Sumsel"},
    "BH": {"wilayah": "Jambi",
           "kota": "Jambi dan seluruh kabupaten Jambi"},
    "BK": {"wilayah": "Sumatera Utara",
           "kota": "Medan, Deli Serdang, Binjai, Tebing Tinggi, Langkat, Karo, Simalungun, Dairi"},
    "BL": {"wilayah": "Aceh",
           "kota": "Banda Aceh dan seluruh Aceh"},
    "BM": {"wilayah": "Riau",
           "kota": "Pekanbaru, Dumai, dan seluruh Riau daratan"},
    "BN": {"wilayah": "Kepulauan Bangka Belitung",
           "kota": "Pangkalpinang, Bangka, Belitung, Bangka Barat, Bangka Tengah, Bangka Selatan"},
    "BP": {"wilayah": "Kepulauan Riau",
           "kota": "Batam, Tanjungpinang, Bintan, Karimun, Natuna, Lingga, Anambas"},
    "BV": {"wilayah": "Sumatera Selatan",
           "kota": "OKU, Ogan Komering Ulu, Muara Enim (sub-area Sumsel)"},
    # ── Kalimantan ──
    "DA": {"wilayah": "Kalimantan Selatan",
           "kota": "Banjarmasin, Banjarbaru, dan seluruh Kalsel"},
    "KB": {"wilayah": "Kalimantan Barat",
           "kota": "Pontianak, Singkawang, dan seluruh Kalbar"},
    "KH": {"wilayah": "Kalimantan Tengah",
           "kota": "Palangkaraya dan seluruh Kalteng"},
    "KT": {"wilayah": "Kalimantan Timur",
           "kota": "Samarinda, Balikpapan, Bontang, dan seluruh Kaltim"},
    "KU": {"wilayah": "Kalimantan Utara",
           "kota": "Tarakan, Bulungan, Nunukan, Malinau, Tana Tidung"},
    # ── Sulawesi ──
    "DB": {"wilayah": "Sulawesi Utara",
           "kota": "Manado, Bitung, Tomohon, Kotamobagu, dan kab Sulut"},
    "DC": {"wilayah": "Sulawesi Barat",
           "kota": "Mamuju dan seluruh Sulbar"},
    "DD": {"wilayah": "Sulawesi Selatan",
           "kota": "Makassar, Pare-Pare, Palopo, dan seluruh Sulsel"},
    "DE": {"wilayah": "Maluku",
           "kota": "Ambon dan seluruh Maluku"},
    "DG": {"wilayah": "Sulawesi Selatan",
           "kota": "Gowa, Takalar, Jeneponto (sub-area Sulsel)"},
    "DH": {"wilayah": "NTT",
           "kota": "Kupang Kota/Kab dan sekitar"},
    "DL": {"wilayah": "Sulawesi Utara",
           "kota": "Kepulauan Sangihe, Talaud, Sitaro"},
    "DM": {"wilayah": "Gorontalo",
           "kota": "Gorontalo Kota dan seluruh provinsi Gorontalo"},
    "DN": {"wilayah": "Sulawesi Tengah",
           "kota": "Palu dan seluruh Sulteng"},
    "DT": {"wilayah": "Sulawesi Tenggara",
           "kota": "Kendari, Baubau, dan seluruh Sultra"},
    "DW": {"wilayah": "Sulawesi Selatan",
           "kota": "Bulukumba, Selayar, Bantaeng (sub-area Sulsel)"},
    # ── Bali & Nusa Tenggara ──
    "DK": {"wilayah": "Bali",
           "kota": "Denpasar, Badung, Gianyar, Tabanan, Klungkung, Bangli, Karangasem, Buleleng, Jembrana"},
    "DR": {"wilayah": "NTB",
           "kota": "Mataram, Lombok Barat, Lombok Tengah, Lombok Timur, Lombok Utara"},
    "EA": {"wilayah": "NTB",
           "kota": "Sumbawa Besar, Dompu, Bima — Pulau Sumbawa"},
    "EB": {"wilayah": "NTT",
           "kota": "Flores — Ende, Sikka, Flores Timur, Ngada, Manggarai, dll"},
    "ED": {"wilayah": "NTT",
           "kota": "Sumba — Sumba Barat, Sumba Timur, Sumba Tengah, Sumba Barat Daya"},
    # ── Papua & Maluku Utara ──
    "PA": {"wilayah": "Papua",
           "kota": "Jayapura dan wilayah Papua (induk)"},
    "PB": {"wilayah": "Papua Barat",
           "kota": "Manokwari, Sorong, Raja Ampat, dan seluruh Papua Barat"},
    "PG": {"wilayah": "Papua Pegunungan",
           "kota": "Wamena, Jayawijaya, dan wilayah pegunungan Papua"},
    "PP": {"wilayah": "Papua Selatan",
           "kota": "Merauke, Boven Digoel, Mappi, Asmat"},
    "PT": {"wilayah": "Papua Tengah",
           "kota": "Nabire, Paniai, Mimika, Puncak, Puncak Jaya, Dogiyai, Intan Jaya, Deiyai"},
    "SA": {"wilayah": "Maluku Utara",
           "kota": "Ternate, Tidore, dan seluruh Maluku Utara"},
}

WARNA_PLAT = {
    "1": ("Hitam",   "Kendaraan pribadi — format lama"),
    "2": ("Putih",   "Kendaraan pribadi — format baru (berlaku bertahap sejak 2022)"),
    "3": ("Kuning",  "Angkutan umum / kendaraan niaga / komersial"),
    "4": ("Merah",   "Kendaraan dinas pemerintah / TNI / Polri"),
    "5": ("Hijau",   "Kawasan Free Trade Zone — Batam, Bintan, Karimun"),
}

def _jakarta_sub(seri):
    """Estimasi sub-wilayah Jakarta dari huruf pertama seri."""
    if not seri:
        return None
    f = seri[0].upper()
    if f in "ABCDEF": return "Jakarta Pusat / Kota"
    if f in "GHIJ":   return "Jakarta Utara"
    if f in "KLMN":   return "Jakarta Barat"
    if f in "PQRS":   return "Jakarta Selatan"
    if f in "TUVWXYZ": return "Jakarta Timur / Bekasi / Tangerang"
    return None


# ─────────────────────────────────────────────
# HELPER — image geo tools (dipakai modul 23 & 24)
# ─────────────────────────────────────────────
def _print_maps_links(lat, lon, source=""):
    print(G + f"\n[GPS — {source}]" + W)
    print(f"Koordinat     : {lat:.6f}, {lon:.6f}")
    print(f"Google Maps   : https://maps.google.com/?q={lat},{lon}")
    print(f"Street View   : https://www.google.com/maps/@{lat},{lon},3a,90y,0h,90t/data=!3m1!1e3")
    print(f"Satellite     : https://www.google.com/maps/@{lat},{lon},18z/data=!3m1!1e3")
    print(f"Google Earth  : https://earth.google.com/web/@{lat},{lon},0a,500d,35y,0h,45t,0r")
    print(f"OpenStreetMap : https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=17")
    try:
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json",
            headers={"User-Agent": "AZ-OSINT-Tool/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as res:
            geo = json.loads(res.read().decode("utf-8"))
        print(G + f"Lokasi        : {geo.get('display_name', '')}" + W)
    except Exception:
        pass


def _print_ai_geo_tools():
    print(C + "\n[AI Geolocation Tools — upload manual di browser]" + W)
    print(f"GeoSpy AI   : https://geospy.ai")
    print(f"  → Upload foto → AI prediksi koordinat → link Google Maps langsung")
    print(f"Picarta AI  : https://picarta.ai")
    print(f"  → Mirip GeoSpy, berbasis neural network geolocation")
    print(f"Google Lens : https://lens.google.com")
    print(f"  → Deteksi landmark, gedung, papan nama → tampilkan lokasi")
    print(f"Yandex      : https://yandex.com/images")
    print(f"  → Reverse image search — akurat untuk Asia & Eropa Timur")
    print(Y + "\nCatatan: AI geolocation tanpa GPS bergantung pada landmark visual — gedung, vegetasi, arsitektur, papan jalan. GeoSpy & Picarta adalah tool paling dedicated untuk ini." + W)

MAC_EPOCH = 2082844800  # detik antara Mac epoch (1904) dan Unix epoch (1970)

def _find_mp4_box(data, offset, target):
    """Cari satu MP4 box by type. Return (pos, size, header_size) atau (-1,0,0)."""
    pos = offset
    target_b = target.encode("latin-1")
    while pos + 8 <= len(data):
        size = struct.unpack(">I", data[pos:pos+4])[0]
        btype = data[pos+4:pos+8]
        if size == 1 and pos + 16 <= len(data):
            size = struct.unpack(">Q", data[pos+8:pos+16])[0]
            hdr = 16
        elif size == 0:
            size = len(data) - pos
            hdr = 8
        else:
            hdr = 8
        if size < 8:
            break
        if btype == target_b:
            return pos, size, hdr
        pos += size
    return -1, 0, 0


def parse_mp4_metadata(data):
    """Ekstrak metadata dasar dari binary MP4/MOV. Return dict."""
    result = {}

    # ftyp — brand/format
    p, sz, h = _find_mp4_box(data, 0, "ftyp")
    if p >= 0 and p + 12 <= len(data):
        brand = data[p+8:p+12].decode("latin-1", errors="replace").strip()
        result["Format"] = f"MP4/QuickTime (brand: {brand})"

    # moov — container utama
    p, sz, h = _find_mp4_box(data, 0, "moov")
    if p < 0:
        return result
    moov = data[p+h:p+sz]

    # mvhd — movie header: creation time, duration
    mp, msz, mh = _find_mp4_box(moov, 0, "mvhd")
    if mp >= 0:
        mvhd = moov[mp+mh:mp+msz]
        ver = mvhd[0] if mvhd else 0
        try:
            if ver == 1 and len(mvhd) >= 32:
                ct  = struct.unpack(">Q", mvhd[4:12])[0]
                mt  = struct.unpack(">Q", mvhd[12:20])[0]
                ts  = struct.unpack(">I", mvhd[20:24])[0]
                dur = struct.unpack(">Q", mvhd[24:32])[0]
            elif len(mvhd) >= 20:
                ct  = struct.unpack(">I", mvhd[4:8])[0]
                mt  = struct.unpack(">I", mvhd[8:12])[0]
                ts  = struct.unpack(">I", mvhd[12:16])[0]
                dur = struct.unpack(">I", mvhd[16:20])[0]
            else:
                ct = mt = ts = dur = 0
            if ct > MAC_EPOCH:
                result["Dibuat"] = datetime.datetime.utcfromtimestamp(ct - MAC_EPOCH).strftime("%Y-%m-%d %H:%M:%S UTC")
            if mt > MAC_EPOCH:
                result["Dimodifikasi"] = datetime.datetime.utcfromtimestamp(mt - MAC_EPOCH).strftime("%Y-%m-%d %H:%M:%S UTC")
            if ts and dur:
                sec = dur / ts
                result["Durasi"] = f"{int(sec // 60)}m {int(sec % 60)}s"
        except struct.error:
            pass

    # udta — user data (GPS, software, kamera, dll)
    up, usz, uh = _find_mp4_box(moov, 0, "udta")
    if up >= 0:
        udta = moov[up+uh:up+usz]
        for tag, label in [
            ("\xa9xyz", "GPS (\u00a9xyz)"),
            ("\xa9day", "Tanggal (\u00a9day)"),
            ("\xa9mak", "Pembuat (\u00a9mak)"),
            ("\xa9mod", "Model (\u00a9mod)"),
            ("\xa9swr", "Software (\u00a9swr)"),
            ("\xa9nam", "Nama (\u00a9nam)"),
            ("\xa9cmt", "Komentar (\u00a9cmt)"),
        ]:
            tag_b = tag.encode("latin-1")
            idx = udta.find(tag_b)
            if idx >= 0:
                chunk = udta[idx + len(tag_b) + 4:]  # skip box size (4 bytes)
                val = chunk[:128].decode("utf-8", errors="replace").strip("\x00").strip()
                if val:
                    result[label] = val

    return result

def banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(C + "=" * 33)
    print("          AZ-OSINT-TOOL")
    print("=" * 33 + W)
    print("[1]  Social Check")
    print("[2]  Metadata Check (file lokal)")
    print("[3]  Digital Footprint Check")
    print("[4]  Domain Intelligence")
    print("[5]  Email Intelligence")
    print(C + "-" * 33 + W)
    print("[6]  Numbers Intelligence (Indonesia)")
    print("[7]  IP Intelligence")
    print("[8]  Website Safety Checker")
    print("[9]  Website Style Grabber (HTML/CSS)")
    print("[10] School Info Grabber (NPSN)")
    print(C + "-" * 33 + W)
    print("[11] Subdomain Finder (crt.sh)")
    print("[12] Paste Site Intelligence")
    print("[13] Username Extended Check")
    print("[14] Reverse IP Lookup")
    print("[15] Google Dork Generator")
    print(C + "-" * 33 + W)
    print("[16] Shodan Intelligence")
    print("[17] URL Media Metadata (gambar/video)")
    print("[18] Geo-OSINT (Creepy-style)")
    print(C + "-" * 33 + W)
    print("[19] Domain Harvester (email & host)")
    print("[20] Wayback Machine CDX Recon")
    print("[21] ASN Intelligence (BGPView)")
    print("[22] DNS History & Zone Recon")
    print(C + "-" * 33 + W)
    print("[23] Plat Nomor Indonesia")
    print("[24] Image Geolocation (Gambar → Maps)")
    print("[0]  Exit")
    print("=" * 33)

def footprint():
    user = input("Username: ").strip().lstrip("@")
    if not user or "/" in user or any(c.isspace() for c in user):
        print(R + "Username tidak valid." + W)
        return

    print(Y + "\nMemeriksa profil publik...\n" + W)
    for name, template in SITES.items():
        url = template.format(user)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AZ-OSINT-Tool/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=7) as res:
                code = res.status
            print(G + f"[{code}] {name}: {url}" + W)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(R + f"[404] {name}: tidak ditemukan" + W)
            else:
                print(Y + f"[{e.code}] {name}: belum terverifikasi" + W)
        except Exception:
            print(Y + f"[?] {name}: gagal diperiksa" + W)
    print(Y + "\nCatatan: status HTTP bukan bukti pasti akun ada." + W)

def metadata():
    path = input("Path foto: ").strip().strip('"')
    file = Path(path).expanduser()
    if not file.is_file():
        print(R + "File tidak ditemukan." + W)
        return

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        with Image.open(file) as img:
            print(C + f"\nFile: {file.name}")
            print(f"Format: {img.format}")
            print(f"Ukuran: {img.size}")
            print(f"Mode: {img.mode}" + W)
            exif = img.getexif()
            if not exif:
                print(Y + "Metadata EXIF tidak tersedia." + W)
                return
            gps_found = False
            for key, value in exif.items():
                tag = TAGS.get(key, str(key))
                if tag == "GPSInfo":
                    gps_found = True
                    try:
                        value = {GPSTAGS.get(k, str(k)): v for k, v in value.items()}
                    except AttributeError:
                        pass
                print(f"{tag}: {value}")
            if not gps_found:
                print(Y + "Tidak ada GPS EXIF yang terbaca." + W)
    except ImportError:
        print(R + "Pillow belum terpasang. Jalankan: pip install Pillow" + W)
    except Exception as e:
        print(R + f"Gagal membaca metadata: {e}" + W)

def digital_footprint():
    keyword = input("Kata kunci (contoh: penipuan): ").strip()
    if not keyword:
        print(R + "Kata kunci tidak boleh kosong." + W)
        return

    print(Y + "\nMembuat pencarian jejak digital publik...\n" + W)
    print("Pilih sumber:")
    print("[1] Semua sumber")
    for i, name in enumerate(SEARCH_SOURCES, 2):
        print(f"[{i}] {name}")
    choice = input("Pilihan: ").strip()

    if choice == "1":
        sources = list(SEARCH_SOURCES.items())
    elif choice.isdigit() and 2 <= int(choice) < len(SEARCH_SOURCES) + 2:
        sources = [list(SEARCH_SOURCES.items())[int(choice) - 2]]
    else:
        print(R + "Pilihan tidak valid." + W)
        return

    for name, template in sources:
        url = template.format(quote_plus(keyword))
        print(C + f"\n[{name}]" + W)
        print(url)
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; AZ-OSINT-Tool/1.0)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as res:
                html = res.read().decode("utf-8", errors="ignore")
            parser = ResultParser()
            parser.feed(html)
            results = parser.results[:5]
            if results:
                for item in results:
                    print(G + "\n- " + item["title"].strip() + W)
                    print(item["url"])
                    if item.get("snippet"):
                        print(item["snippet"].strip())
            else:
                print(Y + "Hasil tidak terbaca otomatis; buka tautan di atas." + W)
        except Exception:
            print(Y + "Tidak bisa mengambil hasil otomatis; buka tautan di atas." + W)

    print(Y + "\nCatatan: hasil bergantung pada indeks mesin pencari. Konten privat, konten yang tidak terindeks, dan sebagian komentar mungkin tidak muncul." + W)

def email_intelligence():
    email = input("Email (contoh: contoh@gmail.com): ").strip()
    if (email.count("@") != 1 or any(ch.isspace() for ch in email)
            or "." not in email.rsplit("@", 1)[-1]
            or email.startswith("@") or email.endswith("@")):
        print(R + "Format email tidak valid." + W)
        return

    exact = f'"{email}"'
    searches = [
        ("Email Digital Footprint - Google", exact),
        ("Email Digital Footprint - Bing", exact),
        ("Public Document Search - PDF", f'{exact} filetype:pdf'),
        ("Public Document Search - DOC/DOCX", f'{exact} (filetype:doc OR filetype:docx)'),
        ("Public Document Search - XLS/XLSX/CSV", f'{exact} (filetype:xls OR filetype:xlsx OR filetype:csv)'),
        ("Public Document Search - TXT", f'{exact} filetype:txt'),
    ]

    print(Y + "\nPencarian email pada sumber publik\n" + W)
    print("Email dicari sebagai teks persis; hasil bisa tidak lengkap atau salah konteks.")
    for title, query in searches:
        encoded = quote_plus(query)
        if "Bing" in title:
            url = "https://www.bing.com/search?q=" + encoded
        else:
            url = "https://www.google.com/search?q=" + encoded
        print(C + "\n[" + title + "]" + W)
        print(url)

    print(C + "\n[Domain email]" + W)
    domain = email.rsplit("@", 1)[-1].lower()
    print("Domain:", domain)
    print("DNS/MX dapat diperiksa lewat Domain Intelligence dengan memasukkan:", domain)
    print(Y + "\nCatatan: fitur ini membuat tautan pencarian; tidak membuktikan pemilik email, keaktifan alamat, atau kebocoran data." + W)


def normalize_domain(value):
    value = value.strip()
    if not value:
        return None
    if "://" not in value:
        value = "//" + value
    host = urlparse(value).hostname
    if not host:
        return None
    try:
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    except UnicodeError:
        return None
    if len(host) > 253 or "." not in host:
        return None
    labels = host.split(".")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
           or not all(ch.isalnum() or ch == "-" for ch in label) for label in labels):
        return None
    return host


def fetch_json(url, accept="application/json", timeout=8):
    req = urllib.request.Request(url, headers={
        "User-Agent": "AZ-OSINT-Tool/1.0",
        "Accept": accept
    })
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def domain_rdap(domain):
    print(C + "\n[RDAP / Registrasi Domain]" + W)
    try:
        data = fetch_json("https://rdap.org/domain/" + quote_plus(domain),
                          "application/rdap+json")
        print("Domain:", data.get("ldhName", domain))
        print("Handle:", data.get("handle", "Tidak tersedia"))
        for event in data.get("events", []):
            action = event.get("eventAction", "")
            date = event.get("eventDate", "")
            if action and date:
                print(f"{action}: {date}")
        nameservers = [n.get("ldhName") for n in data.get("nameservers", []) if n.get("ldhName")]
        if nameservers:
            print("Nameservers:", ", ".join(nameservers))
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                name = entity.get("vcardArray", [])
                registrar = ""
                if len(name) > 1:
                    for item in name[1]:
                        if len(item) > 3 and item[0] == "fn":
                            registrar = str(item[3])
                            break
                print("Registrar:", registrar or entity.get("handle", "tercantum di RDAP"))
        print(G + "RDAP berhasil dibaca." + W)
    except urllib.error.HTTPError as e:
        print(Y + f"RDAP tidak tersedia (HTTP {e.code}); domain bisa saja memakai registry yang tidak merespons." + W)
    except Exception as e:
        print(Y + f"RDAP gagal diakses: {e}" + W)


def domain_dns(domain):
    print(C + "\n[DNS Records Publik]" + W)
    for record_type in ("A", "AAAA", "MX", "NS", "TXT", "CNAME"):
        query = urlencode({"name": domain, "type": record_type})
        try:
            data = fetch_json("https://cloudflare-dns.com/dns-query?" + query,
                              "application/dns-json")
            answers = data.get("Answer", [])
            if answers:
                print(G + record_type + ":" + W)
                for answer in answers[:8]:
                    print("  -", answer.get("data", ""), f"(TTL {answer.get('TTL', '?')})")
            else:
                print(Y + f"{record_type}: tidak ada record yang dikembalikan" + W)
        except Exception as e:
            print(Y + f"{record_type}: gagal diperiksa ({e})" + W)


def domain_tls(domain):
    print(C + "\n[HTTPS / Sertifikat TLS]" + W)
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=6) as raw:
            with context.wrap_socket(raw, server_hostname=domain) as conn:
                cert = conn.getpeercert()
                print("TLS:", conn.version() or "tidak diketahui")
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))
                print("Nama sertifikat:", subject.get("commonName", "Tidak tersedia"))
                print("Penerbit:", issuer.get("organizationName", issuer.get("commonName", "Tidak tersedia")))
                if cert.get("notBefore"):
                    print("Berlaku mulai:", cert["notBefore"])
                if cert.get("notAfter"):
                    print("Kedaluwarsa:", cert["notAfter"])
                sans = [name for kind, name in cert.get("subjectAltName", []) if kind == "DNS"]
                if sans:
                    print("SAN:", ", ".join(sans[:10]))
        print(G + "Koneksi HTTPS berhasil." + W)
    except Exception as e:
        print(Y + f"Tidak dapat membaca sertifikat HTTPS: {e}" + W)


def domain_intelligence():
    raw = input("Domain/URL (contoh: example.com): ")
    domain = normalize_domain(raw)
    if not domain:
        print(R + "Domain tidak valid. Masukkan nama domain, bukan alamat IP." + W)
        return

    print(Y + f"\nMemeriksa informasi publik untuk: {domain}\n" + W)
    domain_rdap(domain)
    domain_dns(domain)
    domain_tls(domain)
    print(C + "\n[Arsip Website]" + W)
    print("Wayback Machine:", f"https://web.archive.org/web/*/{domain}")
    print(Y + "\nCatatan: hasil bergantung pada data publik dan layanan yang tersedia. Ini bukan pemindaian kerentanan." + W)


def numbers_intelligence():
    raw = input("Nomor HP Indonesia (contoh 081234567890 / +6281234567890): ").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())

    if raw.startswith("+62") or raw.startswith("62"):
        national = digits[2:] if digits.startswith("62") else digits
        if national.startswith("0"):
            national = national[1:]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        print(R + "Gunakan format Indonesia: 08..., 628..., atau +628..." + W)
        return

    if not national.isdigit() or not 8 <= len(national) <= 12 or national.startswith("0"):
        print(R + "Format nomor tidak valid atau bukan nomor seluler Indonesia yang umum." + W)
        return

    e164 = "+62" + national
    local = "0" + national
    prefix = local[:4]

    # Prefix is indicative only; allocation and number portability can affect results.
    carriers = {
        "0811": "Telkomsel (perkiraan)", "0812": "Telkomsel (perkiraan)",
        "0813": "Telkomsel (perkiraan)", "0821": "Telkomsel (perkiraan)",
        "0822": "Telkomsel / by.U (perkiraan)", "0823": "Telkomsel (perkiraan)",
        "0851": "Telkomsel / by.U (perkiraan)",
        "0814": "Indosat (perkiraan)", "0815": "Indosat (perkiraan)",
        "0816": "Indosat (perkiraan)", "0855": "Indosat (perkiraan)",
        "0856": "Indosat (perkiraan)", "0857": "Indosat (perkiraan)",
        "0858": "Indosat (perkiraan)",
        "0817": "XL (perkiraan)", "0818": "XL (perkiraan)",
        "0819": "XL (perkiraan)", "0859": "XL (perkiraan)",
        "0877": "XL (perkiraan)", "0878": "XL (perkiraan)",
        "0831": "AXIS (perkiraan)", "0832": "AXIS (perkiraan)",
        "0833": "AXIS (perkiraan)", "0838": "AXIS (perkiraan)",
        "0895": "Tri / 3 (perkiraan)", "0896": "Tri / 3 (perkiraan)",
        "0897": "Tri / 3 (perkiraan)", "0898": "Tri / 3 (perkiraan)",
        "0899": "Tri / 3 (perkiraan)",
        "0881": "Smartfren (perkiraan)", "0882": "Smartfren (perkiraan)",
        "0883": "Smartfren (perkiraan)", "0884": "Smartfren (perkiraan)",
        "0885": "Smartfren (perkiraan)", "0886": "Smartfren (perkiraan)",
        "0887": "Smartfren (perkiraan)", "0888": "Smartfren (perkiraan)",
        "0889": "Smartfren (perkiraan)",
    }

    print(C + "\\n[Numbers Intelligence — Indonesia]" + W)
    print("Format internasional:", e164)
    print("Prefix lokal:", prefix)
    print("Operator berdasarkan prefix:", carriers.get(prefix, "Tidak diketahui dari daftar prefix lokal"))
    print(Y + "\\nPencarian jejak digital publik:" + W)

    query = quote_plus('"' + e164 + '" OR "' + local + '"')
    for name, url in (
        ("Google", "https://www.google.com/search?q=" + query),
        ("Bing", "https://www.bing.com/search?q=" + query),
    ):
        print(C + f"\\n[{name}]" + W)
        print(url)

    print(Y + "\\nCatatan: hasil operator hanya perkiraan dari prefix, bukan verifikasi pelanggan. Pencarian web hanya menampilkan konten publik yang terindeks. Fitur ini tidak melacak GPS, identitas pemilik, atau lokasi real-time." + W)


def ip_intelligence():
    raw = input("Alamat IP publik (IPv4/IPv6): ").strip()
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        print(R + "Format alamat IP tidak valid." + W)
        return

    if not address.is_global:
        print(Y + "IP privat/reserved tidak dicari melalui layanan publik." + W)
        return

    print(Y + "\nMengambil informasi IP publik...\n" + W)
    try:
        data = fetch_json("https://ipwho.is/" + quote_plus(str(address)))
        if not data.get("success", False):
            print(R + "Layanan tidak dapat memberikan data: " + str(data.get("message", "unknown error")) + W)
            return

        connection = data.get("connection") or {}
        timezone = data.get("timezone") or {}
        fields = (
            ("IP", data.get("ip")),
            ("Versi", data.get("type")),
            ("Negara", data.get("country")),
            ("Wilayah", data.get("region")),
            ("Kota perkiraan", data.get("city")),
            ("Kode pos", data.get("postal")),
            ("ISP", connection.get("isp")),
            ("Organisasi", connection.get("org")),
            ("ASN", connection.get("asn")),
            ("Zona waktu", timezone.get("id")),
            ("Koordinat perkiraan", (f"{data.get('latitude')}, {data.get('longitude')}"
                                     if data.get("latitude") is not None and data.get("longitude") is not None else None)),
        )
        for label, value in fields:
            if value not in (None, "", "Unknown"):
                print(f"{label}: {value}")
        if data.get("latitude") is not None and data.get("longitude") is not None:
            print("Peta:", f"https://www.google.com/maps?q={data['latitude']},{data['longitude']}")
    except Exception as e:
        print(R + f"Gagal mengambil data IP: {e}" + W)

    print(Y + "\nCatatan: lokasi IP hanya perkiraan jaringan/ISP, bukan lokasi GPS atau alamat rumah." + W)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def website_safety_checker():
    raw = input("URL website (contoh https://example.com): ").strip()
    if not raw:
        print(R + "URL tidak boleh kosong." + W)
        return
    if "://" not in raw:
        raw = "https://" + raw
    current = raw
    opener = urllib.request.build_opener(NoRedirect)
    response = None

    def public_host(url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False, "Hanya URL HTTP/HTTPS yang didukung."
        if parsed.username or parsed.password:
            return False, "URL dengan kredensial tertanam ditolak."
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            ips = {item[4][0] for item in infos}
            if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
                return False, "Host mengarah ke IP privat/lokal/reserved; pemeriksaan dibatalkan."
        except Exception as exc:
            return False, f"DNS gagal: {exc}"
        return True, ""

    print(Y + "\nMemeriksa indikator keamanan website...\n" + W)
    try:
        for hop in range(6):
            ok, reason = public_host(current)
            if not ok:
                print(R + reason + W)
                return
            req = urllib.request.Request(current, headers={"User-Agent": "Mozilla/5.0 (compatible; AZ-OSINT-Tool/1.0)", "Range": "bytes=0-499999"})
            try:
                response = opener.open(req, timeout=8)
                break
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    nxt = urllib.parse.urljoin(current, e.headers["Location"])
                    print(f"Redirect {e.code}: {current} -> {nxt}")
                    current = nxt
                    continue
                response = e
                break
        else:
            print(R + "Terlalu banyak redirect." + W)
            return

        status = getattr(response, "status", getattr(response, "code", "?"))
        headers = response.headers
        final_url = response.geturl()
        body = response.read(500000).decode("utf-8", errors="ignore") if hasattr(response, "read") else ""
        print("URL akhir:", final_url)
        print("HTTP status:", status)
        parsed = urlparse(final_url)
        if parsed.scheme == "https":
            print(G + "[OK] HTTPS digunakan (enkripsi koneksi)" + W)
        else:
            print(R + "[PERINGATAN] Website memakai HTTP tanpa enkripsi TLS" + W)

        checks = [
            ("Strict-Transport-Security", "HSTS"),
            ("Content-Security-Policy", "CSP"),
            ("X-Content-Type-Options", "X-Content-Type-Options"),
            ("X-Frame-Options", "X-Frame-Options"),
            ("Referrer-Policy", "Referrer-Policy"),
            ("Permissions-Policy", "Permissions-Policy"),
        ]
        print(C + "\n[Security headers]" + W)
        for header, label in checks:
            if headers.get(header):
                print(G + f"[ADA] {label}: {headers.get(header)[:180]}" + W)
            else:
                print(Y + f"[TIDAK TERLIHAT] {label}" + W)

        low = body.lower()
        indicators = [
            ("geolocation", "API geolokasi disebut dalam HTML yang diterima"),
            ("navigator.mediaDevices.getUserMedia", "API akses kamera/mikrofon disebut"),
            ("getusermedia", "API media lama disebut"),
            ("sendbeacon", "API pengiriman data sendBeacon disebut"),
            ("fetch(", "Pemanggilan fetch mungkin ada"),
            ("xmlhttprequest", "XMLHttpRequest mungkin disebut"),
        ]
        found = [(needle, label) for needle, label in indicators if needle in low]
        print(C + "\n[Indikator izin/perpindahan data pada HTML]" + W)
        if found:
            for _, label in found:
                print(Y + "[INDIKATOR] " + label + W)
        else:
            print("Tidak menemukan string indikator pada HTML awal yang diambil.")
        print(Y + "\nPENTING: indikator ini bukan bukti situs berbahaya. Kode JavaScript eksternal/dinamis mungkin tidak terbaca. HTTPS dan header yang lengkap juga tidak menjamin website aman." + W)
    except Exception as e:
        print(R + f"Gagal memeriksa website: {e}" + W)
    finally:
        try:
            if response:
                response.close()
        except Exception:
            pass


class StylesheetParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stylesheets = []
        self.in_style = False
        self.inline_css = []
        self._style_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "link" and "stylesheet" in attrs.get("rel", "").lower().split():
            href = attrs.get("href")
            if href:
                self.stylesheets.append(href)
        elif tag.lower() == "style":
            self.in_style = True
            self._style_parts = []

    def handle_data(self, data):
        if self.in_style:
            self._style_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "style" and self.in_style:
            self.inline_css.append("".join(self._style_parts))
            self.in_style = False
            self._style_parts = []


def fetch_public_resource(url, limit=2_000_000, max_redirects=5):
    """Fetch a public HTTP(S) resource with size and redirect checks."""
    opener = urllib.request.build_opener(NoRedirect)
    current = url
    for _ in range(max_redirects + 1):
        parsed = urlparse(current)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("URL HTTP/HTTPS publik tidak valid.")
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            ips = {item[4][0] for item in infos}
            if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
                raise ValueError("Host mengarah ke IP privat/lokal/reserved; dibatalkan.")
        except socket.gaierror as exc:
            raise ValueError(f"DNS gagal untuk {parsed.hostname}: {exc}") from exc

        req = urllib.request.Request(current, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AZ-OSINT-Tool/1.0)",
            "Range": f"bytes=0-{limit - 1}"
        })
        try:
            response = opener.open(req, timeout=10)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                current = urljoin(current, exc.headers["Location"])
                continue
            raise
        with response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError(f"Resource melebihi batas {limit} byte.")
            return current, response.headers.get("Content-Type", ""), data
    raise ValueError("Terlalu banyak redirect.")


def website_style_grabber():
    raw = input("URL website yang boleh kamu akses (contoh https://example.com): ").strip()
    if not raw:
        print(R + "URL tidak boleh kosong." + W)
        return
    if "://" not in raw:
        raw = "https://" + raw
    try:
        final_url, content_type, data = fetch_public_resource(raw, limit=2_000_000)
        html = data.decode("utf-8", errors="replace")
        if "html" not in content_type.lower() and "<html" not in html[:5000].lower() and "<!doctype" not in html[:5000].lower():
            print(Y + "Peringatan: respons tidak tampak seperti dokumen HTML." + W)

        host = urlparse(final_url).hostname or "website"
        safe_host = re.sub(r"[^A-Za-z0-9.-]", "_", host)
        out_dir = Path.cwd() / ("website_capture_" + safe_host)
        css_dir = out_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)

        parser = StylesheetParser()
        parser.feed(html)
        css_map = {}
        downloaded = 0
        for href in parser.stylesheets[:20]:
            css_url = urljoin(final_url, href)
            try:
                css_final_url, css_type, css_data = fetch_public_resource(css_url, limit=1_000_000)
                if "text/css" not in css_type.lower() and not css_final_url.lower().split("?", 1)[0].endswith(".css"):
                    print(Y + f"[SKIP] Bukan CSS yang dikenali: {css_url}" + W)
                    continue
                css_text = css_data.decode("utf-8", errors="replace")
                # Make relative CSS assets absolute so the saved stylesheet remains usable online.
                css_text = re.sub(
                    r'url\(\s*(["\']?)(?!data:|https?:|//|#)([^)"\']+)\1\s*\)',
                    lambda m: 'url(' + m.group(1) + urljoin(css_final_url, m.group(2).strip()) + m.group(1) + ')',
                    css_text, flags=re.I
                )
                filename = f"style_{downloaded + 1:02d}.css"
                (css_dir / filename).write_text(css_text, encoding="utf-8")
                css_map[href] = "css/" + filename
                downloaded += 1
                print(G + f"[OK] CSS: {css_url} -> {filename}" + W)
            except Exception as exc:
                print(Y + f"[SKIP] Gagal mengambil CSS {css_url}: {exc}" + W)

        # Point downloaded stylesheet links at local copies while preserving the rest of the HTML.
        link_re = re.compile(r"<link\b[^>]*>", re.I)
        href_re = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.I)
        rel_re = re.compile(r"\brel\s*=\s*([\"'])(.*?)\1", re.I)
        def replace_link(match):
            tag = match.group(0)
            rel = rel_re.search(tag)
            href = href_re.search(tag)
            if not rel or not href or "stylesheet" not in rel.group(2).lower().split():
                return tag
            local = css_map.get(href.group(2))
            if not local:
                return tag
            return tag[:href.start(2)] + local + tag[href.end(2):]
        html = link_re.sub(replace_link, html)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        if parser.inline_css:
            (out_dir / "inline_styles.css").write_text("\n\n".join(parser.inline_css), encoding="utf-8")

        print(G + "\n[SELESAI] Website HTML/CSS publik disimpan." + W)
        print("URL sumber:", final_url)
        print("HTML:", out_dir / "index.html")
        print("Folder CSS:", css_dir)
        print("CSS berhasil diunduh:", downloaded)
        if parser.inline_css:
            print("CSS inline juga diekstrak ke:", out_dir / "inline_styles.css")
        print(Y + "Catatan: JavaScript, gambar, font, dan konten dinamis tidak disalin sepenuhnya. Gunakan hanya untuk website milikmu atau yang kamu punya izin untuk arsipkan; hormati hak cipta dan ketentuan situs." + W)
    except Exception as exc:
        print(R + f"Gagal mengambil website: {exc}" + W)


class SchoolInfoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = False
        self.in_cell = False
        self.in_heading = False
        self.cell = ""
        self.row = []
        self.rows = []
        self.text_parts = []
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.title = True
        elif tag in ("th", "td"):
            self.in_cell = True
            self.cell = ""
        elif tag in ("h1", "h2", "h3"):
            self.in_heading = True
        elif tag == "tr":
            self.row = []

    def handle_data(self, data):
        value = " ".join(data.split())
        if not value:
            return
        self.text_parts.append(value)
        if self.title:
            self.headings.append(value)
        if self.in_cell:
            self.cell += (" " if self.cell else "") + value
        if self.in_heading:
            self.headings.append(value)

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = False
        elif tag in ("h1", "h2", "h3"):
            self.in_heading = False
        elif tag in ("th", "td"):
            self.in_cell = False
            self.row.append(self.cell.strip())
            self.cell = ""
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
                self.row = []


def school_info_grabber():
    npsn = input("Masukkan NPSN sekolah (8 karakter): ").strip().upper()
    if len(npsn) != 8 or not npsn.isalnum():
        print(R + "NPSN harus terdiri dari 8 karakter huruf/angka." + W)
        return

    url = "https://referensi.data.kemendikdasmen.go.id/pendidikan/npsn/" + quote_plus(npsn)
    print(Y + "\nMengambil informasi dari Data Referensi Pendidikan Kemendikdasmen..." + W)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AZ-OSINT-Tool/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            final_url = response.geturl()
            raw = response.read(2_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="replace")
        parser = SchoolInfoParser()
        parser.feed(html)

        visible = " ".join(parser.text_parts)
        if "NPSN TIDAK DITEMUKAN" in visible.upper() or not parser.rows:
            print(Y + "Data tidak berhasil dibaca otomatis dari halaman referensi." + W)
            print("Periksa NPSN di portal resmi:", "https://referensi.data.kemendikdasmen.go.id/")
            print("Halaman yang dicoba:", final_url)
            return

        print(G + "\n=== SCHOOL INFO ===" + W)
        print("NPSN:", npsn)
        shown = 0
        for row in parser.rows:
            cells = [re.sub(r"\s+", " ", c).strip() for c in row if c.strip()]
            if len(cells) >= 2:
                print(f"{cells[0]}: {' | '.join(cells[1:])}")
                shown += 1
            elif cells:
                print(cells[0])
                shown += 1
        if shown == 0:
            print(visible[:3500])
        print("\nSumber resmi:", final_url)
        print(Y + "Catatan: hanya data publik yang ditampilkan. Kelengkapan data bergantung pada portal sumber." + W)
        save = input("Simpan hasil ke file TXT? (y/n): ").strip().lower()
        if save == "y":
            out = Path(f"school_info_{npsn}.txt")
            lines = ["SCHOOL INFO", f"NPSN: {npsn}", f"Sumber: {final_url}", ""]
            for row in parser.rows:
                cells = [re.sub(r"\s+", " ", c).strip() for c in row if c.strip()]
                if cells:
                    lines.append((cells[0] + ": " + " | ".join(cells[1:])) if len(cells) > 1 else cells[0])
            out.write_text("\n".join(lines), encoding="utf-8")
            print(G + "Hasil disimpan:", out.resolve(), W)
    except urllib.error.HTTPError as exc:
        print(R + f"Portal merespons HTTP {exc.code}. Coba cek manual: https://referensi.data.kemendikdasmen.go.id/" + W)
    except Exception as exc:
        print(R + f"Gagal mengambil data: {exc}" + W)
        print("Portal resmi: https://referensi.data.kemendikdasmen.go.id/")

# ─────────────────────────────────────────────
# [11] SUBDOMAIN FINDER — crt.sh (Certificate Transparency)
# ─────────────────────────────────────────────
def subdomain_finder():
    raw = input("Domain target (contoh: example.com): ")
    domain = normalize_domain(raw)
    if not domain:
        print(R + "Domain tidak valid." + W)
        return

    url = f"https://crt.sh/?q=%.{quote_plus(domain)}&output=json"
    print(Y + f"\nMencari subdomain via Certificate Transparency (crt.sh)...\n" + W)
    req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8", errors="replace"))
        subdomains = set()
        for entry in data:
            for sub in entry.get("name_value", "").split("\n"):
                sub = sub.strip().lstrip("*.")
                if sub and sub.endswith(domain):
                    subdomains.add(sub.lower())
        if not subdomains:
            print(Y + "Tidak ada subdomain ditemukan di Certificate Transparency." + W)
            return
        print(G + f"Ditemukan {len(subdomains)} subdomain unik:\n" + W)
        for sub in sorted(subdomains):
            print(f"  {sub}")
        if input("\nSimpan ke file TXT? (y/n): ").strip().lower() == "y":
            out = Path(f"subdomains_{domain}.txt")
            out.write_text("\n".join(sorted(subdomains)), encoding="utf-8")
            print(G + "Disimpan:", out.resolve(), W)
    except Exception as e:
        print(R + f"Gagal mengambil data: {e}" + W)
    print(Y + "\nCatatan: hanya subdomain yang pernah punya sertifikat TLS publik yang muncul." + W)


# ─────────────────────────────────────────────
# [12] PASTE SITE INTELLIGENCE
# ─────────────────────────────────────────────
def paste_intelligence():
    keyword = input("Kata kunci / email / username: ").strip()
    if not keyword:
        print(R + "Kata kunci tidak boleh kosong." + W)
        return

    encoded = quote_plus(f'"{keyword}"')
    paste_searches = [
        ("Pastebin",    f"https://www.google.com/search?q={encoded}+site%3Apastebin.com"),
        ("Ghostbin",    f"https://www.google.com/search?q={encoded}+site%3Aghostbin.com"),
        ("Hastebin",    f"https://www.google.com/search?q={encoded}+site%3Ahastebin.com"),
        ("Pastes.io",   f"https://www.google.com/search?q={encoded}+site%3Apastes.io"),
        ("Paste.ee",    f"https://www.google.com/search?q={encoded}+site%3Apaste.ee"),
        ("Rentry.co",   f"https://www.google.com/search?q={encoded}+site%3Arentry.co"),
        ("Pasteio",     f"https://www.google.com/search?q={encoded}+site%3Apaste.io"),
        ("Controlc",    f"https://www.google.com/search?q={encoded}+site%3Acontrolc.com"),
    ]

    print(Y + f"\nMembuat tautan pencarian paste sites untuk: {keyword}\n" + W)
    for name, url in paste_searches:
        print(C + f"[{name}]" + W)
        print(url + "\n")
    print(Y + "Catatan: paste privat atau yang sudah dihapus tidak akan muncul. Buka tautan manual di browser." + W)


# ─────────────────────────────────────────────
# [13] USERNAME EXTENDED CHECK (20+ platform)
# ─────────────────────────────────────────────
SITES_EXTENDED = {
    "Twitter/X":    "https://x.com/{}",
    "LinkedIn":     "https://www.linkedin.com/in/{}/",
    "Facebook":     "https://www.facebook.com/{}",
    "Telegram":     "https://t.me/{}",
    "Snapchat":     "https://www.snapchat.com/add/{}",
    "Spotify":      "https://open.spotify.com/user/{}",
    "SoundCloud":   "https://soundcloud.com/{}",
    "Behance":      "https://www.behance.net/{}",
    "Dribbble":     "https://dribbble.com/{}",
    "Medium":       "https://medium.com/@{}",
    "Dev.to":       "https://dev.to/{}",
    "Keybase":      "https://keybase.io/{}",
    "HackerNews":   "https://news.ycombinator.com/user?id={}",
    "Steam":        "https://steamcommunity.com/id/{}",
    "Roblox":       "https://www.roblox.com/user.aspx?username={}",
    "Linktree":     "https://linktr.ee/{}",
    "Gravatar":     "https://gravatar.com/{}",
    "Fiverr":       "https://www.fiverr.com/{}",
    "Replit":       "https://replit.com/@{}",
    "Codecademy":   "https://www.codecademy.com/profiles/{}",
    "About.me":     "https://about.me/{}",
    "Carrd":        "https://{}.carrd.co",
}

def username_extended():
    user = input("Username: ").strip().lstrip("@")
    if not user or "/" in user or any(c.isspace() for c in user):
        print(R + "Username tidak valid." + W)
        return

    print(Y + f"\nMemeriksa {len(SITES_EXTENDED)} platform tambahan untuk: {user}\n" + W)
    found = 0
    for name, template in SITES_EXTENDED.items():
        url = template.format(user)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AZ-OSINT-Tool/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=7) as res:
                print(G + f"[{res.status}] {name}: {url}" + W)
                found += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(R + f"[404] {name}: tidak ditemukan" + W)
            else:
                print(Y + f"[{e.code}] {name}: belum terverifikasi" + W)
        except Exception:
            print(Y + f"[?]   {name}: gagal diperiksa" + W)

    print(Y + f"\n{found}/{len(SITES_EXTENDED)} platform merespons positif. Status HTTP bukan bukti pasti akun ada." + W)


# ─────────────────────────────────────────────
# [14] REVERSE IP LOOKUP
# ─────────────────────────────────────────────
def reverse_ip():
    raw = input("Domain atau IP (contoh: example.com / 93.184.216.34): ").strip()
    if not raw:
        print(R + "Input tidak boleh kosong." + W)
        return

    target_ip = None
    try:
        ipaddress.ip_address(raw)
        target_ip = raw
    except ValueError:
        domain = normalize_domain(raw)
        if not domain:
            print(R + "Input tidak valid." + W)
            return
        try:
            target_ip = socket.gethostbyname(domain)
            print(G + f"Domain '{domain}' → IP: {target_ip}" + W)
        except Exception as e:
            print(R + f"Gagal resolve DNS: {e}" + W)
            return

    if not ipaddress.ip_address(target_ip).is_global:
        print(R + "IP bukan alamat publik. Reverse lookup tidak berlaku." + W)
        return

    print(Y + f"\nMencari domain lain yang berbagi IP {target_ip}...\n" + W)

    url = f"https://api.hackertarget.com/reverseiplookup/?q={target_ip}"
    print(C + "[HackerTarget Reverse IP]" + W)
    req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            text = res.read().decode("utf-8", errors="replace").strip()
        if "error" in text.lower() or "API count" in text.lower():
            print(Y + "Batas API HackerTarget tercapai atau error:" + W)
            print(text[:300])
        else:
            domains = [d.strip() for d in text.splitlines() if d.strip()]
            print(G + f"Ditemukan {len(domains)} domain pada IP {target_ip}:\n" + W)
            for d in domains[:50]:
                print(f"  {d}")
            if len(domains) > 50:
                print(Y + f"  ... dan {len(domains) - 50} domain lainnya." + W)
            if input("\nSimpan ke file TXT? (y/n): ").strip().lower() == "y":
                out = Path(f"reverseip_{target_ip}.txt")
                out.write_text("\n".join(domains), encoding="utf-8")
                print(G + "Disimpan:", out.resolve(), W)
    except Exception as e:
        print(Y + f"Gagal mengambil data HackerTarget: {e}" + W)

    print(C + "\n[ViewDNS (manual browser)]" + W)
    print(f"https://viewdns.info/reverseip/?host={target_ip}&t=1")
    print(Y + "\nCatatan: shared hosting wajar punya banyak domain di satu IP; tidak berarti saling terhubung." + W)


# ─────────────────────────────────────────────
# [15] GOOGLE DORK GENERATOR
# ─────────────────────────────────────────────
DORK_TEMPLATES = {
    "1": ("File sensitif publik (PDF/DOC/XLS/CSV)",
          'site:{d} (filetype:pdf OR filetype:doc OR filetype:xls OR filetype:xlsx OR filetype:csv)'),
    "2": ("Login & panel admin",
          'site:{d} (inurl:login OR inurl:admin OR inurl:signin OR inurl:dashboard OR inurl:panel)'),
    "3": ("Direktori terbuka",
          'site:{d} intitle:"index of"'),
    "4": ("File konfigurasi & environment",
          'site:{d} (filetype:env OR filetype:cfg OR filetype:conf OR inurl:.env OR inurl:config)'),
    "5": ("Backup & database dump",
          'site:{d} (filetype:bak OR filetype:sql OR filetype:zip OR filetype:tar OR inurl:backup)'),
    "6": ("Error & stack trace bocor",
          'site:{d} (intext:"SQL syntax" OR intext:"Warning: mysql" OR intext:"stack trace" OR intext:"Fatal error")'),
    "7": ("Email & kontak publik",
          'site:{d} (intext:"@{d}" OR intext:"hubungi kami" OR intext:"contact us")'),
    "8": ("Semua kategori di atas", None),
}

def google_dork_generator():
    raw = input("Target domain (contoh: example.com): ")
    domain = normalize_domain(raw)
    if not domain:
        print(R + "Domain tidak valid." + W)
        return

    print(C + "\nPilih kategori dork:" + W)
    for key, (name, _) in DORK_TEMPLATES.items():
        print(f"[{key}] {name}")
    choice = input("Pilihan: ").strip()
    if choice not in DORK_TEMPLATES:
        print(R + "Pilihan tidak valid." + W)
        return

    if choice == "8":
        dorks = [(name, tmpl) for k, (name, tmpl) in DORK_TEMPLATES.items() if k != "8"]
    else:
        name, tmpl = DORK_TEMPLATES[choice]
        dorks = [(name, tmpl)]

    print(Y + f"\nGoogle Dork Generator — target: {domain}\n" + W)
    all_results = []
    for name, tmpl in dorks:
        query = tmpl.format(d=domain)
        url = "https://www.google.com/search?q=" + quote_plus(query)
        print(C + f"[{name}]" + W)
        print("Query :", query)
        print("Link  :", url)
        print()
        all_results.append((name, query, url))

    if input("Simpan semua dork ke TXT? (y/n): ").strip().lower() == "y":
        out = Path(f"dorks_{domain}.txt")
        lines = [f"Google Dork Report — {domain}", "=" * 40, ""]
        for name, query, url in all_results:
            lines += [f"[{name}]", f"Query : {query}", f"Link  : {url}", ""]
        out.write_text("\n".join(lines), encoding="utf-8")
        print(G + "Disimpan:", out.resolve(), W)

    print(Y + "\nCatatan: gunakan hanya untuk domain yang kamu miliki atau ada izin audit. Hasil bergantung pada indeks Google." + W)

# ─────────────────────────────────────────────
# [16] SHODAN INTELLIGENCE
# ─────────────────────────────────────────────
def shodan_intelligence():
    # SESUDAH (benar)
    api_key = os.environ.get("SHODAN_API_KEY", "").strip()
    if not api_key:
        print(Y + "Tip: set env var SHODAN_API_KEY agar tidak perlu input tiap kali." + W)
        api_key = input("Shodan API Key (gratis di shodan.io): ").strip()
    if not api_key:
        print(R + "API key tidak boleh kosong." + W)
        return

    raw = input("IP atau Domain target: ").strip()
    if not raw:
        print(R + "Input tidak boleh kosong." + W)
        return

    target_ip = None
    try:
        ipaddress.ip_address(raw)
        target_ip = raw
    except ValueError:
        domain = normalize_domain(raw)
        if not domain:
            print(R + "Input tidak valid." + W)
            return
        print(Y + f"Resolving '{domain}' via Shodan DNS..." + W)
        try:
            data = fetch_json(
                f"https://api.shodan.io/dns/resolve?hostnames={quote_plus(domain)}&key={api_key}"
            )
            target_ip = data.get(domain)
            if not target_ip:
                print(R + "Shodan tidak bisa resolve domain ini." + W)
                return
            print(G + f"  → {target_ip}" + W)
        except Exception as e:
            print(R + f"Gagal resolve via Shodan: {e}" + W)
            return

    print(Y + f"\nMengambil data Shodan untuk: {target_ip}\n" + W)
    try:
        data = fetch_json(
            f"https://api.shodan.io/shodan/host/{target_ip}?key={api_key}"
        )

        print(C + "[INFO UMUM]" + W)
        print(f"IP         : {data.get('ip_str', target_ip)}")
        hostnames  = data.get("hostnames", [])
        if hostnames:
            print(f"Hostname   : {', '.join(hostnames)}")
        print(f"Organisasi : {data.get('org', 'Tidak tersedia')}")
        print(f"ISP        : {data.get('isp', 'Tidak tersedia')}")
        print(f"ASN        : {data.get('asn', 'Tidak tersedia')}")
        print(f"OS         : {data.get('os', 'Tidak terdeteksi')}")
        print(f"Negara     : {data.get('country_name', '')} [{data.get('country_code', '')}]")
        city = data.get("city")
        if city:
            print(f"Kota       : {city}")
        lat_sh = data.get("latitude")
        lon_sh = data.get("longitude")
        if lat_sh and lon_sh:
            print(f"Koordinat  : {lat_sh}, {lon_sh}")
            print(f"  → Maps   : https://maps.google.com/?q={lat_sh},{lon_sh}")
        last_upd = data.get("last_update")
        if last_upd:
            print(f"Last seen  : {last_upd}")

        ports = sorted(data.get("ports", []))
        if ports:
            print(C + f"\n[OPEN PORTS ({len(ports)})]" + W)
            print("  " + "  ".join(str(p) for p in ports))

        services = data.get("data", [])
        if services:
            print(C + f"\n[SERVICES ({len(services)})]" + W)
            for svc in services[:15]:
                port      = svc.get("port", "?")
                transport = svc.get("transport", "tcp")
                product   = svc.get("product", "")
                version   = svc.get("version", "")
                banner    = svc.get("data", "").strip()[:120].replace("\n", " ")
                line = f"  {port}/{transport}"
                if product:
                    line += f"  {product}"
                if version:
                    line += f" {version}"
                print(G + line + W)
                if banner:
                    print(f"    Banner : {banner}")

        vulns = data.get("vulns", [])
        if vulns:
            print(C + f"\n[VULNERABILITIES ({len(vulns)})]" + W)
            for v in sorted(vulns)[:20]:
                print(Y + f"  {v}" + W)

        tags = data.get("tags", [])
        if tags:
            print(C + "\n[TAGS]" + W)
            print("  " + ", ".join(tags))

        if input("\nSimpan raw JSON? (y/n): ").strip().lower() == "y":
            out = Path(f"shodan_{target_ip.replace(':', '_')}.json")
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(G + "Disimpan:", out.resolve(), W)

    except urllib.error.HTTPError as e:
        msgs = {401: "API key tidak valid.", 404: "IP tidak ada di database Shodan.",
                429: "Rate limit tercapai. Tunggu beberapa menit."}
        print(R + msgs.get(e.code, f"HTTP error {e.code}.") + W)
    except Exception as e:
        print(R + f"Gagal: {e}" + W)

    print(C + f"\n[Shodan Web]" + W)
    print(f"https://www.shodan.io/host/{target_ip}")
    print(Y + "\nCatatan: free API key = 1 query credit/bulan untuk host lookup. Daftar di shodan.io." + W)


# ─────────────────────────────────────────────
# [17] URL MEDIA METADATA
#      Gambar: EXIF penuh via Pillow
#      Video : MP4/MOV container metadata (pure Python)
#      Social media post URL: auto-extract og:image / og:video dulu
#
#      CATATAN PENTING soal video:
#      - File MP4/MOV langsung (CDN, server sendiri): creation time, durasi, GPS ©xyz bisa ada
#      - Video dari TikTok/IG/YT yang sudah dihost: platform strip metadata,
#        yang tersisa hanya container info (duration, codec brand)
#      - Untuk analisis video penuh: ffprobe (ffmpeg) jauh lebih dalam
# ─────────────────────────────────────────────
def url_media_metadata():
    url = input("URL gambar / video / postingan media sosial: ").strip()
    if not url:
        print(R + "URL tidak boleh kosong." + W)
        return
    if "://" not in url:
        url = "https://" + url

    parsed_url = urlparse(url)
    domain     = (parsed_url.hostname or "").lower()

    VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".3gp", ".avi", ".mkv", ".webm")
    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp", ".heic")
    SOCIAL     = ("instagram.com", "tiktok.com", "twitter.com", "x.com",
                  "facebook.com", "reddit.com", "pinterest.com", "threads.net",
                  "youtube.com", "youtu.be")

    path_bare      = parsed_url.path.lower().split("?")[0]
    is_direct_img  = any(path_bare.endswith(e) for e in IMAGE_EXTS)
    is_direct_vid  = any(path_bare.endswith(e) for e in VIDEO_EXTS)
    is_social_post = any(d in domain for d in SOCIAL) and not (is_direct_img or is_direct_vid)

    media_url  = url
    type_hint  = None

    if is_social_post:
        print(Y + "\nURL terdeteksi sebagai postingan — mengekstrak og:image/og:video...\n" + W)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; facebookexternalhit/1.1)"
        })
        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                html = res.read(600_000).decode("utf-8", errors="ignore")

            og_vid = re.search(
                r'<meta[^>]+property=["\']og:video(?::url)?["\'][^>]+content=["\'](https?://[^"\']+)["\']',
                html, re.I
            )
            og_img = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
                html, re.I
            )
            if og_vid:
                media_url = og_vid.group(1)
                type_hint = "video"
                print(G + f"[og:video] {media_url}" + W)
            elif og_img:
                media_url = og_img.group(1)
                type_hint = "image"
                print(G + f"[og:image] {media_url}" + W)
            else:
                print(Y + "og:image/og:video tidak ditemukan. Mencoba URL langsung." + W)
        except Exception as e:
            print(Y + f"Gagal ambil halaman: {e}. Lanjut ke URL langsung." + W)
    elif is_direct_img:
        type_hint = "image"
    elif is_direct_vid:
        type_hint = "video"

    LIMIT = 12 * 1024 * 1024  # 12 MB
    print(Y + f"\nMengunduh media ({LIMIT // 1024 // 1024}MB maks)...\n" + W)
    req = urllib.request.Request(media_url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AZ-OSINT-Tool/1.0)",
        "Range"     : f"bytes=0-{LIMIT - 1}"
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            ct   = res.headers.get("Content-Type", "").lower()
            clen = res.headers.get("Content-Length", "?")
            data = res.read(LIMIT)

        print(C + "[HTTP Info]" + W)
        print(f"Content-Type   : {ct}")
        print(f"Content-Length : {clen} bytes")
        print(f"Diunduh        : {len(data):,} bytes")

        if type_hint is None:
            if "video" in ct:
                type_hint = "video"
            elif "image" in ct:
                type_hint = "image"

        # ── IMAGE ──
        if type_hint == "image" or ("image" in ct and type_hint != "video"):
            print(C + "\n[Metadata Gambar / EXIF]" + W)
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS, GPSTAGS
                with Image.open(io.BytesIO(data)) as img:
                    print(f"Format  : {img.format}")
                    print(f"Ukuran  : {img.size[0]}×{img.size[1]} px")
                    print(f"Mode    : {img.mode}")
                    exif = img.getexif()
                    if not exif:
                        print(Y + "Tidak ada EXIF — platform kemungkinan sudah strip metadata." + W)
                    else:
                        lat_e = lon_e = None
                        for key, val in exif.items():
                            tag = TAGS.get(key, str(key))
                            if tag == "GPSInfo":
                                try:
                                    gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                                    lat_e = _gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
                                    lon_e = _gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))
                                    print(f"GPSInfo : {gps}")
                                except Exception:
                                    print(f"GPSInfo : {val}")
                            else:
                                if isinstance(val, bytes):
                                    val = val[:60]
                                print(f"{tag}: {val}")

                        if lat_e is not None and lon_e is not None:
                            print(G + f"\n[GPS Terdeteksi]" + W)
                            print(f"Koordinat   : {lat_e:.6f}, {lon_e:.6f}")
                            print(f"Google Maps : https://maps.google.com/?q={lat_e},{lon_e}")
                            print(f"OSM         : https://www.openstreetmap.org/?mlat={lat_e}&mlon={lon_e}")
            except ImportError:
                print(R + "Pillow belum terpasang. pip install Pillow" + W)
            except Exception as e:
                print(R + f"Gagal baca metadata gambar: {e}" + W)

        # ── VIDEO ──
        elif type_hint == "video" or "video" in ct:
            print(C + "\n[Metadata Video]" + W)
            is_mp4 = len(data) >= 8 and data[4:8] in (b"ftyp", b"moov", b"free", b"mdat")
            if not is_mp4:
                # try finding ftyp anywhere in first 64 bytes
                is_mp4 = b"ftyp" in data[:64]

            if not is_mp4:
                print(Y + "Format tidak terdeteksi sebagai MP4/MOV dari data awal yang diunduh." + W)
                print(Y + "Untuk analisis mendalam gunakan: ffprobe -v quiet -print_format json -show_format -show_streams <url>" + W)
            else:
                meta = parse_mp4_metadata(data)
                if meta:
                    for k, v in meta.items():
                        if "GPS" in k:
                            print(G + f"{k}: {v}" + W)
                            gm = re.match(r"([+-]?\d+\.?\d*)([+-]\d+\.?\d*)", str(v))
                            if gm:
                                glat, glon = float(gm.group(1)), float(gm.group(2))
                                print(f"  → Google Maps: https://maps.google.com/?q={glat},{glon}")
                        else:
                            print(f"{k}: {v}")
                else:
                    print(Y + "Metadata minimal — kemungkinan platform sudah strip, atau moov box ada di akhir file (perlu unduh penuh)." + W)

            print(C + "\n[Analisis Lanjutan]" + W)
            print(f'ffprobe -v quiet -print_format json -show_format -show_streams "{media_url}"')

        else:
            print(Y + f"Tipe media tidak dikenali dari Content-Type: {ct}" + W)

        print(Y + "\nCatatan penting: Instagram, TikTok, Twitter, YouTube hampir selalu strip EXIF dan GPS dari media yang sudah dihost. Metadata hanya tersedia di file original sebelum upload." + W)

    except urllib.error.HTTPError as e:
        print(R + f"HTTP {e.code} — media tidak bisa diakses." + W)
        if e.code in (401, 403):
            print(Y + "Platform memblokir akses langsung; media memerlukan sesi login atau CDN token." + W)
    except Exception as e:
        print(R + f"Gagal: {e}" + W)


# ─────────────────────────────────────────────
# [18] GEO-OSINT (Creepy-style)
#      Input: koordinat manual, file lokal, atau URL gambar
#      Output: peta, reverse geocoding, OSINT search links
# ─────────────────────────────────────────────
def geo_osint():
    print(C + "\nGeo-OSINT — Pilih sumber koordinat:" + W)
    print("[1] Input koordinat manual (lat, lon)")
    print("[2] Ekstrak GPS dari file gambar lokal")
    print("[3] Ekstrak GPS dari URL gambar")
    mode = input("Pilihan: ").strip()

    lat = lon = None

    if mode == "1":
        raw = input("Koordinat (contoh: -6.2000, 106.8167): ").strip()
        parts = re.split(r"[,\s]+", raw.replace("°", ""))
        if len(parts) < 2:
            print(R + "Format tidak valid. Gunakan: lat, lon" + W)
            return
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            print(R + "Koordinat bukan angka." + W)
            return

    elif mode == "2":
        path = input("Path file gambar: ").strip().strip('"')
        file = Path(path).expanduser()
        if not file.is_file():
            print(R + "File tidak ditemukan." + W)
            return
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            with Image.open(file) as img:
                exif = img.getexif()
            if not exif:
                print(Y + "Tidak ada EXIF di file ini." + W)
                return
            for key, val in exif.items():
                if TAGS.get(key) == "GPSInfo":
                    gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                    lat = _gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
                    lon = _gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))
                    break
            if lat is None:
                print(Y + "Tidak ada GPS EXIF di file ini." + W)
                return
        except ImportError:
            print(R + "Pillow belum terpasang. pip install Pillow" + W)
            return
        except Exception as e:
            print(R + f"Gagal: {e}" + W)
            return

    elif mode == "3":
        img_url = input("URL gambar: ").strip()
        if not img_url:
            print(R + "URL tidak boleh kosong." + W)
            return
        if "://" not in img_url:
            img_url = "https://" + img_url
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            req = urllib.request.Request(img_url, headers={
                "User-Agent": "Mozilla/5.0 AZ-OSINT-Tool/1.0"
            })
            with urllib.request.urlopen(req, timeout=15) as res:
                data = res.read(6_000_000)
            with Image.open(io.BytesIO(data)) as img:
                exif = img.getexif()
            if not exif:
                print(Y + "Tidak ada EXIF — kemungkinan platform sudah strip metadata." + W)
                return
            for key, val in exif.items():
                if TAGS.get(key) == "GPSInfo":
                    gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                    lat = _gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
                    lon = _gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))
                    break
            if lat is None:
                print(Y + "Tidak ada GPS EXIF di gambar ini." + W)
                return
        except ImportError:
            print(R + "Pillow belum terpasang. pip install Pillow" + W)
            return
        except Exception as e:
            print(R + f"Gagal: {e}" + W)
            return
    else:
        print(R + "Pilihan tidak valid." + W)
        return

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        print(R + "Koordinat di luar range valid." + W)
        return

    print(C + f"\n[Koordinat]" + W)
    print(f"Decimal  : {lat:.6f}, {lon:.6f}")
    print(f"DMS      : {_dec_to_dms(lat, 'lat')}  {_dec_to_dms(lon, 'lon')}")

    print(C + "\n[Peta Langsung]" + W)
    print(f"Google Maps      : https://maps.google.com/?q={lat},{lon}")
    print(f"Google Street    : https://www.google.com/maps/@{lat},{lon},3a,90y,0h,90t/data=!3m1!1e3")
    print(f"Google Satellite : https://www.google.com/maps/@{lat},{lon},18z/data=!3m1!1e3")
    print(f"OpenStreetMap    : https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16")
    print(f"Bing Maps        : https://www.bing.com/maps?cp={lat}~{lon}&lvl=18")
    print(f"Yandex Maps      : https://maps.yandex.com/?ll={lon},{lat}&z=17")
    print(f"Wikimapia        : https://wikimapia.org/#lat={lat}&lon={lon}&z=16")

    print(C + "\n[Reverse Geocoding — Nominatim/OSM]" + W)
    try:
        geo_url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json&addressdetails=1"
        )
        req = urllib.request.Request(geo_url, headers={
            "User-Agent": "AZ-OSINT-Tool/1.0 (osint research)"
        })
        with urllib.request.urlopen(req, timeout=10) as res:
            geo = json.loads(res.read().decode("utf-8"))

        print(f"Alamat : {geo.get('display_name', 'Tidak tersedia')}")
        addr = geo.get("address", {})
        for field in ("road", "suburb", "village", "city", "regency",
                      "state", "country", "postcode"):
            val = addr.get(field)
            if val:
                print(f"  {field.capitalize():<12}: {val}")
    except Exception as e:
        print(Y + f"Reverse geocoding gagal: {e}" + W)

    coord_str = f"{lat:.5f},{lon:.5f}"
    print(C + "\n[OSINT Search Links]" + W)
    print(f"Google Images  : https://www.google.com/search?q={quote_plus(coord_str)}&tbm=isch")
    print(f"Google News    : https://news.google.com/search?q={quote_plus(coord_str)}")
    print(f"Twitter/X      : https://x.com/search?q={quote_plus(coord_str)}")
    print(f"Flickr Geo     : https://www.flickr.com/map/?fLat={lat}&fLon={lon}&zl=14")
    print(f"Bing Aerial    : https://www.bing.com/maps?cp={lat}~{lon}&lvl=19&style=a")
    print(f"Google Earth   : https://earth.google.com/web/@{lat},{lon},0a,500d,35y,0h,45t,0r")

    if input("\nSimpan hasil ke TXT? (y/n): ").strip().lower() == "y":
        out = Path(f"geo_osint_{lat:.4f}_{lon:.4f}.txt".replace("-", "S").replace(".", "d"))
        lines = [
            "Geo-OSINT Report", "=" * 40,
            f"Koordinat: {lat:.6f}, {lon:.6f}",
            f"DMS: {_dec_to_dms(lat, 'lat')}  {_dec_to_dms(lon, 'lon')}",
            "",
            "Google Maps: " + f"https://maps.google.com/?q={lat},{lon}",
            "OSM: " + f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")
        print(G + "Disimpan:", out.resolve(), W)

    print(Y + "\nCatatan: platform media sosial hampir selalu strip GPS sebelum host. Koordinat hanya ada di file original." + W)

# ─────────────────────────────────────────────
# [19] DOMAIN HARVESTER (theHarvester-style)
#      Email, host, dan endpoint publik dari satu domain
#      Sumber: crt.sh email SAN, HackerTarget hostsearch, Google dork
# ─────────────────────────────────────────────
def domain_harvester():
    raw = input("Domain target (contoh: example.com): ")
    domain = normalize_domain(raw)
    if not domain:
        print(R + "Domain tidak valid." + W)
        return

    emails_found = set()
    hosts_found  = set()

    # ── 1. crt.sh — email dari Subject Alternative Name sertifikat ──
    print(Y + f"\n[1/3] crt.sh — mencari email & host di sertifikat TLS...\n" + W)
    try:
        url = f"https://crt.sh/?q={quote_plus(domain)}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            certs = json.loads(res.read().decode("utf-8", errors="replace"))
        for entry in certs:
            name_val = entry.get("name_value", "")
            for part in name_val.split("\n"):
                part = part.strip()
                if "@" in part and "." in part.split("@")[-1]:
                    emails_found.add(part.lower())
                elif part.endswith(domain) or part.lstrip("*.").endswith(domain):
                    hosts_found.add(part.lstrip("*.").lower())
        print(G + f"  Ditemukan: {len(emails_found)} email, {len(hosts_found)} host" + W)
    except Exception as e:
        print(Y + f"  crt.sh gagal: {e}" + W)

    # ── 2. HackerTarget hostsearch ──
    print(Y + "\n[2/3] HackerTarget hostsearch...\n" + W)
    try:
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
        with urllib.request.urlopen(req, timeout=12) as res:
            text = res.read().decode("utf-8", errors="replace").strip()
        if "error" not in text.lower() and "API" not in text:
            before = len(hosts_found)
            for line in text.splitlines():
                parts = line.split(",")
                if parts:
                    hosts_found.add(parts[0].strip().lower())
            print(G + f"  +{len(hosts_found) - before} host baru dari HackerTarget" + W)
        else:
            print(Y + f"  HackerTarget: {text[:150]}" + W)
    except Exception as e:
        print(Y + f"  HackerTarget gagal: {e}" + W)

    # ── 3. Google dork links untuk email harvest manual ──
    print(Y + "\n[3/3] Google dork links untuk email harvesting manual:\n" + W)
    dorks = [
        ("Email @domain di web publik",
         f'site:{domain} intext:"@{domain}"'),
        ("Email di dokumen PDF/DOC",
         f'"@{domain}" (filetype:pdf OR filetype:doc OR filetype:xlsx)'),
        ("Email di GitHub publik",
         f'"@{domain}" site:github.com'),
        ("Email di LinkedIn publik",
         f'"@{domain}" site:linkedin.com'),
        ("Email di Pastebin",
         f'"@{domain}" site:pastebin.com'),
    ]
    for name, query in dorks:
        url = "https://www.google.com/search?q=" + quote_plus(query)
        print(C + f"[{name}]" + W)
        print(url)

    # ── Output ──
    print(C + f"\n[Hasil: {len(emails_found)} Email]" + W)
    for e in sorted(emails_found):
        print(G + f"  {e}" + W)

    print(C + f"\n[Hasil: {len(hosts_found)} Host/Subdomain]" + W)
    for h in sorted(hosts_found)[:60]:
        print(f"  {h}")
    if len(hosts_found) > 60:
        print(Y + f"  ... dan {len(hosts_found) - 60} lainnya" + W)

    if (emails_found or hosts_found) and input("\nSimpan ke TXT? (y/n): ").strip().lower() == "y":
        out = Path(f"harvest_{domain}.txt")
        lines = [f"Domain Harvest — {domain}", "=" * 40, ""]
        if emails_found:
            lines += ["[EMAIL]"] + sorted(emails_found) + [""]
        if hosts_found:
            lines += ["[HOST/SUBDOMAIN]"] + sorted(hosts_found) + [""]
        out.write_text("\n".join(lines), encoding="utf-8")
        print(G + "Disimpan:", out.resolve(), W)

    print(Y + "\nCatatan: hasil hanya dari sumber publik. Email dari crt.sh adalah email pemilik sertifikat, bukan email umum domain." + W)


# ─────────────────────────────────────────────
# [20] WAYBACK MACHINE CDX RECON
#      Cari URL historis yang pernah diindeks Wayback
#      Berguna untuk menemukan endpoint lama, backup, API path
# ─────────────────────────────────────────────
WAYBACK_FILTERS = {
    "1": ("Semua URL",              "",                         ""),
    "2": ("API endpoints (JSON)",   "application/json",         "mimetype"),
    "3": ("File PHP",               ".php",                     "urlkey"),
    "4": ("File backup & dump",     r"\.sql|\.bak|\.zip|\.tar", "urlkey"),
    "5": ("File konfigurasi",       r"\.env|\.cfg|\.conf|\.ini","urlkey"),
    "6": ("File dokumen",           r"\.pdf|\.doc|\.xls",       "urlkey"),
    "7": ("Login & admin pages",    r"login|admin|panel|signin","urlkey"),
}

def wayback_cdx_recon():
    raw = input("Domain target (contoh: example.com): ")
    domain = normalize_domain(raw)
    if not domain:
        print(R + "Domain tidak valid." + W)
        return

    print(C + "\nPilih filter:" + W)
    for k, (name, _, _) in WAYBACK_FILTERS.items():
        print(f"[{k}] {name}")
    choice = input("Pilihan: ").strip()
    if choice not in WAYBACK_FILTERS:
        print(R + "Pilihan tidak valid." + W)
        return

    filter_name, filter_val, filter_type = WAYBACK_FILTERS[choice]

    limit = input("Jumlah hasil maks (default 200): ").strip()
    limit = limit if limit.isdigit() and 1 <= int(limit) <= 5000 else "200"

    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=*.{domain}/*"
        f"&output=json"
        f"&limit={limit}"
        f"&fl=original,statuscode,timestamp,mimetype"
        f"&collapse=urlkey"
    )
    if filter_val:
        if filter_type == "mimetype":
            cdx_url += f"&filter=mimetype:{filter_val}"
        elif filter_type == "urlkey":
            cdx_url += f"&filter=urlkey:{filter_val}"

    print(Y + f"\nQuery CDX Wayback Machine — {filter_name}...\n" + W)
    print("Query:", cdx_url[:100] + "...")

    try:
        req = urllib.request.Request(cdx_url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
        with urllib.request.urlopen(req, timeout=30) as res:
            raw_data = json.loads(res.read().decode("utf-8", errors="replace"))

        if not raw_data or len(raw_data) <= 1:
            print(Y + "Tidak ada hasil dari CDX API." + W)
            return

        headers = raw_data[0]
        rows    = raw_data[1:]
        print(G + f"Ditemukan {len(rows)} URL historis:\n" + W)

        results = []
        for row in rows:
            entry = dict(zip(headers, row))
            url_orig   = entry.get("original", "")
            status     = entry.get("statuscode", "?")
            ts         = entry.get("timestamp", "")
            mime       = entry.get("mimetype", "")
            date_str   = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts
            wayback_lnk = f"https://web.archive.org/web/{ts}/{url_orig}" if ts else ""
            results.append((status, date_str, mime, url_orig, wayback_lnk))
            flag = ""
            if any(x in url_orig.lower() for x in ("password", "secret", "token", "key", "backup", "admin")):
                flag = G + " ← MENARIK" + W
            print(f"[{status}] {date_str} | {mime[:25]:<25} | {url_orig[:80]}{flag}")

        if input("\nSimpan ke TXT? (y/n): ").strip().lower() == "y":
            out = Path(f"wayback_{domain}_{choice}.txt")
            lines = [f"Wayback CDX Recon — {domain} — {filter_name}", "=" * 60, ""]
            for status, date, mime, url_o, wb in results:
                lines.append(f"[{status}] {date} | {mime} | {url_o}")
                if wb:
                    lines.append(f"  Wayback: {wb}")
            out.write_text("\n".join(lines), encoding="utf-8")
            print(G + "Disimpan:", out.resolve(), W)

    except Exception as e:
        print(R + f"CDX API gagal: {e}" + W)

    print(C + "\n[Wayback Manual]" + W)
    print(f"https://web.archive.org/web/*/{domain}")
    print(Y + "\nCatatan: CDX API hanya menampilkan URL yang pernah diindeks Wayback. URL yang tidak pernah di-crawl tidak akan muncul." + W)


# ─────────────────────────────────────────────
# [21] ASN INTELLIGENCE (BGPView)
#      Cari semua IP range milik satu organisasi
#      Berguna untuk scope pentest & asset discovery
#      API gratis — tidak perlu API key
# ─────────────────────────────────────────────
def asn_intelligence():
    print(C + "\nASN Intelligence — Pilih input:" + W)
    print("[1] Nomor ASN (contoh: AS13335)")
    print("[2] Nama organisasi (contoh: Cloudflare)")
    print("[3] Alamat IP (cari ASN dari IP)")
    mode = input("Pilihan: ").strip()

    BASE = "https://api.bgpview.io"

    if mode == "1":
        raw = input("ASN (contoh: AS13335 atau 13335): ").strip().upper().lstrip("AS")
        if not raw.isdigit():
            print(R + "Format ASN tidak valid." + W)
            return
        asn = raw
        print(Y + f"\nMengambil info ASN {asn}...\n" + W)
        try:
            data = fetch_json(f"{BASE}/asn/{asn}")
            info = data.get("data", {})
            print(C + "[Info ASN]" + W)
            print(f"ASN         : AS{info.get('asn')}")
            print(f"Nama        : {info.get('name', 'Tidak tersedia')}")
            print(f"Deskripsi   : {info.get('description_short', '')}")
            print(f"Negara      : {info.get('country_code', '')}")
            print(f"Website     : {info.get('website', '')}")
            print(f"RIR         : {info.get('rir_allocation', {}).get('rir_name', '')}")

            # IP prefixes
            pfx_data = fetch_json(f"{BASE}/asn/{asn}/prefixes")
            v4 = pfx_data.get("data", {}).get("ipv4_prefixes", [])
            v6 = pfx_data.get("data", {}).get("ipv6_prefixes", [])

            if v4:
                print(C + f"\n[IPv4 Prefixes ({len(v4)})]" + W)
                for p in v4[:30]:
                    print(f"  {p.get('prefix', '')}  — {p.get('name', '')} ({p.get('description', '')})")
                if len(v4) > 30:
                    print(Y + f"  ... dan {len(v4) - 30} prefix lainnya." + W)
            if v6:
                print(C + f"\n[IPv6 Prefixes ({len(v6)})]" + W)
                for p in v6[:10]:
                    print(f"  {p.get('prefix', '')}")

            # Peers
            peer_data = fetch_json(f"{BASE}/asn/{asn}/peers")
            peers_v4 = peer_data.get("data", {}).get("ipv4_peers", [])
            if peers_v4:
                print(C + f"\n[BGP Peers ({len(peers_v4)})]" + W)
                for p in peers_v4[:10]:
                    print(f"  AS{p.get('asn')} — {p.get('name', '')}")

            if v4 and input("\nSimpan prefix ke TXT? (y/n): ").strip().lower() == "y":
                out = Path(f"asn_{asn}_prefixes.txt")
                lines = [f"ASN{asn} IP Prefixes", "=" * 40, ""]
                lines += [p.get("prefix", "") for p in v4]
                out.write_text("\n".join(lines), encoding="utf-8")
                print(G + "Disimpan:", out.resolve(), W)

        except Exception as e:
            print(R + f"Gagal: {e}" + W)

    elif mode == "2":
        keyword = input("Nama organisasi: ").strip()
        if not keyword:
            print(R + "Nama tidak boleh kosong." + W)
            return
        print(Y + f"\nMencari ASN untuk: {keyword}\n" + W)
        try:
            data = fetch_json(f"{BASE}/search?query_term={quote_plus(keyword)}")
            results = data.get("data", {}).get("asns", [])
            if not results:
                print(Y + "Tidak ditemukan. Coba kata kunci yang lebih spesifik." + W)
                return
            print(G + f"Ditemukan {len(results)} ASN:\n" + W)
            for item in results[:20]:
                print(f"  AS{item.get('asn'):<8} | {item.get('name', ''):<30} | {item.get('country_code', '')} | {item.get('description', '')}")
            print(Y + "\nMasukkan nomor ASN ke mode [1] untuk detail lengkap." + W)
        except Exception as e:
            print(R + f"Gagal: {e}" + W)

    elif mode == "3":
        raw = input("Alamat IP: ").strip()
        try:
            ipaddress.ip_address(raw)
        except ValueError:
            print(R + "IP tidak valid." + W)
            return
        print(Y + f"\nMencari ASN untuk IP {raw}...\n" + W)
        try:
            data = fetch_json(f"{BASE}/ip/{raw}")
            info = data.get("data", {})
            print(C + "[Info IP]" + W)
            print(f"IP          : {info.get('ip', raw)}")
            print(f"RIR         : {info.get('rir_allocation', {}).get('rir_name', '')}")
            print(f"Alokasi     : {info.get('rir_allocation', {}).get('prefix', '')}")
            for p in info.get("prefixes", [])[:5]:
                print(C + "\n[Prefix]" + W)
                print(f"  Prefix   : {p.get('prefix', '')}")
                print(f"  Nama     : {p.get('name', '')}")
                print(f"  Desc     : {p.get('description', '')}")
                asns = p.get("asns", [])
                for a in asns:
                    print(f"  ASN      : AS{a.get('asn')} — {a.get('name', '')}")
        except Exception as e:
            print(R + f"Gagal: {e}" + W)
    else:
        print(R + "Pilihan tidak valid." + W)
        return

    print(C + "\n[BGPView Web]" + W)
    print("https://bgpview.io")
    print(Y + "\nCatatan: data BGP adalah routing publik. IP prefix = range yang di-advertise ke internet, bukan selalu range aktif semua digunakan." + W)


# ─────────────────────────────────────────────
# [22] DNS HISTORY & ZONE RECON (HackerTarget)
#      DNS records, zone transfer test, reverse DNS,
#      shared hosting check — semua gratis tanpa API key
# ─────────────────────────────────────────────
def dns_history_recon():
    raw = input("Domain atau IP (contoh: example.com / 93.184.216.34): ").strip()
    if not raw:
        print(R + "Input tidak boleh kosong." + W)
        return

    # Tentukan mode: domain atau IP
    is_ip = False
    try:
        ipaddress.ip_address(raw)
        is_ip = True
        target = raw
    except ValueError:
        target = normalize_domain(raw)
        if not target:
            print(R + "Input tidak valid." + W)
            return

    BASE = "https://api.hackertarget.com"

    if not is_ip:
        # ── DNS Lookup (A, MX, NS, TXT) ──
        print(Y + f"\n[1/4] DNS Lookup — {target}...\n" + W)
        try:
            url = f"{BASE}/dnslookup/?q={target}"
            req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                text = res.read().decode("utf-8", errors="replace").strip()
            if "error" not in text.lower():
                print(text)
            else:
                print(Y + text[:200] + W)
        except Exception as e:
            print(Y + f"Gagal: {e}" + W)

        # ── Zone Transfer Test ──
        print(Y + f"\n[2/4] Zone Transfer Test — {target}...\n" + W)
        try:
            url = f"{BASE}/zonetransfer/?q={target}"
            req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                text = res.read().decode("utf-8", errors="replace").strip()
            if "failed" in text.lower() or "refused" in text.lower():
                print(G + "Zone transfer ditolak — konfigurasi DNS aman." + W)
                print(text[:300])
            elif "error" in text.lower() or "API" in text:
                print(Y + text[:200] + W)
            else:
                print(R + "Zone transfer BERHASIL — ini adalah temuan kritis!" + W)
                print(text[:2000])
        except Exception as e:
            print(Y + f"Gagal: {e}" + W)

        # ── Host Search (subdomain dari same domain) ──
        print(Y + f"\n[3/4] Host Search — {target}...\n" + W)
        try:
            url = f"{BASE}/hostsearch/?q={target}"
            req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
            with urllib.request.urlopen(req, timeout=12) as res:
                text = res.read().decode("utf-8", errors="replace").strip()
            if "error" not in text.lower() and "API" not in text:
                lines = [l for l in text.splitlines() if l.strip()]
                print(G + f"Ditemukan {len(lines)} host:\n" + W)
                for l in lines[:40]:
                    print(f"  {l}")
                if len(lines) > 40:
                    print(Y + f"  ... dan {len(lines) - 40} lainnya." + W)
            else:
                print(Y + text[:200] + W)
        except Exception as e:
            print(Y + f"Gagal: {e}" + W)

    # ── Reverse DNS (berlaku untuk domain dan IP) ──
    ip_to_check = raw if is_ip else None
    if not is_ip:
        try:
            ip_to_check = socket.gethostbyname(target)
            print(G + f"Domain '{target}' → {ip_to_check}" + W)
        except Exception:
            pass

    if ip_to_check:
        print(Y + f"\n[{'4/4' if not is_ip else '1/1'}] Reverse DNS — {ip_to_check}...\n" + W)
        try:
            url = f"{BASE}/reversedns/?q={ip_to_check}"
            req = urllib.request.Request(url, headers={"User-Agent": "AZ-OSINT-Tool/1.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                text = res.read().decode("utf-8", errors="replace").strip()
            if "error" not in text.lower() and "API" not in text:
                print(text)
            else:
                print(Y + text[:200] + W)
        except Exception as e:
            print(Y + f"Gagal: {e}" + W)

    # ── Manual links ──
    print(C + "\n[Referensi Manual]" + W)
    if not is_ip:
        print(f"DNSDumpster    : https://dnsdumpster.com")
        print(f"SecurityTrails : https://securitytrails.com/domain/{target}/history")
        print(f"ViewDNS History: https://viewdns.info/dnsrecord/?domain={target}")
    print(f"MXToolbox      : https://mxtoolbox.com/SuperTool.aspx?action=dns%3A{raw}")

    print(Y + "\nCatatan: zone transfer yang berhasil pada target produksi = critical finding. HackerTarget free tier dibatasi jumlah query per hari." + W)


# ─────────────────────────────────────────────
# [23] PLAT NOMOR INDONESIA
# ─────────────────────────────────────────────
def plat_nomor():
    raw = input("Plat nomor (contoh: B 1234 ABC / AB1234CD): ").strip().upper()
    clean = re.sub(r'\s+', ' ', raw).strip()

    match = re.match(r'^([A-Z]{1,2})\s*(\d{1,4})\s*([A-Z]{1,3})?$', clean)
    if not match:
        print(R + "Format tidak dikenali. Contoh: B 1234 ABC atau DK 4321 XY" + W)
        return

    kode  = match.group(1)
    angka = match.group(2)
    seri  = match.group(3) or ""

    info = PLAT_DB.get(kode)
    if not info:
        print(R + f"Kode wilayah '{kode}' tidak ada dalam database." + W)
        print(Y + "Kemungkinan kode baru pasca-pemekaran provinsi, plat khusus, atau input salah." + W)
        return

    plat_display = f"{kode} {angka} {seri}".strip()
    print(C + f"\n[Plat Nomor: {plat_display}]" + W)
    print(f"Kode wilayah  : {kode}")
    print(f"Provinsi      : {info['wilayah']}")
    print(f"Kota/Kab      : {info['kota']}")

    if kode == "B" and seri:
        sub = _jakarta_sub(seri)
        if sub:
            print(f"Sub-wilayah   : {sub} (estimasi dari seri '{seri}')")

    print(f"Nomor         : {angka}")
    if seri:
        print(f"Seri          : {seri}")

    # Warna
    print(C + "\n[Warna Plat — masukkan untuk identifikasi kategori]" + W)
    for k, (warna, desc) in WARNA_PLAT.items():
        print(f"  [{k}] {warna:<8} — {desc}")
    wc = input("Pilihan warna (Enter = skip): ").strip()
    if wc in WARNA_PLAT:
        warna, desc = WARNA_PLAT[wc]
        print(G + f"\nKategori : {warna} — {desc}" + W)
        if warna == "Kuning":
            print(Y + "Kendaraan angkutan umum atau niaga. Wajib uji KIR berkala." + W)
        elif warna == "Merah":
            print(Y + "Kendaraan dinas. Tidak bisa diperjualbelikan ke swasta." + W)
        elif warna == "Hijau":
            print(Y + "Kendaraan FTZ — tidak boleh dibawa keluar kawasan bebas tanpa izin Bea Cukai." + W)

    # Ganjil-genap (khusus B)
    if kode == "B" and angka:
        last = int(angka[-1])
        print(C + "\n[Ganjil-Genap — Jakarta]" + W)
        tipe = "GANJIL" if last % 2 == 1 else "GENAP"
        hari = "tanggal ganjil" if last % 2 == 1 else "tanggal genap"
        print(f"Digit terakhir {angka[-1]} → {tipe} — melintas di hari {hari}")
        print(Y + "Berlaku di ruas tertentu Jakarta pukul 06.00–10.00 & 16.00–21.00 hari kerja." + W)

    # Digital search
    plat_q   = quote_plus(plat_display)
    plat_q2  = quote_plus(f"{kode}{angka}{seri}")
    print(C + "\n[Pencarian Digital]" + W)
    print(f"Google        : https://www.google.com/search?q={plat_q}+OR+{plat_q2}")
    print(f"Google Images : https://www.google.com/search?q={plat_q}&tbm=isch")
    print(f"Twitter/X     : https://x.com/search?q={plat_q}")
    print(f"Facebook      : https://www.google.com/search?q={plat_q}+site%3Afacebook.com")
    print(f"Marketplace   : https://www.google.com/search?q={plat_q}+site%3Aolx.co.id+OR+site%3Amudah.id")

    # Cek resmi
    print(C + "\n[Cek Resmi — buka manual di browser]" + W)
    print(f"e-Samsat Nasional : https://e-samsat.id")
    print(f"Signal (Samsat)   : Buka aplikasi Signal → Cek Ranmor")
    print(f"e-Tilang          : https://etle-pmj.id/id/search")
    if kode == "B":
        print(f"Samsat Jakarta    : https://samsat-pkb2.jakarta.go.id")

    if input("\nSimpan ke TXT? (y/n): ").strip().lower() == "y":
        out = Path(f"plat_{kode}{angka}{seri}.txt")
        lines = [
            f"Plat Nomor: {plat_display}", "=" * 40,
            f"Kode     : {kode}",
            f"Provinsi : {info['wilayah']}",
            f"Kota/Kab : {info['kota']}",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")
        print(G + "Disimpan:", out.resolve(), W)

    print(Y + "\nCatatan: tool ini hanya parsing kode wilayah dari data publik resmi. Nama pemilik, alamat, STNK, nomor rangka/mesin TIDAK tersedia — hanya bisa diakses oleh Samsat/Polri dengan otorisasi." + W)


# ─────────────────────────────────────────────
# [24] IMAGE GEOLOCATION — Gambar → Google Maps
#      EXIF GPS → langsung Maps
#      Tanpa GPS → link ke GeoSpy AI, Picarta, Google Lens, Yandex
# ─────────────────────────────────────────────
def image_geolocation():
    print(C + "\nImage Geolocation — Pilih mode:" + W)
    print("[1] File gambar lokal (ekstrak EXIF GPS)")
    print("[2] URL gambar (ekstrak EXIF + reverse image links)")
    print("[3] Tidak punya gambar — langsung ke daftar AI tools")
    mode = input("Pilihan: ").strip()

    if mode == "1":
        path = input("Path file gambar: ").strip().strip('"')
        file = Path(path).expanduser()
        if not file.is_file():
            print(R + "File tidak ditemukan." + W)
            return
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            with Image.open(file) as img:
                print(C + f"\n[{file.name}] {img.format} {img.size[0]}×{img.size[1]}px" + W)
                exif = img.getexif()
            if not exif:
                print(Y + "Tidak ada EXIF di file ini." + W)
                _print_ai_geo_tools()
                return
            lat = lon = None
            for key, val in exif.items():
                if TAGS.get(key) == "GPSInfo":
                    gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                    lat = _gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
                    lon = _gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))
                    break
            if lat and lon:
                _print_maps_links(lat, lon, f"EXIF dari {file.name}")
            else:
                print(Y + "EXIF ada tapi tidak ada GPS — kemungkinan foto dari kamera tanpa GPS." + W)
                _print_ai_geo_tools()
        except ImportError:
            print(R + "Pillow belum terpasang. pip install Pillow" + W)
        except Exception as e:
            print(R + f"Gagal: {e}" + W)
            _print_ai_geo_tools()

    elif mode == "2":
        img_url = input("URL gambar: ").strip()
        if not img_url:
            print(R + "URL tidak boleh kosong." + W)
            return
        if "://" not in img_url:
            img_url = "https://" + img_url

        lat = lon = None
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            req = urllib.request.Request(img_url, headers={
                "User-Agent": "Mozilla/5.0 AZ-OSINT-Tool/1.0"
            })
            with urllib.request.urlopen(req, timeout=15) as res:
                data = res.read(8_000_000)
            with Image.open(io.BytesIO(data)) as img:
                fname = urlparse(img_url).path.split("/")[-1] or "image"
                print(C + f"\n[{fname}] {img.format} {img.size[0]}×{img.size[1]}px" + W)
                exif = img.getexif()
            if exif:
                for key, val in exif.items():
                    if TAGS.get(key) == "GPSInfo":
                        gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                        lat = _gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
                        lon = _gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))
                        break
        except ImportError:
            print(R + "Pillow belum terpasang. pip install Pillow" + W)
        except Exception as e:
            print(Y + f"Tidak bisa baca EXIF: {e}" + W)

        if lat and lon:
            _print_maps_links(lat, lon, "EXIF dari URL gambar")
        else:
            print(Y + "\nTidak ada GPS EXIF — platform kemungkinan sudah strip metadata." + W)

        # Reverse image search — selalu tampil untuk mode URL
        enc = quote_plus(img_url)
        print(C + "\n[Reverse Image Search — buka di browser]" + W)
        print(f"Google Lens  : https://lens.google.com/uploadbyurl?url={enc}")
        print(f"Yandex       : https://yandex.com/images/search?rpt=imageview&url={enc}")
        print(f"Bing Visual  : https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{enc}")
        print(f"TinEye       : https://tineye.com/search?url={enc}")
        _print_ai_geo_tools()

    elif mode == "3":
        _print_ai_geo_tools()

    else:
        print(R + "Pilihan tidak valid." + W)

while True:
    banner()
    choice = input("AZ-OSINT > ").strip()
    if   choice == "1":  footprint()
    elif choice == "2":  metadata()
    elif choice == "3":  digital_footprint()
    elif choice == "4":  domain_intelligence()
    elif choice == "5":  email_intelligence()
    elif choice == "6":  numbers_intelligence()
    elif choice == "7":  ip_intelligence()
    elif choice == "8":  website_safety_checker()
    elif choice == "9":  website_style_grabber()
    elif choice == "10": school_info_grabber()
    elif choice == "11": subdomain_finder()
    elif choice == "12": paste_intelligence()
    elif choice == "13": username_extended()
    elif choice == "14": reverse_ip()
    elif choice == "15": google_dork_generator()
    elif choice == "16": shodan_intelligence()
    elif choice == "17": url_media_metadata()
    elif choice == "18": geo_osint()
    elif choice == "19": domain_harvester()
    elif choice == "20": wayback_cdx_recon()
    elif choice == "21": asn_intelligence()
    elif choice == "22": dns_history_recon()
    elif choice == "23": plat_nomor()
    elif choice == "24": image_geolocation()
    elif choice == "0":
        print("Keluar dari AZ-OSINT-TOOL.")
        sys.exit()
    else:
        print(R + "Pilihan tidak valid." + W)
    input("\nTekan Enter untuk kembali...")