# AstraKeys_v1.1.1 — Black Onyx / Solar Gold / Nebula blend
# Frameless window (draggable by top bar), minimal buttons (—, ×)
# Auto-updater: GitHub Releases integration included
# NOTE: Put your icon at assets/icon.ico and ensure GITHUB_OWNER / GITHUB_REPO are correct.

CURRENT_VERSION = "1.1.1"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"

# ---------------- imports ----------------
import time
import threading
import sys
import re
import random
import os
import winsound
from datetime import datetime

# win32gui optional — used to find/activate Roblox window; fallback if missing
try:
    import win32gui
    import win32con
except Exception:
    win32gui = None
    win32con = None

from pynput.keyboard import Controller, Key, Listener

# network and GUI
import requests
from PyQt6 import QtWidgets, QtCore, QtGui

# ---------------- Auto-update (GitHub Releases) ----------------
def auto_update_github():
    """
    Checks the latest GitHub release (owner/repo) and if a newer version is present,
    downloads the ASSET_NAME asset and replaces the running exe/script.
    Works for both frozen executables (creates update.bat) and .py scripts (replaces file).
    """
    try:
        api = f"https://api.github.com/repos/SMisha2/AstraKeys/releases/latest"
        r = requests.get(api, timeout=8)
        if r.status_code != 200:
            return
        data = r.json()
        latest_tag = (data.get("tag_name") or data.get("name") or "").strip()
        latest_version = latest_tag.lstrip("v").strip()
        if not latest_version:
            body = data.get("body", "")
            m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", body)
            if m:
                latest_version = m.group(1)
        if not latest_version or latest_version == CURRENT_VERSION:
            return
        asset_url = None
        for a in data.get("assets", []):
            if a.get("name", "") == ASSET_NAME:
                asset_url = a.get("browser_download_url")
                break
        if not asset_url:
            print("Auto-update: release found but asset not present.")
            return
        print(f"Auto-update: new version {latest_version} found — downloading...")
        dl = requests.get(asset_url, timeout=30, stream=True)
        if dl.status_code != 200:
            print("Auto-update: download failed", dl.status_code)
            return
        new_name = "AstraKeys_new.exe"
        total = dl.headers.get("content-length")
        if total:
            total = int(total)
            written = 0
            with open(new_name, "wb") as f:
                for chunk in dl.iter_content(1024 * 64):
                    if chunk:
                        f.write(chunk)
                        written += len(chunk)
                        pct = written * 100 // total
                        print(f"\rDownloading... {pct}% ", end="", flush=True)
            print()
        else:
            with open(new_name, "wb") as f:
                f.write(dl.content)
        # If running as frozen exe, create and run batch to replace
        if getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe"):
            bat = f"""@echo off
timeout /t 1 /nobreak >nul
taskkill /f /im "{os.path.basename(sys.argv[0])}" >nul 2>&1
del "{os.path.basename(sys.argv[0])}" >nul 2>&1
rename "{new_name}" "{ASSET_NAME}" >nul 2>&1
start "" "{ASSET_NAME}"
del "%~f0" & exit
"""
            with open("update.bat", "w", encoding="utf-8") as f:
                f.write(bat)
            try:
                os.startfile("update.bat")
            except Exception:
                os.system("start update.bat")
            sys.exit(0)
        else:
            # running as script: replace and restart
            target = os.path.abspath(sys.argv[0])
            try:
                backup = target + ".bak"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(target, backup)
            except Exception:
                pass
            try:
                os.rename(new_name, target)
            except Exception:
                with open(target, "wb") as f:
                    f.write(open(new_name, "rb").read())
                os.remove(new_name)
            print("Auto-update: script updated — restarting.")
            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable, target])
    except Exception as e:
        print("Auto-update error:", e)

def start_update_thread():
    def worker():
        try:
            time.sleep(1.2)
            auto_update_github()
        except Exception:
            pass
    t = threading.Thread(target=worker, daemon=True)
    t.start()

