import os, sys, json, socket, ssl, ipaddress, urllib.request, urllib.error, re
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

def banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(C + "=" * 29)
    print("         AZ-OSINT-TOOL")
    print("=" * 29 + W)
    print("[1] Social Check")
    print("[2] Metadata Check")
    print("[3] Digital Footprint Check")
    print("[4] Domain Intelligence")
    print("[5] Email Intelligence")
    print("[6] Numbers Intelligence (Indonesia)")
    print("[7] IP Intelligence")
    print("[8] Website Safety Checker")
    print("[9] Website Style Grabber (HTML/CSS)")
    print("[10] School Info Grabber (NPSN)")
    print("[0] Exit")
    print("=" * 29)

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


while True:
    banner()
    choice = input("AZ-OSINT > ").strip()
    if choice == "1":
        footprint()
    elif choice == "2":
        metadata()
    elif choice == "3":
        digital_footprint()
    elif choice == "4":
        domain_intelligence()
    elif choice == "5":
        email_intelligence()
    elif choice == "6":
        numbers_intelligence()
    elif choice == "7":
        ip_intelligence()
    elif choice == "8":
        website_safety_checker()
    elif choice == "9":
        website_style_grabber()
    elif choice == "10":
        school_info_grabber()
    elif choice == "0":
        print("Keluar dari AZ-OSINT-TOOL.")
        sys.exit()
    else:
        print(R + "Pilihan tidak valid." + W)
    input("\nTekan Enter untuk kembali...")
