# AstraKeys_v1.1.5 — Black Onyx / Solar Gold / Nebula blend
# by SMisha2
# Features: Fixed freeze mode, working chords and pedal, instant mode 1, smooth operation
CURRENT_VERSION = "1.1.5"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
# ---------------- imports ----------------
import os
import sys
import time
import threading
import re
import random
from datetime import datetime
import webbrowser
import subprocess
# optional win32
try:
    import win32gui
    import win32con
    import win32process
except Exception:
    win32gui = None
    win32con = None
    win32process = None
try:
    from pynput.keyboard import Controller, Key, Listener, KeyCode
except Exception:
    Controller = None
    Key = None
    Listener = None
    KeyCode = None
import requests
try:
    from PyQt6 import QtWidgets, QtCore, QtGui
except Exception:
    raise RuntimeError("PyQt6 is required. Install via: pip install PyQt6")
# ---------------- constants ----------------
PEDAL_KEYS = {"*", "[", "]"}
ROBLOX_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnm"
# ---------------- Keyboard helpers ----------------
def is_valid_key(key):
    """Check if key is valid for pynput"""
    if not key or not isinstance(key, str) or len(key) != 1:
        return False
    return key.isalnum() or key in "!@#$%^&*()_+-=[]{};':\",./<>?\\|`~"