# ---------------- SONGS (small defaults) ----------------
SONG1 = r"""
[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe]
"""
SONG2 = r"""
l--l--
"""
SONG3 = r"""
fffff[4qf]spsfspsg
"""

ROBLOX_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnm"

# ---------------- Bot ----------------
class RobloxPianoBot:
    def __init__(self, playlist, bpm=100):
        self.keyboard = Controller()
        self.roblox_window = None
        self.lock = threading.Lock()
        self.playlist = [self.sanitize_song(song) for song in playlist if self.sanitize_song(song)]
        if not self.playlist:
            print("⚠️ PlayList empty after filtering!")
            sys.exit()
        self.song_index = 0
        self.song = self.playlist[self.song_index]
        self.bpm = bpm
        self.playing = False
        self.restart = False
        self.skip_notes = 0
        self.note_index = 0
        self.hold_star = False
        self.freeze_note = False
        self.frozen_note_index = 0
        self.mode = 1
        self.start_delay = 0.03
        self.active_keys = set()
        print("🎹 AstraKeys Bot initialized")
        print("▶ F1 Play/Pause | F2 Restart | F3 Skip25 | F4 Exit")
        print("⭐ * Hold pedal | ❄ F6 Freeze | F7 NextMode | F5 PrevMode | F8 NextSong")
        threading.Thread(target=self.listen_keys, daemon=True).start()

    def sanitize_song(self, song):
        return re.sub(r"[^a-zA-Z0-9\[\]\s]","", song)

    def find_roblox_window(self):
        if not win32gui:
            return None
        try:
            self.roblox_window = None
            def callback(hwnd, extra):
                try:
                    if "Roblox" in win32gui.GetWindowText(hwnd):
                        self.roblox_window = hwnd
                except Exception:
                    pass
            win32gui.EnumWindows(callback, None)
        except Exception:
            return None
        return self.roblox_window

    def activate_roblox(self):
        if not win32gui:
            return False
        if self.find_roblox_window():
            try:
                win32gui.ShowWindow(self.roblox_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.roblox_window)
            except Exception:
                pass
            return True
        return False

    def press_key(self, key):
        with self.lock:
            if key not in self.active_keys:
                try:
                    self.keyboard.press(key)
                except Exception:
                    pass
                self.active_keys.add(key)

    def release_key(self, key):
        with self.lock:
            if key in self.active_keys:
                try:
                    self.keyboard.release(key)
                except Exception:
                    pass
                self.active_keys.discard(key)

    def release_all(self):
        with self.lock:
            for k in list(self.active_keys):
                try:
                    self.keyboard.release(k)
                except:
                    pass
            self.active_keys.clear()

    def apply_error(self, k):
        try:
            if k.lower() in ["1","m"]:
                return k
            if random.random() < 0.05:
                c = k.lower()
                if c in ROBLOX_KEYS and len(c) == 1:
                    i = ROBLOX_KEYS.index(c)
                    if i == 0:
                        return ROBLOX_KEYS[1]
                    if i == len(ROBLOX_KEYS)-1:
                        return ROBLOX_KEYS[-2]
                    return ROBLOX_KEYS[i + random.choice([-1,1])]
        except Exception:
            pass
        return k

    def listen_keys(self):
        def on_press(key):
            try:
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
                    sys.exit()
                elif hasattr(key, "char") and key.char == "*":
                    self.hold_star = True
                    print("Pedal down")
                elif hasattr(key, "char") and key.char == "-":
                    self.start_delay = max(0.0, self.start_delay - 0.01)
                    print(f"Delay {self.start_delay}")
                elif hasattr(key, "char") and key.char == "=":
                    self.start_delay = min(0.2, self.start_delay + 0.01)
                    print(f"Delay {self.start_delay}")
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
            except Exception as e:
                print("Key error:", e)

        def on_release(key):
            try:
                if hasattr(key, "char") and key.char == "*":
                    self.hold_star = False
                    print("Pedal up")
            except:
                pass

        with Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

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
        self.activate_roblox()
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
                while not self.hold_star and self.playing and not self.restart:
                    time.sleep(0.01)
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

