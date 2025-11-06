# AstraKeys_v1.1.3 — Black Onyx / Solar Gold / Nebula blend
# Frameless window (draggable by top bar), minimal buttons (—, ×)
# Auto-update (manual trigger via GUI) — checks GitHub Releases, downloads asset and replaces running exe/script.
# Pedal keys: '*', '[' and ']' all act as sustain pedal (hold).
# Window is frameless, draggable by top bar, and stays on top of other windows.
#
# IMPORTANT:
# - Put your icon at assets/icon.ico
# - Ensure GITHUB_OWNER / GITHUB_REPO are correct
# - Build with PyInstaller including pywin32 (if you want Roblox activation) and PyQt6:
#     pip install pywin32 pyinstaller pyqt6 pynput requests
#     pyinstaller --noconfirm --onefile --windowed --add-data "assets/icon.ico;assets" AstraKeys.py
#
# Author: generated for user
# Version: 1.1.3

CURRENT_VERSION = "1.1.3"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"  # file that will be downloaded and replace current exe

# ---------------- imports ----------------
import os
import sys
import time
import threading
import re
import random
from datetime import datetime

# optional win32: used only for bringing Roblox window to foreground; absence is tolerated
try:
    import win32gui
    import win32con
except Exception:
    win32gui = None
    win32con = None

# keyboard listener
try:
    from pynput.keyboard import Controller, Key, Listener
except Exception:
    Controller = None
    Key = None
    Listener = None

# network and GUI
import requests

try:
    from PyQt6 import QtWidgets, QtCore, QtGui
except Exception:
    raise RuntimeError("PyQt6 is required. Install via: pip install PyQt6")

# ---------------- constants & pedal ----------------
PEDAL_KEYS = {"*", "[", "]"}  # these keys act as sustain/pedal
ROBLOX_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnm"

