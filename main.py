import sys
import time
import os
import tty
import termios
import math
import random
import threading
import shutil
import re
from datetime import datetime
from colorama import Fore, Back, Style, init

from main_engine import run_single_round, run_infinite_loop

init(autoreset=True)

VERSION   = "1.3.0"
TOOLS_NAME = "AzTools"
AUTHOR    = "Khaerul"
TOTAL_API = 24

exec_data = {
    'target'    : '',
    'threads'   : 5,
    'total_api' : TOTAL_API,
    'status'    : 'Initializing...',
    'progress'  : 0,
    'sent'      : 0,
    'success'   : 0,
    'failed'    : 0,
    'last_log'  : 'Starting...',
    'round'     : 0,
    'start_time': '─',
}

# ══════════════════════════════════════════════
# COLOR UTILITIES
# ══════════════════════════════════════════════

def rgb_color(tick, offset=0):
    r = int((math.sin(tick * 0.5 + offset) + 1) * 127)
    g = int((math.sin(tick * 0.5 + offset + 2) + 1) * 127)
    b = int((math.sin(tick * 0.5 + offset + 4) + 1) * 127)
    return f"\033[38;2;{r};{g};{b}m"

def bg_rgb(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"

def gradient_text(text, tick, offset=0):
    out = ""
    for i, ch in enumerate(text):
        out += f"{rgb_color(tick, offset + i * 0.1)}{ch}\033[0m"
    return out

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def term_size():
    try:
        sz = shutil.get_terminal_size()
        return max(sz.columns, 40), max(sz.lines, 20)
    except Exception:
        return 80, 24

def ui_w():
    """Lebar terminal aktual minus 1 supaya tidak wrap."""
    try:
        return max(20, shutil.get_terminal_size().columns - 1)
    except Exception:
        return 39

def div(tick=0, char='─'):
    w = ui_w()
    c = rgb_color(tick, 1)
    print(f"{c}{char * w}\033[0m")

def cprint(text, indent=1):
    """Cetak teks rata kiri dengan indent tetap."""
    print(' ' * indent + text)

def cprint_center(plain, colored=None):
    """
    Cetak teks rata tengah.
    plain  = teks tanpa ANSI (untuk ukur lebar)
    colored = teks dengan ANSI (yang dicetak), default sama dengan plain
    """
    w   = ui_w()
    pad = max(0, (w - len(plain)) // 2)
    print(' ' * pad + (colored if colored is not None else plain))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ══════════════════════════════════════════════
# MATRIX BACKGROUND
# ══════════════════════════════════════════════

class MatrixBackground:
    CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&'

    def __init__(self):
        self.width, self.height = term_size()
        self.columns = self._init_columns()

    def _init_columns(self):
        cols = []
        for x in range(self.width):
            length = random.randint(8, 25)
            cols.append({
                'x'     : x,
                'y'     : random.randint(-self.height, 0),
                'speed' : random.uniform(0.8, 2.5),
                'length': length,
                'chars' : [random.choice(self.CHARS) for _ in range(length)],
                'bright': random.randint(0, length - 1),
            })
        return cols

    def update(self):
        for col in self.columns:
            col['y'] += col['speed'] * 0.6
            if col['y'] > self.height + col['length']:
                col['y']      = random.randint(-self.height, 0)
                col['length'] = random.randint(8, 25)
                col['chars']  = [random.choice(self.CHARS) for _ in range(col['length'])]
                col['speed']  = random.uniform(0.8, 2.5)
                col['bright'] = random.randint(0, col['length'] - 1)
            if random.random() < 0.03:
                for i in range(len(col['chars'])):
                    if random.random() < 0.3:
                        col['chars'][i] = random.choice(self.CHARS)

    def render(self, overlay_lines=None):
        sys.stdout.write('\033[?25l\033[H')
        screen = [[' '] * self.width for _ in range(self.height)]

        for col in self.columns:
            x, bp = col['x'], col['bright']
            sy = int(col['y'])
            for i, ch in enumerate(col['chars']):
                y = sy + i
                if 0 <= y < self.height and 0 <= x < self.width:
                    if i == bp:
                        c = '\033[1;92m'
                    elif bp - 3 < i < bp + 2:
                        c = '\033[32m'
                    else:
                        c = '\033[2;32m'
                    screen[y][x] = f"{c}{ch}\033[0m"

        sys.stdout.write('\n'.join(''.join(row) for row in screen))

        if overlay_lines:
            lines  = [l for l in overlay_lines if l.strip() or l == '']
            start_y = max(1, (self.height - len(lines)) // 2)
            for i, line in enumerate(lines):
                clean = strip_ansi(line)
                xp    = max(0, (self.width - len(clean)) // 2)
                sys.stdout.write(f'\033[{start_y + i};{xp}H{line}')

        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

# ══════════════════════════════════════════════
# LOADING SCREEN
# ══════════════════════════════════════════════

ASCII_LOGO = [
    "  █████╗ ███████╗    ████████╗ ██████╗  ██████╗ ██╗     ███████╗",
    " ██╔══██╗╚══███╔╝    ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝",
    " ███████║  ███╔╝        ██║   ██║   ██║██║   ██║██║     ███████╗ ",
    " ██╔══██║ ███╔╝         ██║   ██║   ██║██║   ██║██║     ╚════██║ ",
    " ██║  ██║███████╗       ██║   ╚██████╔╝╚██████╔╝███████╗███████║ ",
    " ╚═╝  ╚═╝╚══════╝       ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝",
]

def matrix_loading(duration=3):
    matrix = MatrixBackground()
    start  = time.time()
    tick   = 0.0

    while time.time() - start < duration:
        tick += 0.05
        matrix.update()

        progress = (time.time() - start) / duration
        pct      = int(progress * 100)

        colored_logo = []
        for line in ASCII_LOGO:
            cl = ""
            for i, ch in enumerate(line):
                cl += f"{rgb_color(tick, i * 0.08)}{ch}\033[0m" if ch != ' ' else ' '
            colored_logo.append(cl)

        w       = matrix.width
        bar_len = min(46, w - 14)
        filled  = int(bar_len * progress)
        bar     = '█' * filled + '░' * (bar_len - filled)
        bar_c   = rgb_color(tick, 3)
        pct_c   = rgb_color(tick, 5)

        dc     = int((time.time() - start) * 3) % 4
        dots   = '·' * dc + ' ' * (3 - dc)
        status = (
            'INITIALIZING'    if progress < 0.25 else
            'LOADING MODULES' if progress < 0.55 else
            'PREPARING'       if progress < 0.80 else
            'READY'
        )

        div = f"{rgb_color(tick, 2)}{'─' * min(50, w - 4)}\033[0m"

        overlay = [
            '',
            *colored_logo,
            '',
            div,
            f"{rgb_color(tick, 1)}  {TOOLS_NAME}  ·  v{VERSION}  ·  by {AUTHOR}  ·  {TOTAL_API} APIs\033[0m",
            div,
            '',
            f"{bar_c}[{bar}] {pct_c}{pct}%\033[0m",
            f"{rgb_color(tick, 6)}{status}{dots}\033[0m",
            '',
        ]

        matrix.render(overlay)
        time.sleep(0.03)

    sys.stdout.write('\033[?25h')
    sys.stdout.flush()

# ══════════════════════════════════════════════
# BANNER
# ══════════════════════════════════════════════

def print_banner(tick=0):
    R   = Style.RESET_ALL
    dim = '\033[2m'
    now = datetime.now().strftime("%H:%M:%S")
    c2  = '\033[0;33m'
    c3  = '\033[1;32m'
    c4  = '\033[1;35m'

    print()

    # Judul — ukur dari plain, cetak gradient
    title_plain   = f"{TOOLS_NAME}  \u2014  OTP TOOL"
    cprint_center(title_plain, gradient_text(title_plain, tick))
    print()

    # Info row — plain dulu untuk ukur, colored untuk cetak
    info_plain    = f"API:{TOTAL_API}  VER:{VERSION}  DEV:{AUTHOR}"
    info_colored  = (f"{c2}API{R}{dim}:{R}{c3}{TOTAL_API}{R}  "
                     f"{c2}VER{R}{dim}:{R}{c3}{VERSION}{R}  "
                     f"{c2}DEV{R}{dim}:{R}{c3}{AUTHOR}{R}")
    cprint_center(info_plain, info_colored)

    # Jam — plain untuk ukur, colored untuk cetak
    clock_plain   = f"JAM:{now}"
    clock_colored = f"{c2}JAM{R}{dim}:{R}{c4}{now}{R}"
    cprint_center(clock_plain, clock_colored)
    print()

# Warna background per item saat diselect: hijau, biru, merah
_SEL_BG = ['\033[42;97m', '\033[44;97m', '\033[41;97m']

def print_menu(selected=0, tick=0):
    R   = Style.RESET_ALL
    hc  = '\033[1;35m'
    nc  = '\033[0;36m'
    dc  = '\033[2;37m'
    hkc = '\033[1;33m'

    labels = ['Single Round', 'Infinite Loop', 'Keluar']
    descs  = ['Sekali kirim semua API', 'Kirim nonstop berulang', 'Tutup aplikasi']

    # Header
    cprint_center("MENU UTAMA", f"{hc}MENU UTAMA{R}")
    print()

    for i, (label, desc) in enumerate(zip(labels, descs)):
        # Plain text untuk ukur pad — TIDAK ada ANSI code apapun
        lp = f"  {label}  "
        dp = f"  {desc}  "
        if i == selected:
            bg = _SEL_BG[i]
            cprint_center(lp, f"{bg}{lp}{R}")
            cprint_center(dp, f"{bg}{dp}{R}")
        else:
            cprint_center(label, f"{nc}{label}{R}")
            cprint_center(desc,  f"{dc}{desc}{R}")
        print()

    # Hotkey hint — plain tanpa warna untuk ukur
    hint_p = "\u2191\u2193 Nav  ENTER Pilih  Q Quit"
    hint_c = f"{hkc}\u2191\u2193{R} Nav  {hkc}ENTER{R} Pilih  {hkc}Q{R} Quit"
    cprint_center(hint_p, hint_c)
    print()

# ══════════════════════════════════════════════
# EXECUTION TABLE
# ══════════════════════════════════════════════

def show_execution_table(data, tick=0):
    clear_screen()
    R   = Style.RESET_ALL
    dim = '\033[2m'
    lc  = '\033[0;32m'
    ac  = '\033[1;36m'
    tc  = '\033[1;35m'
    yc  = '\033[1;33m'

    now = datetime.now().strftime("%H:%M:%S")
    div(tick, '═')
    cprint(f"{ac}⚡ {TOOLS_NAME} — EKSEKUSI{R}  {tc}{now}{R}")
    div(tick)

    target_val = str(data.get('target', 'N/A'))
    # truncate supaya tidak wrap
    max_t = ui_w() - 10
    if len(target_val) > max_t:
        target_val = target_val[:max_t-1] + '…'

    cprint(f"{lc}TARGET{R} {yc}{target_val}{R}")
    cprint(f"{lc}API{R}    {ac}{data.get('total_api', TOTAL_API)}{R}  "
           f"{lc}ROUND{R} {tc}{data.get('round', 0)}{R}")
    cprint(f"{lc}MULAI{R}  {tc}{data.get('start_time', '─')}{R}")
    cprint(f"{lc}STATUS{R} {ac}{data.get('status', '...')}{R}")

    div(tick)
    prog   = max(0, min(100, data.get('progress', 0)))
    blen   = max(10, ui_w() - 8)
    filled = int(blen * prog / 100)
    bar    = '█' * filled + '░' * (blen - filled)
    cprint(f"\033[1;32m[{bar}]{R} {prog}%")

    div(tick)
    sent    = data.get('sent',    0)
    success = data.get('success', 0)
    failed  = data.get('failed',  0)
    rate    = f"{int(success / max(1, sent) * 100)}%" if sent else "─"
    cprint(f"{lc}SENT{R} {yc}{sent}{R}  {lc}OK{R} \033[1;32m{success}{R}  "
           f"{lc}FAIL{R} \033[1;31m{failed}{R}  {lc}RATE{R} {ac}{rate}{R}")

    div(tick)
    raw_log  = str(data.get('last_log', ''))
    log_text = raw_log[:ui_w() - 6]
    ll       = raw_log.lower()
    if 'success' in ll or 'ok' in ll:    lcolor = '\033[1;32m'
    elif 'fail' in ll or 'error' in ll:  lcolor = '\033[1;31m'
    elif 'limit' in ll or 'block' in ll: lcolor = '\033[1;33m'
    else:                                 lcolor = '\033[0;37m'
    cprint(f"{lc}LOG{R} {lcolor}{log_text}{R}")
    div(tick, '═')
    cprint(f"{dim}CTRL+C berhenti{R}")

# ══════════════════════════════════════════════
# INPUT & ANIMATION HELPERS
# ══════════════════════════════════════════════

def print_loading_animation(message="Processing", duration=1):
    spins = ['◐', '◓', '◑', '◒']
    start = time.time()
    tick  = 0.0
    while time.time() - start < duration:
        tick += 0.1
        sp   = spins[int((time.time() - start) * 8) % 4]
        sys.stdout.write(f'\r  {rgb_color(tick)}{sp}  {message}...{Style.RESET_ALL}   ')
        sys.stdout.flush()
        time.sleep(0.05)
    print('\r' + ' ' * 60 + '\r', end='')

def input_with_animation(prompt="Masukkan nomor target", duration=1.5):
    R     = Style.RESET_ALL
    spins = ['◐', '◓', '◑', '◒']
    tick  = 0.0
    start = time.time()
    spin_text = "Siapkan nomor (08xx...)"

    print()
    div(0.5, '─')
    cprint(f"\033[1;37m{prompt.upper()}{R}")
    div(0.5, '─')

    while time.time() - start < duration:
        tick += 0.1
        sp = spins[int((time.time() - start) * 6) % 4]
        sys.stdout.write(f"\r \033[0;36m{sp}\033[0m \033[2m{spin_text}\033[0m  ")
        sys.stdout.flush()
        time.sleep(0.05)

    # clear spinner line
    sys.stdout.write(f"\r{' ' * (len(spin_text) + 6)}\r")
    sys.stdout.write(f" \033[0;32m➜\033[0m ")
    sys.stdout.flush()
    value = input().strip()
    div(0.5)
    return value


# ══════════════════════════════════════════════
# KEY INPUT
# ══════════════════════════════════════════════

def get_key(timeout=None):
    """Baca satu keypress. Kalau timeout (detik) diisi, return None kalau tidak ada input."""
    import select
    try:
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if timeout is not None:
                ready, _, _ = select.select([sys.stdin], [], [], timeout)
                if not ready:
                    return None
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                # baca escape sequence tanpa block
                ready2, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready2:
                    ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        try:
            import msvcrt
            return msvcrt.getch().decode()
        except Exception:
            return None

# ══════════════════════════════════════════════
# EXEC DATA UPDATE
# ══════════════════════════════════════════════

def update_exec_data(name, status, detail=""):
    global exec_data
    exec_data['last_log'] = f"{name}: {status}" + (f" — {detail}" if detail else "")
    if status == "SUCCESS":
        exec_data['success'] += 1
    elif status in ("FAIL", "ERROR", "TIMEOUT"):
        exec_data['failed'] += 1
    exec_data['sent'] += 1
    total = exec_data.get('total_api', TOTAL_API)
    sent  = exec_data.get('sent', 0)
    exec_data['progress'] = min(100, int(sent / max(1, total) * 100))

# ══════════════════════════════════════════════
# RUN WITH UI
# ══════════════════════════════════════════════

def run_with_ui(engine_func, target, threads=5):
    global exec_data

    exec_data.update({
        'target'    : target,
        'threads'   : threads,
        'total_api' : TOTAL_API,
        'status'    : 'Running...',
        'progress'  : 0,
        'sent'      : 0,
        'success'   : 0,
        'failed'    : 0,
        'last_log'  : 'Initializing...',
        'round'     : exec_data.get('round', 0) + 1,
        'start_time': datetime.now().strftime("%H:%M:%S"),
    })

    stop_flag = threading.Event()

    def ui_loop():
        tick = 0.0
        while not stop_flag.is_set():
            tick += 0.1
            show_execution_table(exec_data, tick)
            time.sleep(0.1)

    ui_thread = threading.Thread(target=ui_loop, daemon=True)
    ui_thread.start()

    try:
        if engine_func == run_single_round:
            result = run_single_round(threads=threads, target=target, callback=update_exec_data)
        else:
            result = run_infinite_loop(target=target, callback=update_exec_data)

        exec_data['status']   = 'Completed' if result else 'Failed'
        exec_data['progress'] = 100
        time.sleep(1)
        return result
    except KeyboardInterrupt:
        exec_data['status'] = 'Stopped'
        raise
    finally:
        stop_flag.set()
        ui_thread.join(timeout=1.0)

# ══════════════════════════════════════════════
# MENU NAVIGATION
# ══════════════════════════════════════════════

def _exit_clean():
    R = Style.RESET_ALL
    print(f"\n  {rgb_color(1.0, 1)}◐{R}  Keluar...")
    time.sleep(0.4)
    print(f"  \033[1;32m✓{R}  Sampai jumpa! 👋\n")
    sys.exit(0)

def _input_delay():
    R = Style.RESET_ALL
    div(1.2, '─')
    cprint(f"\033[1;37mDELAY SEBELUM JALAN (detik){R}")
    cprint(f"\033[2m0 atau kosong = langsung{R}")
    div(1.2, '─')
    sys.stdout.write(f" \033[0;32m➜{R} ")
    sys.stdout.flush()
    raw = input().strip()
    div(1.2)
    try:
        return max(0, int(raw))
    except (ValueError, TypeError):
        return 0


def _countdown(label, target, seconds):
    R    = Style.RESET_ALL
    tick = 0.0
    print()
    div(0.8, '─')
    cprint(f"\033[1;37m{label}{R}  →  \033[1;33m{target}{R}")
    div(0.8, '─')

    if seconds > 0:
        blen = max(8, ui_w() - 16)
        for i in range(seconds, 0, -1):
            tick += 0.4
            cc  = '\033[1;33m'
            tc  = '\033[1;35m'
            now = datetime.now().strftime("%H:%M:%S")
            done = seconds - i + 1
            bar  = '█' * min(blen, done) + '░' * max(0, blen - done)
            sys.stdout.write(f"\r {cc}{i}dtk{R} [{bar}] \033[2m{tc}{now}{R}  ")
            sys.stdout.flush()
            time.sleep(1)
        print()

    run_ts = datetime.now().strftime("%H:%M:%S")
    cprint(f"\033[1;32m▶ Mulai{R}  \033[2mpada{R} \033[1;35m{run_ts}{R}")
    div(0.8)
    print()

def _handle_choice(choice):
    R = Style.RESET_ALL
    clear_screen()
    target = input_with_animation("Masukkan nomor target", 1.5)
    if not target:
        print(f"\n  \033[1;31m✗{R}  Nomor tidak boleh kosong!")
        time.sleep(1.2)
        return

    print()
    delay  = _input_delay()
    label  = "Single Round" if choice == "single" else "Infinite Loop"
    engine = run_single_round if choice == "single" else run_infinite_loop

    _countdown(label, target, seconds=delay)
    clear_screen()

    print(f"\n  \033[1;33m⚡{R}  Mode \033[1;37m{label}{R} — target \033[1;36m{target}{R}")
    if choice == "infinite":
        print(f"  \033[2;33mMode ini berjalan terus hingga CTRL+C{R}")
    print(f"  \033[2;37mTekan CTRL+C untuk menghentikan{R}\n")

    try:
        run_with_ui(engine, target, threads=5)
    except KeyboardInterrupt:
        print(f"\n\n  \033[1;33m⚠{R}  Proses dihentikan.")

    print(f"\n  \033[1;32m✓{R}  Selesai!")
    print(f"  \033[2;37mTekan Enter untuk kembali ke menu...{R}")
    input()

def menu_navigation():
    items     = ["single", "infinite", "exit"]
    selected  = 0
    is_termux = os.path.exists("/data/data/com.termux/files/usr")

    if not is_termux:
        # Non-termux: render sekali, input angka, tidak perlu live clock
        while True:
            try:
                clear_screen()
                print_banner(0)
                print_menu(selected, 0)
                R = Style.RESET_ALL
                print(f"  \033[2;37mNavigasi keyboard tidak tersedia — gunakan angka{R}")
                print(f"  \033[0;36m[1]{R} Single Round   \033[0;36m[2]{R} Infinite Loop   \033[0;36m[3]{R} Keluar\n")
                raw = input(f"  \033[1;37mPilih (1/2/3): {R}").strip()
                if raw == '1':
                    _handle_choice('single')
                elif raw == '2':
                    _handle_choice('infinite')
                elif raw == '3':
                    _exit_clean()
            except KeyboardInterrupt:
                _exit_clean()
            except Exception as e:
                R = Style.RESET_ALL
                print(f"\n  \033[1;31m✗{R}  Error: {e}")
                time.sleep(1.2)
        return

    # Termux: live render di background thread, keypress dengan timeout
    tick      = 0.0
    stop_flag = threading.Event()
    lock      = threading.Lock()

    def render_loop():
        nonlocal tick
        while not stop_flag.is_set():
            with lock:
                t = tick
            clear_screen()
            print_banner(t)
            print_menu(selected, t)
            with lock:
                tick += 0.08
            time.sleep(0.5)   # refresh setiap 0.5 detik → jam live update

    render_thread = threading.Thread(target=render_loop, daemon=True)
    render_thread.start()

    try:
        while True:
            # get_key timeout 0.5s — kalau tidak ada input, loop lagi (render jalan)
            key = get_key(timeout=0.5)
            if key is None:
                continue
            stop_flag.set()
            render_thread.join(timeout=0.6)

            if key == '\x1b[A':
                selected = (selected - 1) % len(items)
            elif key == '\x1b[B':
                selected = (selected + 1) % len(items)
            elif key in ('\r', '\n', '\x1b[C'):
                choice = items[selected]
                if choice == 'exit':
                    _exit_clean()
                else:
                    _handle_choice(choice)
            elif key in ('q', 'Q'):
                _exit_clean()

            # reset render thread untuk putaran berikutnya
            stop_flag.clear()
            tick = 0.0
            render_thread = threading.Thread(target=render_loop, daemon=True)
            render_thread.start()

    except KeyboardInterrupt:
        stop_flag.set()
        _exit_clean()
    except Exception as e:
        stop_flag.set()
        R = Style.RESET_ALL
        print(f"\n  \033[1;31m✗{R}  Error: {e}")
        time.sleep(1.2)

# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════

def main():
    try:
        matrix_loading(3)
        clear_screen()

        is_termux = os.path.exists("/data/data/com.termux/files/usr")
        if is_termux:
            R = Style.RESET_ALL
            print(f"  \033[1;32m✓{R}  Termux terdeteksi")
            print(f"  \033[2;37m↑ ↓ navigasi  ·  ENTER pilih  ·  Q keluar{R}\n")
            time.sleep(0.8)

        menu_navigation()

    except KeyboardInterrupt:
        _exit_clean()
    except Exception as e:
        R = Style.RESET_ALL
        print(f"\n  \033[1;31m✗{R}  Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