# ---------------- GUI (frameless top-drag) ----------------
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
        # top-level frameless + translucent background to allow rounding effect
        self.setWindowTitle("AstraKeys — by black")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowSystemMenuHint, True)
        self.drag_pos = None

        # load icon if available
        ico_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico') if '__file__' in globals() else 'assets/icon.ico'
        if os.path.exists(ico_path):
            try:
                self.setWindowIcon(QtGui.QIcon(ico_path))
            except Exception:
                pass

        self.init_ui()
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.refresh_status)
        self.updater.start(150)

        try:
            winsound.Beep(1200, 100)
        except:
            pass

    def init_ui(self):
        # colors
        dark = '#0b0b0b'
        panel = 'rgba(18,18,18,0.85)'
        gold = '#d4af37'
        soft_gold = '#ffd86a'
        text = '#f5f3f1'
        nebula = 'qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(60,20,80,0.06), stop:1 rgba(5,20,60,0.04))'

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
        for i,s in enumerate(self.bot.playlist):
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

        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        mid.addLayout(right,1)
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

        # footer with signature and small version/date on right
        footer = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("AstraKeys — by black")
        self.signature.setStyleSheet(f"color: {gold};")

        build_date = datetime.now().strftime("%Y-%m-%d")
        self.version_label = QtWidgets.QLabel(f"v{CURRENT_VERSION} · {build_date}")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.28); font-size: 11px; margin-right: 8px;")

        footer.addWidget(self.signature)
        footer.addStretch()
        footer.addWidget(self.version_label)
        central_layout.addLayout(footer)

        self.central.setLayout(central_layout)
        outer.addWidget(self.central)
        self.setLayout(outer)

        # stylesheet for glow / subtle gradients
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            QSlider::groove:horizontal{{height:8px; background: rgba(255,255,255,0.03); border-radius:4px;}}
            QSlider::handle:horizontal{{background: {soft_gold}; width:14px; border-radius:7px;}}
            QComboBox{{padding:6px; border-radius:6px;}}
            QProgressBar{{background: rgba(255,255,255,0.02); border-radius:8px; text-align:center;}}
            QProgressBar::chunk{{background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gold}, stop:1 {soft_gold}); border-radius:8px;}}
        """)

        # connections
        self.add_btn.clicked.connect(self.add_song_from_input)
        self.start_btn.clicked.connect(self.toggle_start)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_mode_btn.clicked.connect(self.prev_mode)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.song_list.itemDoubleClicked.connect(self.select_song)
        self.delay_slider.valueChanged.connect(self.delay_changed)
        self.mode_combo.currentIndexChanged.connect(self.mode_combo_changed)

    # dragging helpers
    def start_drag(self, global_pos: QtCore.QPoint):
        self.drag_pos = global_pos - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            newpos = event.globalPosition().toPoint() - self.drag_pos
            self.move(newpos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    # UI actions
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
        self.pos_label.setText(f"Pos: {self.bot.note_index}/{len(self.bot.song)}")
        if self.mode_combo.currentIndex() != self.bot.mode - 1:
            self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)


# ---------------- Main runner ----------------
if __name__ == "__main__":
    # start updater thread
    start_update_thread()

    playlist = [SONG1, SONG2, SONG3]
    bot = RobloxPianoBot(playlist)
    player_thread = threading.Thread(target=bot.play_song, daemon=True)
    player_thread.start()

    app = QtWidgets.QApplication(sys.argv)

    # load Montserrat if present
    try:
        font_db = QtGui.QFontDatabase()
        if 'Montserrat' not in font_db.families():
            local_ttf = os.path.join(os.path.dirname(__file__) if '__file__' in globals() else '.', 'Montserrat-Regular.ttf')
            if os.path.exists(local_ttf):
                font_db.addApplicationFont(local_ttf)
    except Exception:
        pass

    gui = BotGUI(bot)

    # fade-in
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

    sys.exit(app.exec())