# ---------------- Auto-update helpers ----------------
def download_asset_to_file(url, dest_path, progress_callback=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = r.headers.get("content-length")
                if total is None:
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
                if os.path.getsize(dest_path) == total:
                    return True, None
                else:
                    if attempt < max_retries - 1:
                        print(f"Download incomplete. Retrying... ({attempt+1})")
                        time.sleep(1)
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        continue
                    return False, "File size mismatch"
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Download failed (attempt {attempt+1}): {e}. Retrying...")
                time.sleep(2)
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            else:
                return False, str(e)
    return False, "Max retries exceeded"
def perform_replacement_and_restart(new_file, target_name, is_frozen):
    try:
        if is_frozen or sys.argv[0].lower().endswith(".exe"):
            current_exec = os.path.basename(sys.argv[0])
            bat_content = f"""@echo off
:kill_loop
taskkill /f /im "{current_exec}" >nul 2>&1
timeout /t 1 >nul
tasklist | findstr /i "{current_exec}" >nul && goto kill_loop
del "{current_exec}" >nul 2>&1
rename "{new_file}" "{target_name}" >nul 2>&1
start "" "{target_name}"
del "%~f0" >nul 2>&1 & exit
"""
            with open("update.bat", "w", encoding="utf-8") as f:
                f.write(bat_content)
            try:
                os.startfile("update.bat")
            except:
                os.system("start update.bat")
            sys.exit(0)
        else:
            target = os.path.abspath(sys.argv[0])
            try:
                backup = target + ".bak"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(target, backup)
            except:
                pass
            try:
                os.replace(new_file, target)
            except:
                with open(new_file, "rb") as src, open(target, "wb") as dst:
                    dst.write(src.read())
                os.remove(new_file)
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
def version_tuple(v):
    try:
        return tuple(map(int, v.split(".")))
    except:
        return (0, 0, 0)
# ---------------- Roblox helpers ----------------
def find_roblox_window():
    if not win32gui:
        return None
    try:
        hwnd_found = None
        def cb(hwnd, extra):
            nonlocal hwnd_found
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Roblox" in title:
                        hwnd_found = hwnd
            except:
                pass
        win32gui.EnumWindows(cb, None)
        return hwnd_found
    except:
        return None
def activate_roblox_window():
    hwnd = find_roblox_window()
    if hwnd:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except:
            pass
    return False
def bring_roblox_to_front():
    """Bring Roblox window to front without stealing focus"""
    hwnd = find_roblox_window()
    if hwnd:
        try:
            current_fg = win32gui.GetForegroundWindow()
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            if current_fg and current_fg != hwnd:
                win32gui.SetWindowPos(current_fg, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            return True
        except:
            pass
    return False
# ---------------- Bot core ----------------
class RobloxPianoBot:
    def __init__(self, playlist_with_names, bpm=100):
        self.keyboard = Controller() if Controller else None
        self.lock = threading.Lock()
        self.playlist = []
        for name, song in playlist_with_names:
            sanitized = self.sanitize_song(song)
            if sanitized:
                self.playlist.append((name, sanitized))
        if not self.playlist:
            print("⚠️ Playlist empty!")
            sys.exit(1)
        self.song_index = 0
        self.song_name, self.song = self.playlist[self.song_index]
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
        self.last_played_time = time.time()
        print("🎹 AstraKeys Bot initialized")
        print("▶ F1 Play/Pause | F2 Restart | F3 Skip25 | F4 Exit")
        print("⭐ * - Pedal | F6 Freeze Note | F7 Next Mode | F5 Prev Mode | F8 Next Song | F10 Force Roblox")
        if Listener:
            threading.Thread(target=self.listen_keys, daemon=True).start()
    def sanitize_song(self, song):
        if not song:
            return ""
        white = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
        black = "!@$%^*()_+-=[]{};':\",./<>?\\|`~&"
        allowed = white + black + " \t\n\r"
        return ''.join(ch for ch in song if ch in allowed)
    def is_key_valid(self, key):
        """Check if key can be pressed safely"""
        if not key or not isinstance(key, str):
            return False
        problematic = ['`', '~', '\\', '|']
        if key in problematic:
            return False
        return True
    def press_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            if not self.is_key_valid(key):
                return
            if key not in self.active_keys:
                try:
                    self.keyboard.press(key)
                    self.active_keys.add(key)
                except Exception as e:
                    print(f"Error pressing key '{key}': {e}")
    def release_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            if not self.is_key_valid(key):
                return
            if key in self.active_keys:
                try:
                    self.keyboard.release(key)
                    self.active_keys.discard(key)
                except Exception as e:
                    print(f"Error releasing key '{key}': {e}")
    def release_all(self):
        with self.lock:
            if not self.keyboard:
                self.active_keys.clear()
                return
            for k in list(self.active_keys):
                try:
                    self.keyboard.release(k)
                except:
                    pass
            self.active_keys.clear()
    def apply_error(self, k):
        try:
            if len(k) != 1:
                return k
            c = k.lower()
            if c not in ROBLOX_KEYS:
                return k
            if c in ["1", "m"]:
                return k
            if random.random() < 0.05:
                i = ROBLOX_KEYS.index(c)
                if i == 0:
                    return ROBLOX_KEYS[1]
                if i == len(ROBLOX_KEYS) - 1:
                    return ROBLOX_KEYS[-2]
                return ROBLOX_KEYS[i + random.choice([-1, 1])]
            return k
        except:
            return k
    def listen_keys(self):
        def on_press(key):
            try:
                # Enhanced bracket detection
                key_char = getattr(key, 'char', None)
                is_bracket = False
                
                # Check for bracket keys directly
                if hasattr(key, 'vk'):
                    # VK_LEFTBRACKET = 219, VK_RIGHTBRACKET = 221
                    if key.vk in (219, 221):
                        is_bracket = True
                elif isinstance(key, KeyCode) and hasattr(key, 'char') and key.char in ["[", "]", "{", "}"]:
                    is_bracket = True
                elif key_char in ["[", "]"]:
                    is_bracket = True
                
                if key == Key.f7:
                    old = self.mode
                    self.mode = self.mode + 1 if self.mode < 4 else 1
                    print(f"Mode: {self.mode} (was {old})")
                elif key == Key.f5:
                    old = self.mode
                    self.mode = self.mode - 1 if self.mode > 1 else 4
                    print(f"Mode: {self.mode} (was {old})")
                elif key == Key.f1:
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
                elif key == Key.f8:
                    self.next_song()
                elif key == Key.f10:
                    activate_roblox_window()
                # Check for pedal keys including brackets
                elif (key_char in PEDAL_KEYS) or is_bracket:
                    self.hold_star = True
                    key_repr = key_char or ("[" if hasattr(key, 'vk') and key.vk == 219 else "]")
                    print(f"Pedal down ({key_repr})")
            except Exception as e:
                print(f"Error in on_press: {e}")
                pass
        def on_release(key):
            try:
                # Enhanced bracket detection for release too
                key_char = getattr(key, 'char', None)
                is_bracket = False
                
                if hasattr(key, 'vk'):
                    if key.vk in (219, 221):
                        is_bracket = True
                elif isinstance(key, KeyCode) and hasattr(key, 'char') and key.char in ["[", "]", "{", "}"]:
                    is_bracket = True
                elif key_char in ["[", "]"]:
                    is_bracket = True
                
                # Check for pedal keys including brackets
                if (key_char in PEDAL_KEYS) or is_bracket:
                    self.hold_star = False
                    key_repr = key_char or ("[" if hasattr(key, 'vk') and key.vk == 219 else "]")
                    print(f"Pedal up ({key_repr})")
            except Exception as e:
                print(f"Error in on_release: {e}")
                pass
        try:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            print("Listener failed:", e)
    def next_song(self):
        old_index = self.song_index
        n = len(self.playlist)
        for _ in range(n):
            self.song_index = (self.song_index + 1) % n
            if self.playlist[self.song_index][1]:
                self.song_name, self.song = self.playlist[self.song_index]
                self.note_index = 0
                self.frozen_note_index = 0
                print(f"Next song: {self.song_name} ({self.song_index+1}/{n})")
                return
        self.song_index = old_index
    def play_chord(self, chord):
        """Play chord with mode-specific timing"""
        if self.mode == 4:
            chord = [self.apply_error(k) for k in chord]
        if self.mode == 1:
            # No delay between notes in mode 1
            for k in chord:
                self.press_key(k)
        elif self.mode == 2:
            press_threads = []
            base_delay = 0.01
            for i, k in enumerate(chord):
                delay = base_delay + random.uniform(0.005, 0.02)
                t = threading.Timer(delay, self.press_key, args=[k])
                t.daemon = True
                t.start()
                press_threads.append(t)
            time.sleep(base_delay + 0.025)
        elif self.mode == 3:
            press_threads = []
            base_press_delay = random.uniform(0.002, 0.008)
            for i, k in enumerate(chord):
                press_delay = base_press_delay + (i * 0.003)
                t_press = threading.Timer(press_delay, self.press_key, args=[k])
                t_press.daemon = True
                t_press.start()
                press_threads.append(t_press)
            max_press_time = base_press_delay + (len(chord) * 0.003) + 0.002
            time.sleep(max_press_time)
    def release_chord(self, chord):
        """Release chord with mode-specific timing"""
        if not chord:
            return
        if self.mode == 1:
            # Instant release in mode 1
            for k in chord:
                self.release_key(k)
        elif self.mode == 2:
            for k in chord:
                delay = random.uniform(0.05, 0.2)
                t = threading.Timer(delay, self.release_key, args=[k])
                t.daemon = True
                t.start()
        elif self.mode == 3:
            base_release_delay = random.uniform(0.015, 0.04)
            for i, k in enumerate(chord):
                release_delay = base_release_delay + (i * 0.005)
                t_release = threading.Timer(release_delay, self.release_key, args=[k])
                t_release.daemon = True
                t_release.start()
        else:
            for k in chord:
                self.release_key(k)
    def play_song(self):
        time.sleep(0.5)
        last_pedal_state = False
        current_chord = None
        while True:
            try:
                if self.restart:
                    self.restart = False
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.release_all()
                    current_chord = None
                    print("Restarted")
                    while self.hold_star:
                        time.sleep(0.01)
                    time.sleep(0.1)
                    continue
                if not self.playing:
                    time.sleep(0.05)
                    continue
                # Handle F6 freeze
                current_index = self.frozen_note_index if self.freeze_note else self.note_index
                if current_index >= len(self.song):
                    time.sleep(0.05)
                    continue
                char = self.song[current_index]
                # Skip whitespace
                if char.isspace():
                    if not self.freeze_note:
                        self.note_index += 1
                    time.sleep(0.01)
                    continue
                # Handle F3 Skip25
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
                # Wait for pedal press to play next note/chord
                if not self.hold_star:
                    time.sleep(0.01)
                    continue
                # Parse chord or single note
                if char == "[":
                    end = self.song.find("]", current_index)
                    if end == -1:
                        chord = [char]
                        next_index = current_index + 1
                    else:
                        chord = list(self.song[current_index+1:end])
                        next_index = end + 1
                else:
                    chord = [char]
                    next_index = current_index + 1
                
                # Skip processing if this is a bracket that's being used as pedal
                if chord and chord[0] in ["[", "]"]:
                    if not self.freeze_note:
                        self.note_index = next_index
                    time.sleep(0.01)
                    continue
                
                # Activate Roblox before playing
                bring_roblox_to_front()
                time.sleep(0.01)  # Small delay to ensure window is active
                # Apply start delay if set
                if self.start_delay > 0:
                    time.sleep(self.start_delay)
                # Play the chord
                self.play_chord(chord)
                current_chord = chord
                print(f"Played: {chord} at pos {current_index}")
                # Keep holding the chord while pedal is pressed
                while self.hold_star and self.playing and not self.restart:
                    time.sleep(0.01)
                # Release the chord when pedal is released
                if current_chord:
                    self.release_chord(current_chord)
                    current_chord = None
                # Move to next note only if not frozen
                if not self.freeze_note:
                    self.note_index = next_index
                time.sleep(0.001)
            except Exception as e:
                print("Main loop error:", e)
                time.sleep(0.1)
# ---------------- About Dialog ----------------
class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе — AstraKeys")
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background: #0b0b0b;
                color: #f5f3f1;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 14px;
            }
            QLabel.title {
                font-size: 20px;
                font-weight: bold;
                color: #ffd86a;
            }
            QLabel.link {
                color: #7aa7ff;
                text-decoration: underline;
            }
            QPushButton {
                background: #1a1a1a;
                border: 1px solid #d4af37;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #252525;
            }
        """)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = QtWidgets.QLabel("AstraKeys")
        title.setProperty("class", "title")
        layout.addWidget(title, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        version = QtWidgets.QLabel(f"Версия: {CURRENT_VERSION}")
        version.setStyleSheet("color: #9b9b9b;")
        layout.addWidget(version, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        desc = QtWidgets.QLabel(
            "Программа для игры на пианино в Roblox\n"
            "Поддерживает чёрные и белые клавиши,\n"
            "автоматическое обновление и многое другое."
        )
        desc.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        link = QtWidgets.QLabel(f'<a href="{RELEASES_URL}" style="color:#7aa7ff;text-decoration:underline;">{RELEASES_URL}</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(link)
        author = QtWidgets.QLabel("Автор: SMisha2")
        author.setStyleSheet("color: #d4af37;")
        author.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)
        btn = QtWidgets.QPushButton("Закрыть")
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)
# ---------------- GUI ----------------
class BotGUI(QtWidgets.QWidget):
    def __init__(self, bot: RobloxPianoBot):
        super().__init__()
        self.bot = bot
        self.setWindowTitle("AstraKeys — by SMisha2")
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        # Default size and position
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        default_width = 700
        default_height = 550  # Slightly increased height for the new display area
        x = (screen.width() - default_width) // 2
        y = (screen.height() - default_height) // 2
        self.setGeometry(x, y, default_width, default_height)
        # Dragging variables
        self.dragging = False
        self.drag_position = None
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
        # Start Roblox keepalive thread
        self.roblox_thread = threading.Thread(target=self.roblox_keepalive, daemon=True)
        self.roblox_thread.start()
        self.check_internet_status()
    def init_ui(self):
        dark = '#0b0b0b'
        panel = 'rgba(18,18,18,0.85)'
        gold = '#d4af37'
        soft_gold = '#ffd86a'
        text = '#f5f3f1'
        # Main layout with margins for rounded corners
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)
        # Central frame with rounded corners
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
        # Title bar with buttons
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet(f"background: transparent;")
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.setContentsMargins(12, 0, 12, 0)
        title_layout.setSpacing(8)
        title_label = QtWidgets.QLabel("AstraKeys — by SMisha2")
        title_label.setStyleSheet(f"font-weight:600; font-size:14px; color: {soft_gold};")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        self.btn_about = QtWidgets.QPushButton("?")
        self.btn_about.setFixedSize(30, 28)
        self.btn_about.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_about.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(212,175,55,0.08);
            }}
        """)
        self.btn_about.setToolTip("О программе")
        title_layout.addWidget(self.btn_about)
        self.btn_min = QtWidgets.QPushButton("—")
        self.btn_min.setFixedSize(36, 28)
        self.btn_min.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_min.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(212,175,55,0.08);
            }}
        """)
        self.btn_min.setToolTip("Свернуть")
        title_layout.addWidget(self.btn_min)
        self.btn_max = QtWidgets.QPushButton("□")
        self.btn_max.setFixedSize(36, 28)
        self.btn_max.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_max.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(212,175,55,0.08);
            }}
        """)
        self.btn_max.setToolTip("Развернуть")
        title_layout.addWidget(self.btn_max)
        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255,80,80,0.12);
            }}
        """)
        self.btn_close.setToolTip("Закрыть")
        title_layout.addWidget(self.btn_close)
        self.title_bar.setLayout(title_layout)
        central_layout.addWidget(self.title_bar)
        subtitle = QtWidgets.QLabel("Solar Gold · Black Onyx · Nebula")
        subtitle.setStyleSheet(f"color: {soft_gold}; font-size:12px; margin-left:14px;")
        central_layout.addWidget(subtitle)
        
        # Song progress display (new feature)
        self.song_display = QtWidgets.QTextEdit()
        self.song_display.setReadOnly(True)
        self.song_display.setFixedHeight(70)  # Height for about 2 lines of text
        self.song_display.setStyleSheet(f"""
            QTextEdit {{
                background: {panel};
                border-radius:8px;
                padding:8px;
                color:{text};
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }}
            QTextEdit:hover {{
                border: 1px solid {gold};
            }}
        """)
        central_layout.addWidget(self.song_display)
        
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText("Вставьте текст песни сюда и нажмите 'Добавить'")
        self.song_input.setFixedHeight(110)
        self.song_input.setStyleSheet(f"background: {panel}; border-radius:8px; padding:8px; color:{text};")
        central_layout.addWidget(self.song_input)
        add_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Добавить песню")
        self.add_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.add_btn.setFixedHeight(36)
        self.add_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color:{text};")
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        central_layout.addLayout(add_row)
        self.add_btn.clicked.connect(self.add_song_from_input)
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
        mid = QtWidgets.QHBoxLayout()
        leftcol = QtWidgets.QVBoxLayout()
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setStyleSheet(f"background: {panel}; border-radius:10px; padding:6px; color:{text};")
        for name, content in self.bot.playlist:
            self.song_list.addItem(f"{name} — {len(content)} chars")
        self.song_list.setCurrentRow(self.bot.song_index)
        leftcol.addWidget(self.song_list)
        list_controls = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton("Удалить")
        self.remove_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.remove_btn.setFixedHeight(30)
        self.remove_btn.setStyleSheet("border-radius:6px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
        self.rename_btn = QtWidgets.QPushButton("Переименовать")
        self.rename_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.rename_btn.setFixedHeight(30)
        self.rename_btn.setStyleSheet("border-radius:6px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
        list_controls.addWidget(self.remove_btn)
        list_controls.addWidget(self.rename_btn)
        list_controls.addStretch()
        leftcol.addLayout(list_controls)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.rename_btn.clicked.connect(self.rename_selected)
        mid.addLayout(leftcol, 2)
        right = QtWidgets.QVBoxLayout()
        self.status_label = QtWidgets.QLabel("Status: Idle")
        self.mode_label = QtWidgets.QLabel("Mode: 1")
        self.pos_label = QtWidgets.QLabel(f"Pos: 0/{len(self.bot.song)}")
        for lbl in (self.status_label, self.mode_label, self.pos_label):
            lbl.setStyleSheet("color: %s;" % text)
            right.addWidget(lbl)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        right.addWidget(self.progress)
        mid.addLayout(right, 1)
        central_layout.addLayout(mid)
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
        mode_row = QtWidgets.QHBoxLayout()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["1 - Ровный", "2 - Живой", "3 - Гибридный", "4 - Ошибочный (5%)"])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.setStyleSheet(f"background: {panel}; color:{text}; border-radius:6px; padding:6px;")
        mode_row.addWidget(QtWidgets.QLabel("Mode:"))
        mode_row.addWidget(self.mode_combo)
        central_layout.addLayout(mode_row)
        help_label = QtWidgets.QLabel("F1 Start/Pause | F2 Restart | F3 Skip25 | F4 Exit | F5 PrevMode | F6 Freeze | F7 NextMode | F8 NextSong | F10 Force Roblox")
        help_label.setStyleSheet("color: #9b9b9b;")
        central_layout.addWidget(help_label)
        # Update section
        update_layout = QtWidgets.QHBoxLayout()
        self.check_update_btn = QtWidgets.QPushButton("Проверить обновление")
        self.check_update_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.check_update_btn.setFixedHeight(36)
        self.check_update_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color: %s;" % text)
        self.download_btn = QtWidgets.QPushButton("Скачать последнюю версию")
        self.download_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.download_btn.setFixedHeight(36)
        self.download_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color: %s;" % text)
        update_layout.addWidget(self.check_update_btn)
        update_layout.addWidget(self.download_btn)
        central_layout.addLayout(update_layout)
        self.check_update_btn.clicked.connect(self.gui_check_update)
        self.download_btn.clicked.connect(self.open_releases_page)
        footer = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("AstraKeys — by SMisha2")
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
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            QSlider::groove:horizontal{{height:8px; background: rgba(255,255,255,0.03); border-radius:4px;}}
            QSlider::handle:horizontal{{background: {soft_gold}; width:14px; border-radius:7px;}}
            QComboBox{{padding:6px; border-radius:6px;}}
            QProgressBar{{background: rgba(255,255,255,0.02); border-radius:8px; text-align:center;}}
            QProgressBar::chunk{{background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gold}, stop:1 {soft_gold}); border-radius:8px;}}
        """)
        # Connect signals for title bar buttons
        self.btn_close.clicked.connect(self.close)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximize)
        self.btn_about.clicked.connect(self.show_about)
        # Connect other signals
        self.add_btn.clicked.connect(self.add_song_from_input)
        self.start_btn.clicked.connect(self.toggle_start)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_mode_btn.clicked.connect(self.prev_mode)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.song_list.itemDoubleClicked.connect(self.rename_selected)
        self.delay_slider.valueChanged.connect(self.delay_changed)
        self.mode_combo.currentIndexChanged.connect(self.mode_combo_changed)
        # Enable mouse tracking for dragging
        self.setMouseTracking(True)
        self.central.setMouseTracking(True)
        self.title_bar.setMouseTracking(True)
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()
    def open_releases_page(self):
        webbrowser.open(RELEASES_URL)
    def check_internet_status(self):
        def worker():
            try:
                requests.get("https://api.github.com", timeout=3)
            except:
                pass
        threading.Thread(target=worker, daemon=True).start()
    def roblox_keepalive(self):
        """Keep Roblox window accessible without constant focus changes"""
        while True:
            try:
                find_roblox_window()
                time.sleep(5)
            except:
                time.sleep(5)
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            # FIXED: Check if click is in title bar area
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self.dragging = False
        super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self.toggle_maximize()
        super().mouseDoubleClickEvent(event)
    def add_song_from_input(self):
        text = self.song_input.toPlainText().strip()
        if text:
            name, ok = QtWidgets.QInputDialog.getText(self, "Имя песни", "Введите название песни:", text=f"Song {len(self.bot.playlist)+1}")
            if not ok or not name.strip():
                name = f"Song {len(self.bot.playlist)+1}"
            sanitized = self.bot.sanitize_song(text)
            self.bot.playlist.append((name, sanitized))
            self.song_list.addItem(f"{name} — {len(sanitized)} chars")
            print(f"Song '{name}' added")
            self.song_input.clear()
    def remove_selected(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            self.bot.playlist.pop(row)
            self.song_list.takeItem(row)
            if self.bot.song_index >= len(self.bot.playlist):
                self.bot.song_index = max(0, len(self.bot.playlist) - 1)
            if self.bot.playlist:
                self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
            self.song_list.setCurrentRow(self.bot.song_index)
    def rename_selected(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            current_name, content = self.bot.playlist[row]
            new_name, ok = QtWidgets.QInputDialog.getText(self, "Переименовать песню", "Новое название:", text=current_name)
            if ok and new_name.strip():
                self.bot.playlist[row] = (new_name.strip(), content)
                if row == self.bot.song_index:
                    self.bot.song_name = new_name.strip()
                self.song_list.item(row).setText(f"{new_name.strip()} — {len(content)} chars")
                print(f"Renamed song to '{new_name.strip()}'")
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
    def delay_changed(self, val):
        self.bot.start_delay = val / 1000.0
        self.delay_label.setText(f"Start Delay: {self.bot.start_delay:.3f}s")
    def mode_combo_changed(self, idx):
        self.bot.mode = idx + 1
        self.refresh_status()
    def update_song_display(self):
        """Update the song display with current position highlighting"""
        if not self.bot.song:
            self.song_display.setPlainText("")
            return
        
        # Define display parameters
        chars_per_line = 35  # Characters per line
        lines_to_show = 2    # Number of lines to show
        total_chars = chars_per_line * lines_to_show
        
        # Determine current position (considering freeze mode)
        current_pos = self.bot.frozen_note_index if self.bot.freeze_note else self.bot.note_index
        
        # If current position is beyond song length, just show the end
        if current_pos >= len(self.bot.song):
            start_pos = max(0, len(self.bot.song) - total_chars)
            display_text = self.bot.song[start_pos:]
            self.song_display.setPlainText(display_text)
            return
        
        # Calculate start position to center current note
        start_pos = max(0, current_pos - (total_chars // 3))
        
        # Get the text to display
        display_text = self.bot.song[start_pos:start_pos + total_chars]
        
        # If we're at the end of the song, adjust to show the end
        if len(display_text) < total_chars and start_pos + total_chars > len(self.bot.song):
            start_pos = max(0, len(self.bot.song) - total_chars)
            display_text = self.bot.song[start_pos:start_pos + total_chars]
        
        # Calculate position within the displayed text
        current_in_display = current_pos - start_pos
        
        # Create HTML with highlighting if current position is within display range
        if 0 <= current_in_display < len(display_text):
            # Check if we're at the start of a chord
            if current_in_display < len(display_text) - 1 and display_text[current_in_display] == '[':
                # Find the end of the chord
                end_bracket = -1
                for i in range(current_in_display + 1, min(current_in_display + 20, len(display_text))):
                    if display_text[i] == ']':
                        end_bracket = i
                        break
                
                if end_bracket != -1:
                    # Split text into parts
                    before = display_text[:current_in_display]
                    chord = display_text[current_in_display:end_bracket + 1]
                    after = display_text[end_bracket + 1:]
                    
                    # Create HTML with chord highlighting
                    highlighted = (
                        f'<span style="color: #ccc;">{before}</span>'
                        f'<span style="background-color: rgba(255,216,106,0.4); border-radius: 3px; padding: 0 2px; color: #ffd86a; font-weight: bold;">'
                        f'{chord}'
                        f'</span>'
                        f'<span style="color: #ccc;">{after}</span>'
                    )
                    self.song_display.setHtml(highlighted)
                    return
            
            # For single note highlighting
            before = display_text[:current_in_display]
            current = display_text[current_in_display]
            after = display_text[current_in_display + 1:]
            
            highlighted = (
                f'<span style="color: #ccc;">{before}</span>'
                f'<span style="background-color: rgba(255,216,106,0.5); border-radius: 3px; padding: 0 2px; color: #ffd86a; font-weight: bold;">'
                f'{current}'
                f'</span>'
                f'<span style="color: #ccc;">{after}</span>'
            )
            self.song_display.setHtml(highlighted)
            return
        
        # Fallback: no highlighting needed or possible
        self.song_display.setPlainText(display_text)
    def refresh_status(self):
        st = "Playing" if self.bot.playing else "Paused"
        self.status_label.setText(f"Status: {st}")
        mode_names = {1: "Ровный", 2: "Живой", 3: "Гибридный", 4: "Ошибочный"}
        self.mode_label.setText(f"Mode: {self.bot.mode} — {mode_names.get(self.bot.mode,'?')}")
        try:
            self.pos_label.setText(f"Pos: {self.bot.note_index}/{len(self.bot.song)}")
        except:
            self.pos_label.setText("Pos: 0/0")
        if self.mode_combo.currentIndex() != self.bot.mode - 1:
            self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)
        
        # Update song display with current position
        self.update_song_display()
    def gui_check_update(self):
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
                body = info.get("body", "")
                m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", body)
                if m:
                    latest_version = m.group(1)
            if not latest_version:
                self._show_message_box("Ошибка", "Не удалось определить номер версии релиза.")
                self._update_ui_after_check(False)
                return
            if version_tuple(latest_version) <= version_tuple(CURRENT_VERSION):
                self._show_message_box("Обновления", "Установлена последняя или более новая версия.")
                self._update_ui_after_check(False)
                return
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self._show_message_box("Обновления", "Обнаружена новая версия, но нужный файл не найден в релизе.")
                self._update_ui_after_check(False)
                return
            tmp_name = "AstraKeys_update_tmp.exe"
            def prog_cb(pct):
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
            is_frozen = getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe")
            try:
                perform_replacement_and_restart(tmp_name, ASSET_NAME, is_frozen)
            except Exception as e:
                self._show_message_box("Ошибка", f"Не удалось заменить файл при обновлении: {e}")
                self._update_ui_after_check(False)
                return
        finally:
            QtCore.QTimer.singleShot(0, lambda: self._update_ui_after_check(False))
    def _update_ui_after_check(self, busy=True):
        self.check_update_btn.setEnabled(True)
        if not busy:
            self.progress.setVisible(False)
            self.progress.setValue(0)
    def _show_message_box(self, title, text):
        def show():
            mb = QtWidgets.QMessageBox(self)
            mb.setWindowTitle(title)
            mb.setText(text)
            mb.exec()
        QtCore.QTimer.singleShot(0, show)
# ---------------- Main runner ----------------
if __name__ == "__main__":
    # Default playlist with named songs
    default_playlist = [
        ("Stairway to Heaven", r"[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe]"),
        ("Minecraft Theme", r"l--l--l--l-lzlk"),
        ("Twinkle Twinkle", r"fffff[4qf]spsfspsg"),
    ]
    bot = RobloxPianoBot(default_playlist)
    player_thread = threading.Thread(target=bot.play_song, daemon=True)
    player_thread.start()
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
    gui.show()
    sys.exit(app.exec())
