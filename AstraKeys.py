# AstraKeys_v1.1.11 — Black Onyx / Solar Gold / Nebula blend
# by SMisha2
# Features: Russian keyboard support, adjustable modes, resizable window, overlay note display with transparency
# Updated with animated background, playlist management, detailed logging, and improved update process
CURRENT_VERSION = "1.1.1"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
LOG_FILE = "astrakeys.log"
PLAYLIST_FILE = "playlist.json"
# ---------------- imports ----------------
import os
import sys
import time
import threading
import re
import random
import math
import json
import logging
from datetime import datetime
import webbrowser
import requests
from PyQt6 import QtWidgets, QtCore, QtGui
# optional win32
try:
    import win32gui
    import win32con
    import win32process
except Exception:
    win32gui = None
    win32con = None
    win32process = None
# optional pynput
try:
    from pynput.keyboard import Controller, Key, Listener, KeyCode
except Exception:
    Controller = None
    Key = None
    Listener = None
    KeyCode = None
# ---------------- setup logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AstraKeys")
logger.info(f"Starting AstraKeys v{CURRENT_VERSION} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
# ---------------- constants ----------------
PEDAL_KEYS = {"-", "=", "[", "]"}
RU_EN_MAPPING = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y', 'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
    'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h', 'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': '\'',
    'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n', 'ь': 'm', 'б': ',', 'ю': '.', 'ё': '`',
    'Й': 'Q', 'Ц': 'W', 'У': 'E', 'К': 'R', 'Е': 'T', 'Н': 'Y', 'Г': 'U', 'Ш': 'I', 'Щ': 'O', 'З': 'P', 'Х': '{', 'Ъ': '}',
    'Ф': 'A', 'Ы': 'S', 'В': 'D', 'А': 'F', 'П': 'G', 'Р': 'H', 'О': 'J', 'Л': 'K', 'Д': 'L', 'Ж': ':', 'Э': '"',
    'Я': 'Z', 'Ч': 'X', 'С': 'C', 'М': 'V', 'И': 'B', 'Т': 'N', 'Ь': 'M', 'Б': '<', 'Ю': '>', 'Ё': '~',
    # Special characters for black keys
    '!': '!', '@': '@', '#': '#', '$': '$', '%': '%', '^': '^', '&': '&', '*': '*',
    '(': '(', ')': ')', '-': '-', '_': '_', '=': '=', '+': '+', '\\': '\\', '|': '|',
    '/': '/', '?': '?', '.': '.', ',': ',', '"': '"', "'": "'", ';': ';', ':': ':',
    '<': '<', '>': '>', '[': '[', ']': ']', '{': '{', '}': '}'
}
ROBLOX_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM!@$%^*()_+-=[]{};':\",./<>?\\|`~&\"'"
# ---------------- Keyboard helpers ----------------
def is_valid_key(key):
    """Check if key is valid for pynput"""
    if not key or not isinstance(key, str) or len(key) != 1:
        return False
    return key in ROBLOX_KEYS
# ---------------- Auto-update helpers ----------------
def download_asset_to_file(url, dest_path, progress_callback=None, chunk_size=1024*64, max_retries=3):
    for attempt in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = r.headers.get("content-length")
                if total is None:
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size):
                            if chunk:
                                f.write(chunk)
                    if progress_callback:
                        progress_callback(100)
                    return True, None
                total = int(total)
                written = 0
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size):
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
                        logger.warning(f"Download incomplete. Retrying... ({attempt+1})")
                        time.sleep(1)
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        continue
                    return False, "File size mismatch"
        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(f"Download failed (attempt {attempt+1}): {e}. Retrying...")
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
            logger.info("Update script executed, exiting application")
            sys.exit(0)
        else:
            target = os.path.abspath(sys.argv[0])
            try:
                backup = target + ".bak"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(target, backup)
            except Exception as e:
                logger.error(f"Backup failed: {e}")
            try:
                os.replace(new_file, target)
            except Exception as e:
                logger.error(f"Replace failed: {e}")
                with open(new_file, "rb") as src, open(target, "wb") as dst:
                    dst.write(src.read())
            os.remove(new_file)
            os.execv(sys.executable, [sys.executable, target])
    except Exception as e:
        logger.error(f"Replacement error: {e}")
        raise
def fetch_latest_release_info():
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    try:
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        logger.error(f"Failed to fetch release info: {e}")
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
# ---------------- Animated Background Widget ----------------
class AnimatedBackground(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StaticContents)
        self.setFixedSize(800, 600)  # Default size, will be adjusted
        self.stars = []
        self.init_stars()
        self.animation_timer = QtCore.QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)  # 20 FPS
    def init_stars(self):
        for _ in range(50):  # Number of stars
            star = {
                'x': random.randint(0, self.width()),
                'y': random.randint(0, self.height()),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.uniform(0.3, 1.0),
                'speed': random.uniform(0.005, 0.02),
                'direction': random.uniform(0, 2 * math.pi)
            }
            self.stars.append(star)
    def update_animation(self):
        for star in self.stars:
            # Slowly move stars
            star['x'] += math.cos(star['direction']) * star['speed']
            star['y'] += math.sin(star['direction']) * star['speed']
            
            # Wrap around edges
            if star['x'] < 0:
                star['x'] = self.width()
            elif star['x'] > self.width():
                star['x'] = 0
                
            if star['y'] < 0:
                star['y'] = self.height()
            elif star['y'] > self.height():
                star['y'] = 0
            
            # Slightly change brightness
            star['brightness'] += random.uniform(-0.01, 0.01)
            star['brightness'] = max(0.3, min(1.0, star['brightness']))
        self.update()
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Draw stars
        for star in self.stars:
            brightness = star['brightness']
            color = QtGui.QColor(
                int(255 * brightness),
                int(235 * brightness),
                int(190 * brightness),
                int(180 * brightness)  # Transparency
            )
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawEllipse(
                int(star['x'] - star['size']), 
                int(star['y'] - star['size']),
                int(star['size'] * 2),
                int(star['size'] * 2)
            )
    def resizeEvent(self, event):
        # Adjust star positions when window resizes
        new_width = event.size().width()
        new_height = event.size().height()
        for star in self.stars:
            star['x'] = min(star['x'], new_width - 1)
            star['y'] = min(star['y'], new_height - 1)
        super().resizeEvent(event)