# ---------------- Auto-update (manual trigger) ----------------
def download_asset_to_file(url, dest_path, progress_callback=None):
    """
    Downloads a file from url to dest_path.
    If progress_callback is provided, calls progress_callback(percent_int) periodically.
    """
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = r.headers.get("content-length")
            if total is None:
                # unknown size
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(1024 * 64):
                        if chunk:
                            f.write(chunk)
                if progress_callback:
                    progress_callback(100)
                return True, None
            total = int(total)
            written = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(1024 * 64):
                    if chunk:
                        f.write(chunk)
                        written += len(chunk)
                        if progress_callback:
                            pct = int(written * 100 // total)
                            progress_callback(pct)
            return True, None
    except Exception as e:
        return False, str(e)

def perform_replacement_and_restart(new_file, target_name, is_frozen):
    """
    Replaces current executable/script with new_file and restarts.
    If is_frozen (running as exe), create and run update.bat that replaces and restarts.
    """
    try:
        if is_frozen or sys.argv[0].lower().endswith(".exe"):
            current_exec = os.path.basename(sys.argv[0])
            # create update batch
            bat_content = f"""@echo off
timeout /t 1 /nobreak >nul
taskkill /f /im "{current_exec}" >nul 2>&1
del "{current_exec}" >nul 2>&1
rename "{new_file}" "{target_name}" >nul 2>&1
start "" "{target_name}"
del "%~f0" & exit
"""
            with open("update.bat", "w", encoding="utf-8") as f:
                f.write(bat_content)
            try:
                os.startfile("update.bat")
            except Exception:
                os.system("start update.bat")
            # Exit current process so batch can replace
            sys.exit(0)
        else:
            # running as script: replace the script file and execv python interpreter
            target = os.path.abspath(sys.argv[0])
            try:
                backup = target + ".bak"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(target, backup)
            except Exception:
                # ignore backup errors
                pass
            try:
                os.replace(new_file, target)
            except Exception:
                # fallback copy
                with open(new_file, "rb") as src, open(target, "wb") as dst:
                    dst.write(src.read())
                os.remove(new_file)
            # restart
            os.execv(sys.executable, [sys.executable, target])
    except Exception as e:
        print("Replacement error:", e)
        raise

def fetch_latest_release_info():
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    try:
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

# ---------------- Roblox activation helpers ----------------
def find_roblox_window():
    if not win32gui:
        return None
    try:
        hwnd_found = None
        def cb(hwnd, extra):
            nonlocal hwnd_found
            try:
                title = win32gui.GetWindowText(hwnd)
                if "Roblox" in title:
                    hwnd_found = hwnd
            except Exception:
                pass
        win32gui.EnumWindows(cb, None)
        return hwnd_found
    except Exception:
        return None

def activate_roblox_window():
    if not win32gui:
        return False
    hwnd = find_roblox_window()
    if not hwnd:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False

# ---------------- Bot core ----------------
class RobloxPianoBot:
    def __init__(self, playlist, bpm=100):
        # keyboard controller (pynput)
        self.keyboard = Controller() if Controller else None
        self.roblox_window = None
        self.lock = threading.Lock()
        self.playlist = [self.sanitize_song(song) for song in playlist if self.sanitize_song(song)]
        if not self.playlist:
            print("⚠️ Playlist empty after filtering!")
            sys.exit(1)
        self.song_index = 0
        self.song = self.playlist[self.song_index]
        self.bpm = bpm
        self.playing = False
        self.restart = False
        self.skip_notes = 0
        self.note_index = 0
        self.hold_star = False  # sustain pedal
        self.freeze_note = False
        self.frozen_note_index = 0
        # modes: 1 - rovny, 2 - live, 3 - hybrid, 4 - error
        self.mode = 1
        self.start_delay = 0.03
        self.active_keys = set()
        print("🎹 AstraKeys Bot initialized")
        print("▶ F1 Play/Pause | F2 Restart | F3 Skip25 | F4 Exit")
        print("⭐ Pedal: *, [ , ] | ❄ F6 Freeze | F7 NextMode | F5 PrevMode | F8 NextSong | F9 CheckUpdate")
        # start listener in background if pynput available
        if Listener:
            threading.Thread(target=self.listen_keys, daemon=True).start()

    def sanitize_song(self, song):
        if not song:
            return ""
        return re.sub(r"[^a-zA-Z0-9\[\]\s]", "", song)

    def press_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            if key not in self.active_keys:
                try:
                    self.keyboard.press(key)
                except Exception:
                    pass
                self.active_keys.add(key)

    def release_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            if key in self.active_keys:
                try:
                    self.keyboard.release(key)
                except Exception:
                    pass
                self.active_keys.discard(key)

    def release_all(self):
        with self.lock:
            if not self.keyboard:
                self.active_keys.clear()
                return
            for k in list(self.active_keys):
                try:
                    self.keyboard.release(k)
                except Exception:
                    pass
            self.active_keys.clear()

    def apply_error(self, k):
        try:
            if k.lower() in ["1", "m"]:
                return k
            if random.random() < 0.05:
                c = k.lower()
                if c in ROBLOX_KEYS and len(c) == 1:
                    i = ROBLOX_KEYS.index(c)
                    if i == 0:
                        return ROBLOX_KEYS[1]
                    if i == len(ROBLOX_KEYS) - 1:
                        return ROBLOX_KEYS[-2]
                    return ROBLOX_KEYS[i + random.choice([-1, 1])]
        except Exception:
            pass
        return k

    def listen_keys(self):
        # Using pynput Listener to catch global keys (optional)
        def on_press(key):
            try:
                # function keys
                if key == Key.f7:
                    old = self.mode
                    self.mode = self.mode + 1 if self.mode < 4 else 1
                    print(f"Mode: {self.mode} (was {old})")
                    return
                if key == Key.f5:
                    old = self.mode
                    self.mode = self.mode - 1 if self.mode > 1 else 4
                    print(f"Mode: {self.mode} (was {old})")
                    return
                if key == Key.f1:
                    self.playing = not self.playing
                    print("Play" if self.playing else "Pause")
                elif key == Key.f2:
                    self.restart = True
                    print("Restart")
                elif key == Key.f3:
                    self.skip_notes += 25
                    print("Skip 25")
                elif key == Key.f4:
                    print("Exit")
                    self.release_all()
                    os._exit(0)
                elif key == Key.f6:
                    self.freeze_note = not self.freeze_note
                    if self.freeze_note:
                        self.frozen_note_index = self.note_index
                        print(f"Freeze at {self.frozen_note_index}")
                    else:
                        print("Freeze off")
                        self.release_all()
                elif key == Key.f8:
                    self.next_song()
                elif key == Key.f9:
                    # We'll not directly call GUI update from here (thread-safety).
                    # Instead, set a flag or print — GUI has its own button for update.
                    print("F9 pressed — please use GUI update button for controlled update.")
                else:
                    # pedal keys mapping: support char-based keys
                    if hasattr(key, "char") and key.char in PEDAL_KEYS:
                        self.hold_star = True
                        print("Pedal down (via listener)")
            except Exception as e:
                print("Listener keypress error:", e)

        def on_release(key):
            try:
                if hasattr(key, "char") and key.char in PEDAL_KEYS:
                    self.hold_star = False
                    print("Pedal up (via listener)")
            except Exception:
                pass

        try:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            print("Global listener failed:", e)

    def next_song(self):
        old_index = self.song_index
        n = len(self.playlist)
        for _ in range(n):
            self.song_index = (self.song_index + 1) % n
            if self.playlist[self.song_index]:
                self.song = self.playlist[self.song_index]
                self.note_index = 0
                self.frozen_note_index = 0
                print(f"Next song: {self.song_index+1}/{n}")
                return
        self.song_index = old_index

    def play_chord(self, chord):
        # in error mode, apply possible neighbor errors
        if self.mode == 4:
            chord = [self.apply_error(k) for k in chord]
        if self.mode == 1:
            for k in chord:
                self.press_key(k)
        elif self.mode == 2:
            press_threads = []
            for k in chord:
                delay = random.uniform(0.05, 0.1)
                t = threading.Timer(delay, self.press_key, args=[k])
                t.daemon = True
                t.start()
                press_threads.append(t)
            for t in press_threads:
                t.join()
        elif self.mode == 3:
            press_delay = random.uniform(0.01, 0.03)
            for k in chord:
                t = threading.Timer(press_delay, self.press_key, args=[k])
                t.daemon = True
                t.start()

    def release_chord(self, chord):
        if self.mode == 1:
            for k in chord:
                self.release_key(k)
        elif self.mode == 2:
            for k in chord:
                delay = random.uniform(0.05, 0.2)
                t = threading.Timer(delay, self.release_key, args=[k])
                t.daemon = True
                t.start()
        elif self.mode == 3:
            for k in chord:
                delay = random.uniform(0.02, 0.08)
                t = threading.Timer(delay, self.release_key, args=[k])
                t.daemon = True
                t.start()
        else:
            for k in chord:
                self.release_key(k)

    def play_song(self):
        # try to activate roblox once at start (best-effort)
        try:
            activate_roblox_window()
        except Exception:
            pass

        time.sleep(0.5)
        while True:
            try:
                if self.restart:
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.restart = False
                    self.release_all()
                    print("Restarted")
                    while self.hold_star and self.playing:
                        time.sleep(0.01)
                    time.sleep(0.01)
                    continue
                if not self.playing:
                    time.sleep(0.05)
                    continue
                current_index = self.frozen_note_index if self.freeze_note else self.note_index
                if current_index >= len(self.song):
                    time.sleep(0.05)
                    continue
                char = self.song[current_index]
                if self.skip_notes > 0 and not self.freeze_note:
                    if char == "[":
                        end = self.song.find("]", current_index)
                        if end != -1:
                            self.note_index = end + 1
                        else:
                            self.note_index += 1
                    else:
                        self.note_index += 1
                    self.skip_notes -= 1
                    continue
                if char.isspace():
                    if not self.freeze_note:
                        self.note_index += 1
                    continue
                # wait for pedal hold (if program configured so) — keep semantics from original
                # but we proceed regardless of pedal — only hold affects sustain behavior
                if char == "[":
                    end = self.song.find("]", current_index)
                    if end == -1:
                        if not self.freeze_note:
                            self.note_index += 1
                        continue
                    chord = list(self.song[current_index+1:end])
                else:
                    chord = [char]
                if self.freeze_note:
                    if self.start_delay > 0:
                        time.sleep(self.start_delay)
                    self.play_chord(chord)
                    while self.hold_star and self.playing and not self.restart:
                        time.sleep(0.05)
                    self.release_chord(chord)
                    continue
                if self.start_delay > 0:
                    time.sleep(self.start_delay)
                self.play_chord(chord)
                while self.hold_star and self.playing and not self.restart:
                    time.sleep(0.01)
                self.release_chord(chord)
                if not self.freeze_note:
                    if char == "[":
                        self.note_index = end + 1
                    else:
                        self.note_index += 1
                time.sleep(0.001)
            except Exception as e:
                print("Main loop error:", e)
                time.sleep(0.1)

# ---------------- GUI ----------------
class TitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None, title_text="AstraKeys — by black"):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setObjectName("titlebar")
        self.init_ui(title_text)
        self.setMouseTracking(True)

    def init_ui(self, title_text):
        gold = "#d4af37"
        soft_gold = "#ffd86a"
        text = "#f5f3f1"

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        self.title = QtWidgets.QLabel(title_text)
        self.title.setStyleSheet("font-weight:600; font-size:14px; color: %s;" % soft_gold)
        layout.addWidget(self.title)
        layout.addStretch()

        # minimize button
        self.btn_min = QtWidgets.QPushButton("—")
        self.btn_min.setFixedSize(36, 28)
        self.btn_min.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_min.setObjectName("btn_min")
        self.btn_min.setToolTip("Свернуть")
        layout.addWidget(self.btn_min)

        # close button
        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setToolTip("Закрыть")
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

        # style
        self.setStyleSheet(f"""
            QWidget#titlebar{{background: transparent;}}
            QPushButton#btn_min, QPushButton#btn_close {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton#btn_min:hover {{ background: rgba(212,175,55,0.08); }}
            QPushButton#btn_close:hover {{ background: rgba(255,80,80,0.12); }}
        """)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.parent.start_drag(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        pass

class BotGUI(QtWidgets.QWidget):
    def __init__(self, bot: RobloxPianoBot):
        super().__init__()
        self.bot = bot
        # make frameless, translucent background (for rounded corners), and stay-on-top
        self.setWindowTitle("AstraKeys — by black")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowSystemMenuHint, True)
        self.drag_pos = None

        # load icon if available
        ico_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico') if '__file__' in globals() else 'assets/icon.ico'
        if os.path.exists(ico_path):
            try:
                self.setWindowIcon(QtGui.QIcon(ico_path))
            except Exception:
                pass

        # UI
        self.init_ui()

        # status updater
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.refresh_status)
        self.updater.start(150)

    def init_ui(self):
        # colors
        dark = '#0b0b0b'
        panel = 'rgba(18,18,18,0.85)'
        gold = '#d4af37'
        soft_gold = '#ffd86a'
        text = '#f5f3f1'

        # main layout container with padding to simulate rounded corners
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        # central widget (rounded rectangle)
        self.central = QtWidgets.QFrame()
        self.central.setObjectName("central_frame")
        self.central.setStyleSheet(f"""
            QFrame#central_frame {{
                background: {dark};
                border-radius: 12px;
            }}
        """)
        central_layout = QtWidgets.QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 10)
        central_layout.setSpacing(8)

        # title bar (top draggable)
        self.titlebar = TitleBar(self, title_text=f"AstraKeys — by black")
        self.titlebar.btn_close.clicked.connect(self.close)
        self.titlebar.btn_min.clicked.connect(self.showMinimized)
        central_layout.addWidget(self.titlebar)

        # subtitle
        subtitle = QtWidgets.QLabel("Solar Gold · Black Onyx · Nebula")
        subtitle.setStyleSheet(f"color: {soft_gold}; font-size:12px; margin-left:14px;")
        central_layout.addWidget(subtitle)

        # song input
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText("Вставьте текст песни сюда и нажмите 'Добавить'")
        self.song_input.setFixedHeight(110)
        self.song_input.setStyleSheet(f"background: {panel}; border-radius:8px; padding:8px; color:{text};")
        central_layout.addWidget(self.song_input)

        # add button
        add_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Добавить песню")
        self.add_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.add_btn.setFixedHeight(36)
        self.add_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color:{text};")
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        central_layout.addLayout(add_row)
        self.add_btn.clicked.connect(self.add_song_from_input)

        # controls row
        row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start / Pause (F1)")
        self.next_btn = QtWidgets.QPushButton("Next Song (F8)")
        self.prev_mode_btn = QtWidgets.QPushButton("Prev Mode (F5)")
        self.next_mode_btn = QtWidgets.QPushButton("Next Mode (F7)")
        for btn in (self.start_btn, self.next_btn, self.prev_mode_btn, self.next_mode_btn):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(36)
            btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
            row.addWidget(btn)
        central_layout.addLayout(row)

        # song list and status
        mid = QtWidgets.QHBoxLayout()
        leftcol = QtWidgets.QVBoxLayout()
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setStyleSheet(f"background: {panel}; border-radius:10px; padding:6px; color:{text};")
        for i, s in enumerate(self.bot.playlist):
            self.song_list.addItem(f"Song {i+1} — {len(s)} chars")
        self.song_list.setCurrentRow(self.bot.song_index)
        leftcol.addWidget(self.song_list)

        list_controls = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.remove_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.remove_btn.setFixedHeight(30)
        self.remove_btn.setStyleSheet("border-radius:6px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
        list_controls.addWidget(self.remove_btn)
        list_controls.addStretch()
        leftcol.addLayout(list_controls)
        self.remove_btn.clicked.connect(self.remove_selected)

        mid.addLayout(leftcol, 2)

        right = QtWidgets.QVBoxLayout()
        self.status_label = QtWidgets.QLabel("Status: Idle")
        self.mode_label = QtWidgets.QLabel("Mode: 1")
        self.pos_label = QtWidgets.QLabel("Pos: 0")
        for lbl in (self.status_label, self.mode_label, self.pos_label):
            lbl.setStyleSheet("color: %s;" % text)
            right.addWidget(lbl)

        # progress bar for updates
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        mid.addLayout(right, 1)
        central_layout.addLayout(mid)

        # bottom controls
        bottom = QtWidgets.QHBoxLayout()
        self.delay_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.delay_slider.setMinimum(0)
        self.delay_slider.setMaximum(200)
        self.delay_slider.setValue(int(self.bot.start_delay * 1000))
        self.delay_label = QtWidgets.QLabel(f"Start Delay: {self.bot.start_delay:.3f}s")
        self.delay_label.setStyleSheet("color: %s;" % text)
        bottom.addWidget(self.delay_label)
        bottom.addWidget(self.delay_slider)
        central_layout.addLayout(bottom)

        # mode combo
        mode_row = QtWidgets.QHBoxLayout()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["1 - Ровный", "2 - Живой", "3 - Гибридный", "4 - Ошибочный (5%)"])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.setStyleSheet(f"background: {panel}; color:{text}; border-radius:6px; padding:6px;")
        mode_row.addWidget(QtWidgets.QLabel("Mode:"))
        mode_row.addWidget(self.mode_combo)
        central_layout.addLayout(mode_row)

        help_label = QtWidgets.QLabel("F1 Start/Pause | F2 Restart | F3 Skip25 | F4 Exit | F5 PrevMode | F7 NextMode | F8 NextSong")
        help_label.setStyleSheet("color: #9b9b9b;")
        central_layout.addWidget(help_label)

        # Update check button row
        update_row = QtWidgets.QHBoxLayout()
        self.check_update_btn = QtWidgets.QPushButton("Проверить обновление")
        self.check_update_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.check_update_btn.setFixedHeight(36)
        self.check_update_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color: %s;" % text)
        update_row.addStretch()
        update_row.addWidget(self.check_update_btn)
        update_row.addStretch()
        central_layout.addLayout(update_row)
        self.check_update_btn.clicked.connect(self.gui_check_update)

        # footer with signature and small version/date on right
        footer = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("AstraKeys — by black")
        self.signature.setStyleSheet(f"color: {gold};")

        build_date = datetime.now().strftime("%d.%m.%Y")
        self.version_label = QtWidgets.QLabel(f"v{CURRENT_VERSION} · {build_date}")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.28); font-size: 11px; margin-right: 8px;")

        footer.addWidget(self.signature)
        footer.addStretch()
        footer.addWidget(self.version_label)
        central_layout.addLayout(footer)

        self.central.setLayout(central_layout)
        outer.addWidget(self.central)
        self.setLayout(outer)

        # global stylesheet for subtle glow
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            QSlider::groove:horizontal{{height:8px; background: rgba(255,255,255,0.03); border-radius:4px;}}
            QSlider::handle:horizontal{{background: {soft_gold}; width:14px; border-radius:7px;}}
            QComboBox{{padding:6px; border-radius:6px;}}
            QProgressBar{{background: rgba(255,255,255,0.02); border-radius:8px; text-align:center;}}
            QProgressBar::chunk{{background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gold}, stop:1 {soft_gold}); border-radius:8px;}}
        """)

        # connect signals
        self.add_btn.clicked.connect(self.add_song_from_input)
        self.start_btn.clicked.connect(self.toggle_start)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_mode_btn.clicked.connect(self.prev_mode)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.song_list.itemDoubleClicked.connect(self.select_song)
        self.delay_slider.valueChanged.connect(self.delay_changed)
        self.mode_combo.currentIndexChanged.connect(self.mode_combo_changed)

    # dragging helpers (drag only via top titlebar)
    def start_drag(self, global_pos: QtCore.QPoint):
        self.drag_pos = global_pos - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            newpos = event.globalPosition().toPoint() - self.drag_pos
            self.move(newpos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    # UI interactions
    def add_song_from_input(self):
        text = self.song_input.toPlainText().strip()
        if text:
            sanitized = self.bot.sanitize_song(text)
            self.bot.playlist.append(sanitized)
            self.song_list.addItem(f"Song {len(self.bot.playlist)} — {len(sanitized)} chars")
            print("Song added")
            self.song_input.clear()

    def remove_selected(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            self.bot.playlist.pop(row)
            self.song_list.takeItem(row)
            if self.bot.song_index >= len(self.bot.playlist):
                self.bot.song_index = max(0, len(self.bot.playlist) - 1)
            self.song_list.setCurrentRow(self.bot.song_index)

    def toggle_start(self):
        self.bot.playing = not self.bot.playing
        self.refresh_status()

    def next_song(self):
        self.bot.next_song()
        self.song_list.setCurrentRow(self.bot.song_index)
        self.refresh_status()

    def prev_mode(self):
        self.bot.mode = self.bot.mode - 1 if self.bot.mode > 1 else 4
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.refresh_status()

    def next_mode(self):
        self.bot.mode = self.bot.mode + 1 if self.bot.mode < 4 else 1
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.refresh_status()

    def select_song(self, item):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            self.bot.song_index = row
            self.bot.song = self.bot.playlist[row]
            self.bot.note_index = 0
            self.bot.frozen_note_index = 0
            print(f"GUI: selected {row+1}")

    def delay_changed(self, val):
        self.bot.start_delay = val / 1000.0
        self.delay_label.setText(f"Start Delay: {self.bot.start_delay:.3f}s")

    def mode_combo_changed(self, idx):
        self.bot.mode = idx + 1
        self.refresh_status()

    def refresh_status(self):
        st = "Playing" if self.bot.playing else "Paused"
        self.status_label.setText(f"Status: {st}")
        mode_names = {1: "Ровный", 2: "Живой", 3: "Гибридный", 4: "Ошибочный"}
        self.mode_label.setText(f"Mode: {self.bot.mode} — {mode_names.get(self.bot.mode,'?')}")
        # protect against empty song
        try:
            self.pos_label.setText(f"Pos: {self.bot.note_index}/{len(self.bot.song)}")
        except Exception:
            self.pos_label.setText("Pos: 0/0")
        if self.mode_combo.currentIndex() != self.bot.mode - 1:
            self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)

    # ---------------- Update flow (GUI-triggered) ----------------
    def gui_check_update(self):
        # non-blocking: start thread to check and (optionally) download
        self.check_update_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self):
        try:
            info, err = fetch_latest_release_info()
            if err or not info:
                self._show_message_box("Ошибка", f"Не удалось получить информацию о релизах: {err or 'unknown'}")
                self._update_ui_after_check(False)
                return
            latest_tag = (info.get("tag_name") or info.get("name") or "").strip()
            latest_version = latest_tag.lstrip("v").strip()
            if not latest_version:
                # try parse from body
                body = info.get("body", "")
                m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", body)
                if m:
                    latest_version = m.group(1)
            if not latest_version:
                self._show_message_box("Ошибка", "Не удалось определить номер версии релиза.")
                self._update_ui_after_check(False)
                return
            # compare versions simply by string (assumes semantic versioning with same format)
            if latest_version == CURRENT_VERSION:
                self._show_message_box("Обновления", "Установлена последняя версия.")
                self._update_ui_after_check(False)
                return
            # found newer version -> find asset
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self._show_message_box("Обновления", "Обнаружена новая версия, но нужный файл не найден в релизе.")
                self._update_ui_after_check(False)
                return
            # download asset to temporary file
            tmp_name = "AstraKeys_update_tmp.exe"
            # download with progress updating
            def prog_cb(pct):
                # ensure called in main thread via signal? We'll schedule via Qt's singleShot
                QtCore.QTimer.singleShot(0, lambda: self.progress.setValue(pct))
            ok, derr = download_asset_to_file(asset_url, tmp_name, progress_callback=prog_cb)
            if not ok:
                self._show_message_box("Ошибка", f"Ошибка скачивания: {derr}")
                self._update_ui_after_check(False)
                try:
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception:
                    pass
                return
            # perform replacement
            is_frozen = getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe")
            try:
                perform_replacement_and_restart(tmp_name, ASSET_NAME, is_frozen)
            except Exception as e:
                self._show_message_box("Ошибка", f"Не удалось заменить файл при обновлении: {e}")
                self._update_ui_after_check(False)
                return
            # If replacement initiated a restart via batch, current process will exit above.
            # If running as script, perform_replacement_and_restart will execv and won't return.
        finally:
            # only reached if something prevented restart; re-enable UI
            QtCore.QTimer.singleShot(0, lambda: self._update_ui_after_check(False))

    def _update_ui_after_check(self, busy=True):
        # called in main thread
        self.check_update_btn.setEnabled(True)
        if not busy:
            self.progress.setVisible(False)
            self.progress.setValue(0)

    def _show_message_box(self, title, text):
        # show a simple message box in main thread
        def show():
            mb = QtWidgets.QMessageBox(self)
            mb.setWindowTitle(title)
            mb.setText(text)
            mb.exec()
        QtCore.QTimer.singleShot(0, show)

# ---------------- Main runner ----------------
if __name__ == "__main__":
    # start update-check thread at startup (optional fast initial check could be disabled)
    # The user asked manual update via button; we still start a background thread that does nothing heavy.
    # To avoid unexpected auto-download we won't call auto_update_github automatically here.
    # start_update_thread()  # intentionally not called automatically

    # Prepare playlist
    playlist = [
        # keep small default songs; user can add songs via GUI
        r"[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe]",
        r"l--l--",
        r"fffff[4qf]spsfspsg"
    ]

    # create bot and start player thread
    bot = RobloxPianoBot(playlist)
    player_thread = threading.Thread(target=bot.play_song, daemon=True)
    player_thread.start()

    # start Qt app
    app = QtWidgets.QApplication(sys.argv)

    # load Montserrat font if available
    try:
        font_db = QtGui.QFontDatabase()
        if 'Montserrat' not in font_db.families():
            local_ttf = os.path.join(os.path.dirname(__file__) if '__file__' in globals() else '.', 'Montserrat-Regular.ttf')
            if os.path.exists(local_ttf):
                font_db.addApplicationFont(local_ttf)
    except Exception:
        pass

    gui = BotGUI(bot)

    # fade-in animation
    try:
        gui.setWindowOpacity(0.0)
        gui.show()
        anim = QtCore.QPropertyAnimation(gui, b"windowOpacity")
        anim.setDuration(380)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        anim.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    except Exception:
        gui.show()

    # ensure app keeps running
    sys.exit(app.exec())