# ---------------- Note Overlay Window ----------------
class NoteOverlayWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Default properties
        self.is_fullscreen = False
        self.opacity = 0.9
        self.font_size = 24
        self.bg_color = "#0a0a0a"
        self.text_color = "#ffd86a"
        self.highlight_color = "#ffd86a"
        self.highlight_bg = "rgba(255,216,106,0.3)"
        # Setup UI
        self.init_ui()
        # Load settings
        self.load_settings()
        self.apply_settings()
        # Default size and position
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.resize(400, 150)
        self.move(screen.width() // 2 - self.width() // 2, screen.height() - self.height() - 100)
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        # Title bar with controls
        title_bar = QtWidgets.QWidget()
        title_bar_layout = QtWidgets.QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_label = QtWidgets.QLabel("AstraKeys Notes")
        title_label.setStyleSheet("color: #ffd86a; font-weight: bold;")
        self.pin_btn = QtWidgets.QPushButton("📌")
        self.pin_btn.setFixedSize(30, 30)
        self.pin_btn.setStyleSheet("background: transparent; border: none; color: #ccc;")
        self.pin_btn.setToolTip("Закрепить/открепить окно")
        self.opacity_btn = QtWidgets.QPushButton("👁️")
        self.opacity_btn.setFixedSize(30, 30)
        self.opacity_btn.setStyleSheet("background: transparent; border: none; color: #ccc;")
        self.opacity_btn.setToolTip("Настроить прозрачность")
        self.fullscreen_btn = QtWidgets.QPushButton("❐")
        self.fullscreen_btn.setFixedSize(30, 30)
        self.fullscreen_btn.setStyleSheet("background: transparent; border: none; color: #ccc;")
        self.fullscreen_btn.setToolTip("Полноэкранный режим")
        self.close_btn = QtWidgets.QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("background: transparent; border: none; color: #ccc;")
        self.close_btn.setToolTip("Закрыть")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.pin_btn)
        title_bar_layout.addWidget(self.opacity_btn)
        title_bar_layout.addWidget(self.fullscreen_btn)
        title_bar_layout.addWidget(self.close_btn)
        # Note display area
        self.note_display = QtWidgets.QTextEdit()
        self.note_display.setReadOnly(True)
        self.note_display.setStyleSheet("""
        QTextEdit {
            background: transparent;
            border: none;
            color: #ffd86a;
            font-family: 'Courier New', monospace;
            font-size: 24px;
        }
        """)
        self.note_display.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.note_display.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.note_display.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(title_bar)
        layout.addWidget(self.note_display)
        # Connect buttons
        self.pin_btn.clicked.connect(self.toggle_pin)
        self.opacity_btn.clicked.connect(self.show_opacity_menu)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.close_btn.clicked.connect(self.hide)
        # Enable dragging
        self.dragging = False
        self.drag_position = None
        self.title_bar = title_bar
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
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
    def toggle_pin(self):
        flags = self.windowFlags()
        if flags & QtCore.Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, False)
            self.pin_btn.setText("◻️")
        else:
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
            self.pin_btn.setText("📌")
        if self.isVisible():
            self.show()
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            self.fullscreen_btn.setText("❐")
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            self.fullscreen_btn.setText("❐")
    def show_opacity_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
        QMenu {
            background-color: #1a1a1a;
            color: #f5f3f1;
            border: 1px solid #d4af37;
        }
        QMenu::item:selected {
            background-color: #2a2a2a;
        }
        """)
        # Opacity options
        opacities = [10, 30, 50, 70, 90, 100]
        for opacity in opacities:
            action = menu.addAction(f"{opacity}%")
            action.setData(opacity / 100)
        action = menu.exec(self.opacity_btn.mapToGlobal(QtCore.QPoint(0, self.opacity_btn.height())))
        if action:
            self.opacity = action.data()
            self.setWindowOpacity(self.opacity)
    def update_notes(self, song, current_pos, lines=4, chars_per_line=30):
        if not song or current_pos >= len(song):
            self.note_display.setPlainText("")
            return
        # Get the portion of the song to display
        end_pos = min(len(song), current_pos + lines * chars_per_line)
        display_text = song[current_pos:end_pos]
        # Split into lines
        lines_text = []
        for i in range(0, len(display_text), chars_per_line):
            line = display_text[i:i+chars_per_line]
            lines_text.append(line)
        # Highlight current position
        current_line = 0
        char_in_line = current_pos % chars_per_line
        # Create HTML with highlighting
        html_content = ""
        for i, line in enumerate(lines_text):
            if i == current_line and char_in_line < len(line):
                # Split line at current position
                before = line[:char_in_line]
                current = line[char_in_line]
                after = line[char_in_line+1:]
                # Highlight current character
                html_content += f'<span style="color:{self.text_color}">{before}</span>'
                html_content += f'<span style="background-color:{self.highlight_bg}; color:{self.highlight_color}; font-weight:bold; padding:0 1px; border-radius:2px">{current}</span>'
                html_content += f'<span style="color:{self.text_color}">{after}</span><br>'
            else:
                html_content += f'<span style="color:{self.text_color}">{line}</span><br>'
        self.note_display.setHtml(html_content.rstrip("<br>"))
    def apply_settings(self):
        self.setWindowOpacity(self.opacity)
        self.note_display.setStyleSheet(f"""
        QTextEdit {{
            background: {self.bg_color};
            border: none;
            color: {self.text_color};
            font-family: 'Courier New', monospace;
            font-size: {self.font_size}px;
        }}
        """)
    def load_settings(self):
        try:
            if os.path.exists("overlay_settings.json"):
                with open("overlay_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.opacity = settings.get("opacity", self.opacity)
                self.font_size = settings.get("font_size", self.font_size)
                self.bg_color = settings.get("bg_color", self.bg_color)
                self.text_color = settings.get("text_color", self.text_color)
                self.highlight_color = settings.get("highlight_color", self.highlight_color)
                self.highlight_bg = settings.get("highlight_bg", self.highlight_bg)
        except Exception as e:
            logger.error(f"Error loading overlay settings: {e}")
    def save_settings(self):
        settings = {
            "opacity": self.opacity,
            "font_size": self.font_size,
            "bg_color": self.bg_color,
            "text_color": self.text_color,
            "highlight_color": self.highlight_color,
            "highlight_bg": self.highlight_bg
        }
        try:
            with open("overlay_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving overlay settings: {e}")
    def closeEvent(self, event):
        self.save_settings()
        event.accept()
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
            logger.warning("Playlist empty!")
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
        self.active_keys = {}
        self.last_played_time = time.time()
        self.overlay_window = None
        # Note delay parameters
        self.min_note_delay = 0  # milliseconds
        self.max_note_delay = 10  # milliseconds
        logger.info("🎹 AstraKeys Bot initialized")
        logger.info("▶ F1 Play/Pause | F2 Restart | F3 Skip Forward 25 | F4 Skip Backward 25 | F6 Freeze Note")
        logger.info("⭐ * - Pedal | F7 Next Mode | F5 Prev Mode | F8 Next Song | F10 Force Roblox | F11 Toggle Overlay")
        if Listener:
            threading.Thread(target=self.listen_keys, daemon=True).start()
    def set_overlay_window(self, window):
        self.overlay_window = window
    def get_random_delay(self):
        """Returns random delay in seconds between min_note_delay and max_note_delay"""
        delay_ms = random.uniform(self.min_note_delay, self.max_note_delay)
        return delay_ms / 1000.0  # Convert to seconds
    def sanitize_song(self, song):
        if not song:
            return ""
        return ''.join(ch for ch in song if ch in ROBLOX_KEYS + " \t\r[]")
    def convert_to_english(self, key):
        """Convert Russian key to English equivalent for Roblox"""
        if not key or not isinstance(key, str):
            return key
        # Handle special characters first
        special_chars = {
            '*': '*', '[': '[', ']': ']', '{': '[', '}': ']',
            '8': '8',  # For shifted *
            'l': 'l', 'L': 'L', 'z': 'z', 'Z': 'Z', 'k': 'k', 'K': 'K',
            '!': '!', '@': '@', '#': '#', '$': '$', '%': '%', '^': '^',
            '&': '&', '(': '(', ')': ')', '-': '-', '_': '_', '=': '=', '+': '+',
            '\\': '\\', '|': '|', '/': '/', '?': '?', '.': '.', ',': ',',
            '"': '"', "'": "'", ';': ';', ':': ':', '<': '<', '>': '>',
            '~': '~', '`': '`'
        }
        if key in special_chars:
            return special_chars[key]
        lower_key = key.lower()
        if lower_key in RU_EN_MAPPING:
            converted = RU_EN_MAPPING[lower_key]
            # Preserve case
            if key.isupper() and converted.isalpha():
                return converted.upper()
            return converted
        # Return as-is for English letters and numbers
        return key
    def is_key_valid(self, key):
        """Check if key can be pressed safely"""
        if not key or not isinstance(key, str):
            return False
        return key in ROBLOX_KEYS
    def press_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            original_key = key
            key = self.convert_to_english(key)
            if not self.is_key_valid(key):
                logger.debug(f"Invalid key '{original_key}' -> '{key}'")
                return
            # Check if key is already pressed
            if key in self.active_keys and self.active_keys[key]:
                return
            try:
                # Handle special characters and uppercase letters through Shift
                needs_shift = False
                base_key = key
                # Define shift mapping
                shift_mapping = {
                    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                    '_': '-', '+': '=', '{': '[', '}': ']', ':': ';',
                    '"': "'", '<': ',', '>': '.', '?': '/', '|': '\\',
                    '~': '`'
                }
                # Check if key needs Shift
                if key in shift_mapping:
                    needs_shift = True
                    base_key = shift_mapping[key]
                elif key.isupper() and key.isalpha():
                    needs_shift = True
                    base_key = key.lower()
                # Press Shift if needed
                if needs_shift:
                    self.keyboard.press(Key.shift)
                    time.sleep(0.0001)  # Very short delay
                # Press main key
                self.keyboard.press(base_key)
                self.active_keys[key] = True
                logger.debug(f"Pressed: '{original_key}' -> '{base_key}'" + (" with Shift" if needs_shift else ""))
                # Release Shift immediately after use
                if needs_shift:
                    time.sleep(0.0001)  # Very short delay
                    self.keyboard.release(Key.shift)
                    logger.debug("Released Shift immediately after use")
            except Exception as e:
                logger.error(f"Error pressing key '{original_key}' -> '{key}': {e}")
                # Ensure Shift is released even on error
                try:
                    if needs_shift:
                        self.keyboard.release(Key.shift)
                except:
                    pass
    def release_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            key = self.convert_to_english(key)
            if key not in self.active_keys or not self.active_keys[key]:
                return
            try:
                # Determine base key
                base_key = key
                shift_mapping = {
                    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                    '_': '-', '+': '=', '{': '[', '}': ']', ':': ';',
                    '"': "'", '<': ',', '>': '.', '?': '/', '|': '\\',
                    '~': '`'
                }
                if key in shift_mapping:
                    base_key = shift_mapping[key]
                elif key.isupper() and key.isalpha():
                    base_key = key.lower()
                # Release main key
                self.keyboard.release(base_key)
                self.active_keys[key] = False
                logger.debug(f"Released: '{base_key}'")
            except Exception as e:
                logger.error(f"Error releasing key '{key}': {e}")
    def release_all(self):
        with self.lock:
            if not self.keyboard:
                self.active_keys.clear()
                return
            # Collect all keys to release
            keys_to_release = list(self.active_keys.keys())
            # Release regular keys first
            for k in keys_to_release:
                if k in self.active_keys and self.active_keys[k]:
                    try:
                        if k.isupper() and k.isalpha():
                            base_key = k.lower()
                        elif k in {
                            '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                            '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                            '_': '-', '+': '=', '{': '[', '}': ']', ':': ';',
                            '"': "'", '<': ',', '>': '.', '?': '/', '|': '\\',
                            '~': '`'
                        }:
                            shift_mapping = {
                                '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                                '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                                '_': '-', '+': '=', '{': '[', '}': ']', ':': ';',
                                '"': "'", '<': ',', '>': '.', '?': '/', '|': '\\',
                                '~': '`'
                            }
                            base_key = shift_mapping.get(k, k.lower() if k.isupper() and k.isalpha() else k)
                        else:
                            base_key = k
                        self.keyboard.release(base_key)
                        logger.debug(f"Released: '{base_key}'")
                        self.active_keys[k] = False
                    except Exception as e:
                        logger.error(f"Error releasing key during cleanup: {e}")
            # Ensure Shift is released
            try:
                self.keyboard.release(Key.shift)
                logger.debug("Released Shift in release_all")
            except Exception as e:
                logger.error(f"Error releasing Shift in cleanup: {e}")
            logger.debug("All keys released")
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
                    self.mode = self.mode + 1 if self.mode < 3 else 1  # Only 3 modes now
                    logger.info(f"Mode: {self.mode} (was {old})")
                elif key == Key.f5:
                    old = self.mode
                    self.mode = self.mode - 1 if self.mode > 1 else 3  # Only 3 modes now
                    logger.info(f"Mode: {self.mode} (was {old})")
                elif key == Key.f1:
                    self.playing = not self.playing
                    logger.info("Play" if self.playing else "Pause")
                elif key == Key.f2:
                    self.restart = True
                    logger.info("Restart")
                elif key == Key.f3:
                    self.skip_notes += 25
                    logger.info("Skip forward 25")
                elif key == Key.f4:
                    self.skip_notes -= 25
                    logger.info("Skip backward 25")
                elif key == Key.f6:
                    self.freeze_note = not self.freeze_note
                    if self.freeze_note:
                        self.frozen_note_index = self.note_index
                        logger.info(f"Freeze at {self.frozen_note_index}")
                    else:
                        logger.info("Freeze off")
                elif key == Key.f8:
                    self.next_song()
                elif key == Key.f10:
                    activate_roblox_window()
                elif key == Key.f11:
                    if self.overlay_window:
                        if self.overlay_window.isVisible():
                            self.overlay_window.hide()
                        else:
                            self.overlay_window.show()
                # Check for pedal keys including brackets
                elif (key_char in PEDAL_KEYS) or is_bracket:
                    self.hold_star = True
                    key_repr = key_char or ("[" if hasattr(key, 'vk') and key.vk == 219 else "]")
                    logger.debug(f"Pedal down ({key_repr})")
            except Exception as e:
                logger.error(f"Error in on_press: {e}")
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
                    logger.debug(f"Pedal up ({key_repr})")
            except Exception as e:
                logger.error(f"Error in on_release: {e}")
        try:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            logger.error(f"Listener failed: {e}")
    def next_song(self):
        old_index = self.song_index
        n = len(self.playlist)
        for _ in range(n):
            self.song_index = (self.song_index + 1) % n
            if self.playlist[self.song_index][1]:
                self.song_name, self.song = self.playlist[self.song_index]
                self.note_index = 0
                self.frozen_note_index = 0
                logger.info(f"Next song: {self.song_name} ({self.song_index+1}/{n})")
                return
        self.song_index = old_index
    def play_chord(self, chord):
        """Play chord with mode-specific timing and random delays"""
        logger.debug(f"Playing chord: {chord}")
        # Add random delays for each note
        random_delays = [self.get_random_delay() for _ in range(len(chord))]
        
        if self.mode == 1:
            # Mode 1: All keys press almost simultaneously with delays
            threads = []
            for i, k in enumerate(chord):
                delay = random_delays[i]
                t = threading.Timer(delay, self.press_key, args=[k])
                t.daemon = True
                t.start()
                threads.append(t)
            time.sleep(max(random_delays) + 0.001)
            
        elif self.mode == 2:
            press_threads = []
            base_delay = 0.001
            for i, k in enumerate(chord):
                delay = base_delay + random_delays[i] + random.uniform(0.0001, 0.001)
                t = threading.Timer(delay, self.press_key, args=[k])
                t.daemon = True
                t.start()
                press_threads.append(t)
            time.sleep(base_delay + max(random_delays) + 0.005)
            
        elif self.mode == 3:
            press_threads = []
            base_press_delay = random.uniform(0.0002, 0.0008)
            for i, k in enumerate(chord):
                press_delay = base_press_delay + random_delays[i] + (i * 0.0002)
                t_press = threading.Timer(press_delay, self.press_key, args=[k])
                t_press.daemon = True
                t_press.start()
                press_threads.append(t_press)
            max_press_time = base_press_delay + max(random_delays) + (len(chord) * 0.0003) + 0.0002
            time.sleep(max_press_time)
    def release_chord(self, chord):
        """Release chord with mode-specific timing"""
        if not chord:
            return
            
        if self.mode == 1:
            # Mode 1: All keys release almost simultaneously
            for k in reversed(chord):
                self.release_key(k)
            time.sleep(0.0005)
            
        elif self.mode == 2:
            release_threads = []
            base_delay = 0.005
            for k in reversed(chord):
                delay = base_delay + random.uniform(0.0005, 0.005)
                t = threading.Timer(delay, self.release_key, args=[k])
                t.daemon = True
                t.start()
                release_threads.append(t)
            time.sleep(base_delay + 0.01)
            
        elif self.mode == 3:
            release_threads = []
            base_release_delay = random.uniform(0.0015, 0.004)
            for i, k in enumerate(reversed(chord)):
                release_delay = base_release_delay + (i * 0.0005)
                t_release = threading.Timer(release_delay, self.release_key, args=[k])
                t_release.daemon = True
                t_release.start()
                release_threads.append(t_release)
            time.sleep(base_release_delay + 0.01)
        else:
            for k in reversed(chord):
                self.release_key(k)
    def play_song(self):
        time.sleep(0.5)
        current_chord = None
        while True:
            try:
                # Update overlay if needed
                if self.overlay_window and self.overlay_window.isVisible():
                    current_pos = self.frozen_note_index if self.freeze_note else self.note_index
                    self.overlay_window.update_notes(self.song, current_pos)
                if self.restart:
                    self.restart = False
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.release_all()
                    current_chord = None
                    logger.info("Restarted")
                    while self.hold_star:
                        time.sleep(0.01)
                    time.sleep(0.1)
                    continue
                if not self.playing:
                    time.sleep(0.05)
                    continue
                # Handle freeze
                current_index = self.frozen_note_index if self.freeze_note else self.note_index
                if current_index >= len(self.song):
                    time.sleep(0.05)
                    continue
                char = self.song[current_index]
                # Skip whitespace
                if char.isspace():
                    if not self.freeze_note:
                        self.note_index += 1
                    time.sleep(0.001)
                    continue
                # Handle skip notes
                if self.skip_notes != 0 and not self.freeze_note:
                    direction = 1 if self.skip_notes > 0 else -1
                    notes_to_skip = abs(self.skip_notes)
                    
                    # Skip notes
                    for _ in range(notes_to_skip):
                        if direction > 0:
                            if char == "[":
                                end = self.song.find("]", current_index)
                                if end != -1:
                                    self.note_index = end + 1
                                else:
                                    self.note_index += 1
                            else:
                                self.note_index += 1
                        else:  # Skip backward
                            if self.note_index > 0:
                                # Find previous position
                                prev_index = self.note_index - 1
                                while prev_index > 0 and self.song[prev_index].isspace():
                                    prev_index -= 1
                                
                                # Handle chords when moving backward
                                if prev_index > 0 and self.song[prev_index] == ']':
                                    start = prev_index - 1
                                    while start > 0 and self.song[start] != '[':
                                        start -= 1
                                    if start > 0:
                                        self.note_index = start - 1
                                    else:
                                        self.note_index = prev_index
                                else:
                                    self.note_index = prev_index
                        if self.note_index < 0:
                            self.note_index = 0
                        if self.note_index >= len(self.song):
                            break
                        char = self.song[self.note_index]
                    
                    self.skip_notes = 0
                    logger.info(f"Skipped to position {self.note_index}")
                    continue
                # Wait for pedal press to play next note/chord
                if not self.hold_star:
                    time.sleep(0.001)
                    continue
                # Parse chord or single note
                if char == "[":
                    end = self.song.find("]", current_index)
                    if end == -1:
                        chord = [char]
                        next_index = current_index + 1
                    else:
                        chord_notes = self.song[current_index+1:end]
                        # Remove whitespace from chord
                        chord_notes = ''.join(chord_notes.split())
                        chord = list(chord_notes)
                        next_index = end + 1
                else:
                    chord = [char]
                    next_index = current_index + 1
                # Skip processing if this is a bracket that's being used as pedal
                if chord and chord[0] in ["[", "]"]:
                    if not self.freeze_note:
                        self.note_index = next_index
                    time.sleep(0.001)
                    continue
                # Activate Roblox before playing
                if activate_roblox_window():
                    logger.debug("Roblox window activated")
                else:
                    logger.debug("Failed to activate Roblox window")
                time.sleep(0.005)
                # Apply start delay if set
                if self.start_delay > 0:
                    time.sleep(self.start_delay * 0.5)
                # Play the chord
                self.play_chord(chord)
                current_chord = chord
                logger.debug(f"Played: {chord} at pos {current_index}")
                # Keep holding the chord while pedal is pressed
                while self.hold_star and self.playing and not self.restart:
                    time.sleep(0.001)
                # Release the chord when pedal is released
                if current_chord:
                    self.release_chord(current_chord)
                    current_chord = None
                # Move to next note only if not frozen
                if not self.freeze_note:
                    self.note_index = next_index
                time.sleep(0.0005)
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(0.01)
# ---------------- About Dialog ----------------
class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе — AstraKeys")
        self.setFixedSize(400, 360)
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
        QLabel.new_features {
            color: #5fd7ff;
            margin-top: 10px;
        }
        """)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QtWidgets.QLabel("AstraKeys")
        title.setProperty("class", "title")
        layout.addWidget(title, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        version = QtWidgets.QLabel(f"Версия: {CURRENT_VERSION}")
        version.setStyleSheet("color: #9b9b9b;")
        layout.addWidget(version, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        desc = QtWidgets.QLabel(
            "Программа для игры на пианино в Roblox\n"
            "Поддерживает чёрные и белые клавиши,\n"
            "настраиваемые задержки и многое другое."
        )
        desc.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        # New features section
        new_features = QtWidgets.QLabel(
            "Новые возможности:\n"
            "- Загрузка и сохранение плейлиста\n"
            "- Анимированный фон (мерцающие звезды)\n"
            "- Детальное логгирование всех действий\n"
            "- Прокрутка нот назад на 25 (F4)\n"
            "- Улучшенный процесс обновления\n"
            "- Убран ошибочный режим\n"
            "- Прозрачное управление"
        )
        new_features.setProperty("class", "new_features")
        layout.addWidget(new_features)
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
# ---------------- Update Animation Widget ----------------
class UpdateAnimation(QtWidgets.QWidget):
    progress_updated = QtCore.pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.angle = 0
        self.progress = 0
        self.animation_timer = QtCore.QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(30)  # ~33 FPS
    def update_animation(self):
        self.angle = (self.angle + 3) % 360  # Rotate 3 degrees per frame
        self.update()
    def set_progress(self, value):
        self.progress = value
        self.progress_updated.emit(value)
        self.update()
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        
        # Draw background circle
        bg_color = QtGui.QColor(30, 30, 30, 120)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QBrush(bg_color))
        painter.drawEllipse(center, 80, 80)
        
        # Draw progress arc
        if self.progress > 0:
            progress_color = QtGui.QColor(212, 175, 55, 200)  # Gold
            painter.setPen(QtGui.QPen(progress_color, 8))
            span_angle = int(360 * self.progress / 100)
            painter.drawArc(center.x() - 75, center.y() - 75, 150, 150, 90 * 16, -span_angle * 16)
        
        # Draw rotating indicator
        indicator_color = QtGui.QColor(255, 216, 106, 255)  # Bright gold
        painter.setPen(QtGui.QPen(indicator_color, 4))
        radius = 65
        x = center.x() + radius * math.cos(math.radians(self.angle))
        y = center.y() + radius * math.sin(math.radians(self.angle))
        painter.drawPoint(int(x), int(y))
        
        # Draw center text
        if self.progress > 0:
            painter.setPen(QtGui.QColor(255, 216, 106))
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, f"{self.progress}%")
# ---------------- GUI ----------------
class BotGUI(QtWidgets.QWidget):
    def __init__(self, bot: RobloxPianoBot):
        super().__init__()
        self.bot = bot
        self.setWindowTitle("AstraKeys — by SMisha2")
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        # Default size and position
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        default_width = 780
        default_height = 650
        x = (screen.width() - default_width) // 2
        y = (screen.height() - default_height) // 2
        self.setGeometry(x, y, default_width, default_height)
        # Load window state
        self.load_window_state()
        # Dragging variables
        self.dragging = False
        self.drag_position = None
        # Animated background
        self.background = AnimatedBackground(self)
        self.background.lower()
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
        # Load saved playlist
        self.load_playlist()
    def init_ui(self):
        dark = '#0b0b0b'
        panel = 'rgba(18,18,18,0.85)'
        gold = '#d4af37'
        soft_gold = '#ffd86a'
        text = '#f5f3f1'
        # Central frame with rounded corners
        self.central = QtWidgets.QFrame()
        self.central.setObjectName("central_frame")
        self.central.setStyleSheet(f"""
        QFrame#central_frame {{
            background: {dark};
            border-radius: 8px;
        }}
        """)
        central_layout = QtWidgets.QVBoxLayout()
        central_layout.setContentsMargins(15, 10, 15, 15)
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
        self.btn_restore = QtWidgets.QPushButton("❐")
        self.btn_restore.setFixedSize(36, 28)
        self.btn_restore.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_restore.setStyleSheet(f"""
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
        self.btn_restore.setToolTip("Развернуть/Восстановить")
        title_layout.addWidget(self.btn_restore)
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
        # Song progress display
        self.song_display = QtWidgets.QTextEdit()
        self.song_display.setReadOnly(True)
        self.song_display.setMinimumHeight(80)
        self.song_display.setStyleSheet(f"""
        QTextEdit {{
            background: {panel};
            border-radius:8px;
            padding:8px;
            color:{text};
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        QTextEdit:hover {{
            border: 1px solid {gold};
        }}
        """)
        central_layout.addWidget(self.song_display)
        # Song input and playlist controls
        input_layout = QtWidgets.QHBoxLayout()
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText("Вставьте текст песни сюда и нажмите 'Добавить'")
        self.song_input.setMinimumHeight(80)
        self.song_input.setStyleSheet(f"background: {panel}; border-radius:8px; padding:8px; color:{text};")
        input_layout.addWidget(self.song_input, 3)
        
        # Playlist control buttons
        playlist_btns = QtWidgets.QVBoxLayout()
        self.add_btn = QtWidgets.QPushButton("➕ Добавить")
        self.save_playlist_btn = QtWidgets.QPushButton("💾 Сохранить")
        self.load_playlist_btn = QtWidgets.QPushButton("📂 Загрузить")
        for btn in (self.add_btn, self.save_playlist_btn, self.load_playlist_btn):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"border-radius:6px; border:1px solid rgba(212,175,55,0.12); background: transparent; color:{text};")
        playlist_btns.addWidget(self.add_btn)
        playlist_btns.addWidget(self.save_playlist_btn)
        playlist_btns.addWidget(self.load_playlist_btn)
        playlist_btns.addStretch()
        input_layout.addLayout(playlist_btns, 1)
        central_layout.addLayout(input_layout)
        # Control buttons
        control_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("▶ Start / Pause (F1)")
        self.next_btn = QtWidgets.QPushButton("⏭ Next Song (F8)")
        self.prev_mode_btn = QtWidgets.QPushButton("⏪ Prev Mode (F5)")
        self.next_mode_btn = QtWidgets.QPushButton("⏩ Next Mode (F7)")
        for btn in (self.start_btn, self.next_btn, self.prev_mode_btn, self.next_mode_btn):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(36)
            btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
        control_row.addWidget(self.start_btn)
        control_row.addWidget(self.next_btn)
        control_row.addWidget(self.prev_mode_btn)
        control_row.addWidget(self.next_mode_btn)
        central_layout.addLayout(control_row)
        # Split layout: playlist and status
        split_layout = QtWidgets.QHBoxLayout()
        # Left side - playlist
        playlist_layout = QtWidgets.QVBoxLayout()
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setStyleSheet(f"""
        QListWidget {{
            background: {panel};
            border-radius:10px;
            padding:6px;
            color:{text};
            border: 1px solid rgba(255,255,255,0.05);
        }}
        QListWidget::item:selected {{
            background: rgba(212,175,55,0.2);
            color: {soft_gold};
        }}
        """)
        # Enable drag-and-drop
        self.song_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.song_list.setDragEnabled(True)
        self.song_list.viewport().setAcceptDrops(True)
        self.song_list.setDropIndicatorShown(True)
        self.song_list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        for name, content in self.bot.playlist:
            self.song_list.addItem(f"{name} — {len(content)} chars")
        self.song_list.setCurrentRow(self.bot.song_index)
        playlist_layout.addWidget(self.song_list)
        # Playlist item controls
        list_controls = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton("🗑️ Удалить")
        self.rename_btn = QtWidgets.QPushButton("✏️ Переименовать")
        for btn in (self.remove_btn, self.rename_btn):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(30)
            btn.setStyleSheet("border-radius:6px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: %s;" % text)
        list_controls.addWidget(self.remove_btn)
        list_controls.addWidget(self.rename_btn)
        list_controls.addStretch()
        playlist_layout.addLayout(list_controls)
        # Overlay toggle button
        self.overlay_btn = QtWidgets.QPushButton("🎭 Показать/Скрыть ноты (F11)")
        self.overlay_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.overlay_btn.setFixedHeight(36)
        self.overlay_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color: %s;" % text)
        playlist_layout.addWidget(self.overlay_btn)
        split_layout.addLayout(playlist_layout, 2)
        # Right side - status and controls
        status_layout = QtWidgets.QVBoxLayout()
        # Status labels
        self.status_label = QtWidgets.QLabel("Status: Idle")
        self.mode_label = QtWidgets.QLabel("Mode: 1 — Ровный")
        self.pos_label = QtWidgets.QLabel(f"Pos: 0/{len(self.bot.song)}")
        for lbl in (self.status_label, self.mode_label, self.pos_label):
            lbl.setStyleSheet("color: %s;" % text)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.mode_label)
        status_layout.addWidget(self.pos_label)
        # Mode selection
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(QtWidgets.QLabel("Mode:"))
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([
            "1 - Ровный",
            "2 - Живой",
            "3 - Гибридный"
        ])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.setStyleSheet(f"background: {panel}; color:{text}; border-radius:6px; padding:6px;")
        mode_layout.addWidget(self.mode_combo)
        status_layout.addLayout(mode_layout)
        # Note delays
        delay_section = QtWidgets.QGroupBox("Случайные задержки для нот")
        delay_section.setStyleSheet(f"""
        QGroupBox {{
            color: {text};
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            margin-top: 1ex;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 3px;
        }}
        """)
        delay_layout = QtWidgets.QVBoxLayout()
        # Min delay
        min_layout = QtWidgets.QHBoxLayout()
        min_layout.addWidget(QtWidgets.QLabel("Мин. задержка (мс):"))
        self.min_delay_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.min_delay_slider.setMinimum(0)
        self.min_delay_slider.setMaximum(20)
        self.min_delay_slider.setValue(self.bot.min_note_delay)
        min_layout.addWidget(self.min_delay_slider)
        self.min_delay_value = QtWidgets.QLabel(str(self.bot.min_note_delay))
        min_layout.addWidget(self.min_delay_value)
        delay_layout.addLayout(min_layout)
        # Max delay
        max_layout = QtWidgets.QHBoxLayout()
        max_layout.addWidget(QtWidgets.QLabel("Макс. задержка (мс):"))
        self.max_delay_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.max_delay_slider.setMinimum(0)
        self.max_delay_slider.setMaximum(50)
        self.max_delay_slider.setValue(self.bot.max_note_delay)
        max_layout.addWidget(self.max_delay_slider)
        self.max_delay_value = QtWidgets.QLabel(str(self.bot.max_note_delay))
        max_layout.addWidget(self.max_delay_value)
        delay_layout.addLayout(max_layout)
        delay_section.setLayout(delay_layout)
        status_layout.addWidget(delay_section)
        # Start delay
        start_delay_layout = QtWidgets.QHBoxLayout()
        start_delay_layout.addWidget(QtWidgets.QLabel("Задержка запуска (мс):"))
        self.start_delay_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.start_delay_slider.setMinimum(0)
        self.start_delay_slider.setMaximum(100)
        self.start_delay_slider.setValue(int(self.bot.start_delay * 1000))
        start_delay_layout.addWidget(self.start_delay_slider)
        self.start_delay_value = QtWidgets.QLabel(f"{self.bot.start_delay*1000:.0f}")
        start_delay_layout.addWidget(self.start_delay_value)
        status_layout.addLayout(start_delay_layout)
        # Update section
        update_layout = QtWidgets.QHBoxLayout()
        self.update_btn = QtWidgets.QPushButton("🔄 Обновить клиент")
        self.update_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.update_btn.setFixedHeight(40)
        self.update_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.12); background: transparent; color: %s;" % text)
        self.update_animation = UpdateAnimation()
        update_layout.addWidget(self.update_btn)
        update_layout.addWidget(self.update_animation)
        update_layout.addStretch()
        status_layout.addLayout(update_layout)
        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        status_layout.addWidget(self.progress)
        split_layout.addLayout(status_layout, 1)
        central_layout.addLayout(split_layout)
        # Help text
        help_label = QtWidgets.QLabel(
            "F1 Play/Pause | F2 Restart | F3 Вперед 25 нот | F4 Назад 25 нот | F5 PrevMode | F6 Freeze\n"
            "F7 NextMode | F8 NextSong | F10 Force Roblox | F11 Toggle Notes Overlay | Double-click to edit | Drag to reorder"
        )
        help_label.setStyleSheet("color: #9b9b9b; font-size: 11px;")
        help_label.setWordWrap(True)
        central_layout.addWidget(help_label)
        # Footer
        footer_layout = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("AstraKeys — by SMisha2")
        self.signature.setStyleSheet(f"color: {gold};")
        build_date = datetime.now().strftime("%d.%m.%Y")
        self.version_label = QtWidgets.QLabel(f"v{CURRENT_VERSION} · {build_date}")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.28); font-size: 11px; margin-right: 8px;")
        footer_layout.addWidget(self.signature)
        footer_layout.addStretch()
        footer_layout.addWidget(self.version_label)
        central_layout.addLayout(footer_layout)
        self.central.setLayout(central_layout)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.central)
        # Stylesheets
        self.setStyleSheet(f"""
        QWidget {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: transparent;
            color: {text};
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: rgba(255,255,255,0.03);
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {soft_gold};
            width: 14px;
            border-radius: 7px;
        }}
        QComboBox {{
            padding: 6px;
            border-radius: 6px;
            background: {panel};
            border: 1px solid rgba(255,255,255,0.1);
        }}
        QProgressBar {{
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gold}, stop:1 {soft_gold});
            border-radius: 8px;
        }}
        QPushButton {{
            text-align: center;
        }}
        QPushButton:hover {{
            border-color: {gold};
        }}
        """)
        # Connect signals
        self.btn_close.clicked.connect(self.close_application)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_restore.clicked.connect(self.toggle_maximized)
        self.btn_about.clicked.connect(self.show_about)
        self.add_btn.clicked.connect(self.add_song_from_input)
        self.save_playlist_btn.clicked.connect(self.save_playlist)
        self.load_playlist_btn.clicked.connect(self.load_playlist_dialog)
        self.start_btn.clicked.connect(self.toggle_start)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_mode_btn.clicked.connect(self.prev_mode)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.song_list.itemDoubleClicked.connect(self.handle_item_double_click)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.rename_btn.clicked.connect(self.rename_selected)
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        self.mode_combo.currentIndexChanged.connect(self.mode_combo_changed)
        self.min_delay_slider.valueChanged.connect(self.min_delay_changed)
        self.max_delay_slider.valueChanged.connect(self.max_delay_changed)
        self.start_delay_slider.valueChanged.connect(self.start_delay_changed)
        self.update_btn.clicked.connect(self.gui_update_client)
        self.song_list.model().rowsMoved.connect(self.handle_rows_moved)
        # Enable window resizing
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMaximizeButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint)
        # Create overlay window
        self.overlay_window = NoteOverlayWindow()
        self.bot.set_overlay_window(self.overlay_window)
        self.update_animation.progress_updated.connect(self.update_progress_display)
    def resizeEvent(self, event):
        self.background.setFixedSize(self.size())
        super().resizeEvent(event)
    def min_delay_changed(self, value):
        self.bot.min_note_delay = value
        self.min_delay_value.setText(str(value))
        if self.bot.min_note_delay > self.bot.max_note_delay:
            self.bot.max_note_delay = self.bot.min_note_delay
            self.max_delay_slider.setValue(self.bot.max_note_delay)
            self.max_delay_value.setText(str(self.bot.max_note_delay))
        logger.info(f"Min note delay changed to {value}ms")
    def max_delay_changed(self, value):
        self.bot.max_note_delay = value
        self.max_delay_value.setText(str(value))
        if self.bot.max_note_delay < self.bot.min_note_delay:
            self.bot.min_note_delay = self.bot.max_note_delay
            self.min_delay_slider.setValue(self.bot.min_note_delay)
            self.min_delay_value.setText(str(self.bot.min_note_delay))
        logger.info(f"Max note delay changed to {value}ms")
    def start_delay_changed(self, value):
        self.bot.start_delay = value / 1000.0
        self.start_delay_value.setText(f"{value}")
        logger.info(f"Start delay changed to {value}ms")
    def update_progress_display(self, value):
        self.progress.setValue(value)
        if value >= 100:
            self.progress.setVisible(False)
    def handle_item_double_click(self, item):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            menu = QtWidgets.QMenu(self)
            rename_action = menu.addAction("✏️ Переименовать песню")
            edit_content_action = menu.addAction("📝 Редактировать ноты")
            action = menu.exec(QtGui.QCursor.pos())
            
            if action == rename_action:
                self.rename_selected()
            elif action == edit_content_action:
                self.edit_song_content(row)
    def edit_song_content(self, row):
        if 0 <= row < len(self.bot.playlist):
            name, content = self.bot.playlist[row]
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Редактировать ноты: {name}")
            dialog.setMinimumSize(600, 400)
            
            layout = QtWidgets.QVBoxLayout(dialog)
            
            # Добавляем текстовое поле для редактирования содержимого
            text_edit = QtWidgets.QTextEdit()
            text_edit.setPlainText(content)
            text_edit.setStyleSheet("""
                QTextEdit {
                    background: rgba(18,18,18,0.85);
                    border-radius:8px;
                    padding:8px;
                    color:#f5f3f1;
                    font-family: 'Courier New', monospace;
                    font-size: 13px;
                }
            """)
            layout.addWidget(text_edit)
            
            # Кнопки Ok/Cancel
            btn_layout = QtWidgets.QHBoxLayout()
            ok_btn = QtWidgets.QPushButton("Сохранить")
            ok_btn.setStyleSheet("background: #1a1a1a; border: 1px solid #d4af37; color: white; padding: 8px 16px; border-radius: 6px;")
            cancel_btn = QtWidgets.QPushButton("Отмена")
            cancel_btn.setStyleSheet("background: #1a1a1a; border: 1px solid #d4af37; color: white; padding: 8px 16px; border-radius: 6px;")
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            # Обработчики кнопок
            ok_btn.clicked.connect(lambda: self.save_song_content(row, text_edit.toPlainText(), dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
    def save_song_content(self, row, new_content, dialog):
        if 0 <= row < len(self.bot.playlist):
            name, old_content = self.bot.playlist[row]
            sanitized = self.bot.sanitize_song(new_content)
            self.bot.playlist[row] = (name, sanitized)
            if row == self.bot.song_index:
                self.bot.song = sanitized
            self.song_list.item(row).setText(f"{name} — {len(sanitized)} chars")
            logger.info(f"Song content '{name}' updated")
            dialog.accept()
    def handle_rows_moved(self, parent, start, end, destination, row):
        """Обработка перемещения элементов в плейлисте - исправлено дублирование"""
        if start == end:
            return
            
        # Блокируем сигналы во время обработки
        self.song_list.blockSignals(True)
        
        try:
            # Фиксируем текущую позицию и данные
            self.song_list.setCurrentRow(-1)  # Снимаем выделение
            
            # Создаем копию плейлиста
            new_playlist = self.bot.playlist.copy()
            
            # Определяем элементы для перемещения
            items_to_move = []
            for i in range(start, end + 1):
                items_to_move.append(self.bot.playlist[i])
            
            # Удаляем элементы из старых позиций (в обратном порядке, чтобы индексы не сбивались)
            for i in range(end, start - 1, -1):
                new_playlist.pop(i)
            
            # Определяем позицию вставки
            insert_pos = row
            if row > end + 1:
                insert_pos -= (end - start + 1)
            
            # Вставляем элементы в новую позицию
            for i, item in enumerate(items_to_move):
                new_playlist.insert(insert_pos + i, item)
            
            # Обновляем индекс текущей песни
            if self.bot.song_index >= start and self.bot.song_index <= end:
                # Текущая песня была в перемещаемой группе
                offset = self.bot.song_index - start
                self.bot.song_index = insert_pos + offset
            elif self.bot.song_index >= insert_pos and self.bot.song_index < insert_pos + len(items_to_move):
                # Текущая песня остается на месте
                pass
            elif self.bot.song_index >= start and self.bot.song_index < insert_pos:
                # Сдвигаем индекс вниз
                self.bot.song_index -= (end - start + 1)
            elif self.bot.song_index >= insert_pos and self.bot.song_index < start:
                # Сдвигаем индекс вверх
                self.bot.song_index += (end - start + 1)
            
            # Ограничиваем индекс диапазоном плейлиста
            self.bot.song_index = max(0, min(self.bot.song_index, len(new_playlist) - 1))
            
            # Обновляем плейлист
            self.bot.playlist = new_playlist
            self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
            
            # Обновляем отображение списка
            self.song_list.clear()
            for i, (name, content) in enumerate(self.bot.playlist):
                self.song_list.addItem(f"{name} — {len(content)} chars")
            
            # Устанавливаем выделение
            self.song_list.setCurrentRow(self.bot.song_index)
            
            logger.info(f"Playlist reordered. Current song: {self.bot.song_index + 1}/{len(self.bot.playlist)}")
            
        except Exception as e:
            logger.error(f"Error while moving playlist items: {e}")
            # Восстанавливаем оригинальное состояние
            self.song_list.clear()
            for i, (name, content) in enumerate(self.bot.playlist):
                self.song_list.addItem(f"{name} — {len(content)} chars")
            self.song_list.setCurrentRow(self.bot.song_index)
        finally:
            # Разблокируем сигналы
            self.song_list.blockSignals(False)
    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_restore.setText("❐")
        else:
            self.showMaximized()
            self.btn_restore.setText("❐")
    def close_application(self):
        self.save_window_state()
        self.overlay_window.close()
        logger.info("Application closed")
        sys.exit(0)
    def save_window_state(self):
        try:
            state = {
                "geometry": {
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                },
                "maximized": self.isMaximized()
            }
            with open("window_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            logger.info("Window state saved")
        except Exception as e:
            logger.error(f"Error saving window state: {e}")
    def load_window_state(self):
        try:
            if os.path.exists("window_state.json"):
                with open("window_state.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
                if not state.get("maximized", False):
                    geom = state.get("geometry", {})
                    if all(k in geom for k in ["x", "y", "width", "height"]):
                        self.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
                logger.info("Window state loaded")
        except Exception as e:
            logger.error(f"Error loading window state: {e}")
    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()
    def open_releases_page(self):
        webbrowser.open(RELEASES_URL)
    def check_internet_status(self):
        def worker():
            try:
                requests.get("https://api.github.com", timeout=3)
                logger.info("Internet connection available")
            except:
                logger.warning("No internet connection")
        threading.Thread(target=worker, daemon=True).start()
    def roblox_keepalive(self):
        """Keep Roblox window accessible without constant focus changes"""
        while True:
            try:
                find_roblox_window()
                time.sleep(5)
            except:
                time.sleep(5)
    def add_song_from_input(self):
        text = self.song_input.toPlainText().strip()
        if text:
            name, ok = QtWidgets.QInputDialog.getText(self, "Имя песни", "Введите название песни:", text=f"Song {len(self.bot.playlist)+1}")
            if not ok or not name.strip():
                name = f"Song {len(self.bot.playlist)+1}"
            sanitized = self.bot.sanitize_song(text)
            self.bot.playlist.append((name, sanitized))
            self.song_list.addItem(f"{name} — {len(sanitized)} chars")
            logger.info(f"Song '{name}' added")
            self.song_input.clear()
    def remove_selected(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            # Подтверждение удаления
            reply = QtWidgets.QMessageBox.question(
                self, 
                "Подтверждение удаления", 
                f"Вы уверены, что хотите удалить песню '{self.bot.playlist[row][0]}'?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return
                
            self.bot.playlist.pop(row)
            self.song_list.takeItem(row)
            if self.bot.song_index >= len(self.bot.playlist):
                self.bot.song_index = max(0, len(self.bot.playlist) - 1)
            if self.bot.playlist:
                self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
                self.song_list.setCurrentRow(self.bot.song_index)
            logger.info(f"Song removed. Now {len(self.bot.playlist)} songs in playlist.")
    def rename_selected(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            current_name, content = self.bot.playlist[row]
            new_name, ok = QtWidgets.QInputDialog.getText(self, "Переименовать песню", "Новое название:", text=current_name)
            if ok and new_name.strip():
                new_name = new_name.strip()
                # Проверяем, не существует ли уже песни с таким именем
                for i, (name, _) in enumerate(self.bot.playlist):
                    if i != row and name == new_name:
                        reply = QtWidgets.QMessageBox.question(
                            self, 
                            "Подтверждение переименования", 
                            f"Песня с названием '{new_name}' уже существует. Заменить?",
                            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                        )
                        if reply == QtWidgets.QMessageBox.StandardButton.No:
                            return
                        break
                self.bot.playlist[row] = (new_name, content)
                if row == self.bot.song_index:
                    self.bot.song_name = new_name
                self.song_list.item(row).setText(f"{new_name} — {len(content)} chars")
                logger.info(f"Renamed song to '{new_name}'")
    def toggle_start(self):
        self.bot.playing = not self.bot.playing
        logger.info(f"Playback {'started' if self.bot.playing else 'paused'}")
        self.refresh_status()
    def next_song(self):
        self.bot.next_song()
        self.song_list.setCurrentRow(self.bot.song_index)
        logger.info(f"Switched to next song: {self.bot.song_name}")
        self.refresh_status()
    def prev_mode(self):
        self.bot.mode = self.bot.mode - 1 if self.bot.mode > 1 else 3
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        logger.info(f"Mode changed to {self.bot.mode}")
        self.refresh_status()
    def next_mode(self):
        self.bot.mode = self.bot.mode + 1 if self.bot.mode < 3 else 1
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        logger.info(f"Mode changed to {self.bot.mode}")
        self.refresh_status()
    def mode_combo_changed(self, idx):
        self.bot.mode = idx + 1
        logger.info(f"Mode changed via combo to {self.bot.mode}")
        self.refresh_status()
    def save_playlist(self):
        try:
            playlist_data = [{"name": name, "content": content} for name, content in self.bot.playlist]
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Успешно", f"Плейлист сохранен в {PLAYLIST_FILE}")
            logger.info(f"Playlist saved to {PLAYLIST_FILE} with {len(self.bot.playlist)} songs")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить плейлист: {e}")
            logger.error(f"Failed to save playlist: {e}")
    def load_playlist(self):
        try:
            if os.path.exists(PLAYLIST_FILE):
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    playlist_data = json.load(f)
                self.bot.playlist = [(item["name"], item["content"]) for item in playlist_data]
                self.bot.song_index = 0
                if self.bot.playlist:
                    self.bot.song_name, self.bot.song = self.bot.playlist[0]
                self.refresh_playlist_display()
                logger.info(f"Playlist loaded from {PLAYLIST_FILE} with {len(self.bot.playlist)} songs")
                return True
        except Exception as e:
            logger.error(f"Failed to load playlist: {e}")
        return False
    def load_playlist_dialog(self):
        if self.load_playlist():
            QtWidgets.QMessageBox.information(self, "Успешно", f"Плейлист загружен из {PLAYLIST_FILE}")
        else:
            reply = QtWidgets.QMessageBox.question(
                self, "Плейлист не найден", 
                f"Файл {PLAYLIST_FILE} не найден или поврежден. Хотите загрузить песни из файла?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, "Загрузить плейлист", "", "JSON Files (*.json);;All Files (*)"
                )
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            playlist_data = json.load(f)
                        self.bot.playlist = [(item["name"], item["content"]) for item in playlist_data]
                        self.bot.song_index = 0
                        if self.bot.playlist:
                            self.bot.song_name, self.bot.song = self.bot.playlist[0]
                        self.refresh_playlist_display()
                        QtWidgets.QMessageBox.information(self, "Успешно", "Плейлист загружен")
                        logger.info(f"Playlist loaded from {file_path} with {len(self.bot.playlist)} songs")
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить плейлист: {e}")
                        logger.error(f"Failed to load playlist from {file_path}: {e}")
    def refresh_playlist_display(self):
        self.song_list.clear()
        for name, content in self.bot.playlist:
            self.song_list.addItem(f"{name} — {len(content)} chars")
        self.song_list.setCurrentRow(self.bot.song_index)
    def toggle_overlay(self):
        if self.overlay_window.isVisible():
            self.overlay_window.hide()
            logger.info("Overlay window hidden")
        else:
            self.overlay_window.show()
            logger.info("Overlay window shown")
    def refresh_status(self):
        st = "Playing" if self.bot.playing else "Paused"
        self.status_label.setText(f"Status: {st}")
        mode_names = {1: "Ровный", 2: "Живой", 3: "Гибридный"}
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
    def update_song_display(self):
        """Update the song display with current position highlighting"""
        if not self.bot.song:
            self.song_display.setPlainText("")
            return
        # Define display parameters
        chars_per_line = 45  # Characters per line
        lines_to_show = 3    # Number of lines to show
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
            if current_in_display < len(display_text) - 1 and display_text[current_in_display] == '[' and ']' in display_text[current_in_display+1:]:
                # Find the end of the chord
                end_bracket = -1
                for i in range(current_in_display + 1, min(current_in_display + 20, len(display_text))):
                    if display_text[i] == ']':
                        end_bracket = i
                        break
                if end_bracket != -1 and end_bracket < len(display_text):
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
            current_char = display_text[current_in_display] if current_in_display < len(display_text) else ''
            after = display_text[current_in_display + 1:] if current_in_display + 1 < len(display_text) else ''
            # Ensure current_char is not empty
            if current_char:
                highlighted = (
                    f'<span style="color: #ccc;">{before}</span>'
                    f'<span style="background-color: rgba(255,216,106,0.5); border-radius: 3px; padding: 0 2px; color: #ffd86a; font-weight: bold;">'
                    f'{current_char}'
                    f'</span>'
                    f'<span style="color: #ccc;">{after}</span>'
                )
                self.song_display.setHtml(highlighted)
                return
        # Fallback: no highlighting needed or possible
        self.song_display.setPlainText(display_text)
    def gui_update_client(self):
        self.update_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        threading.Thread(target=self._update_worker, daemon=True).start()
    def _update_worker(self):
        try:
            logger.info("Starting update check")
            info, err = fetch_latest_release_info()
            if err or not info:
                self.show_message_box("Ошибка", f"Не удалось получить информацию о релизах: {err or 'unknown'}")
                self.update_ui_after_update(False)
                return
            latest_tag = (info.get("tag_name") or info.get("name") or "").strip()
            latest_version = latest_tag.lstrip("v").strip()
            if not latest_version:
                body = info.get("body", "")
                m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", body)
                if m:
                    latest_version = m.group(1)
            if not latest_version:
                self.show_message_box("Ошибка", "Не удалось определить номер версии релиза.")
                self.update_ui_after_update(False)
                return
            if version_tuple(latest_version) <= version_tuple(CURRENT_VERSION):
                self.show_message_box("Обновления", "Установлена последняя версия.")
                self.update_ui_after_update(False)
                return
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self.show_message_box("Обновления", "Обнаружена новая версия, но нужный файл не найден в релизе.")
                self.update_ui_after_update(False)
                return
            tmp_name = "AstraKeys_update_tmp.exe"
            def prog_cb(pct):
                QtCore.QTimer.singleShot(0, lambda: self.update_animation.set_progress(pct))
            logger.info(f"Downloading update from {asset_url}")
            ok, derr = download_asset_to_file(asset_url, tmp_name, progress_callback=prog_cb)
            if not ok:
                self.show_message_box("Ошибка", f"Ошибка скачивания: {derr}")
                self.update_ui_after_update(False)
                try:
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception as e:
                    logger.error(f"Failed to remove temp file: {e}")
                return
            is_frozen = getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe")
            logger.info("Starting replacement process")
            try:
                perform_replacement_and_restart(tmp_name, ASSET_NAME, is_frozen)
            except Exception as e:
                self.show_message_box("Ошибка", f"Не удалось заменить файл при обновлении: {e}")
                self.update_ui_after_update(False)
                return
        except Exception as e:
            logger.error(f"Update process failed: {e}")
            self.show_message_box("Ошибка", f"Процесс обновления завершился с ошибкой: {e}")
        finally:
            QtCore.QTimer.singleShot(0, lambda: self.update_ui_after_update(False))
    def update_ui_after_update(self, busy=True):
        self.update_btn.setEnabled(True)
        if not busy:
            self.progress.setVisible(False)
            self.update_animation.set_progress(0)
    def show_message_box(self, title, text):
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
        ("Русская мелодия", r"ааааа[аф]ддддаа[см]мммм")
    ]
    bot = RobloxPianoBot(default_playlist)
    player_thread = threading.Thread(target=bot.play_song, daemon=True)
    player_thread.start()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    # Set application font
    font = QtGui.QFont("Segoe UI", 9)
    app.setFont(font)
    gui = BotGUI(bot)
    gui.show()
    logger.info("Application started successfully")
    sys.exit(app.exec())
