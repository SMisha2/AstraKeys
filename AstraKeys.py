# AstraKeys_v1.1.8 — Solar Gold / Pure Black
# by black
# Features: Russian keyboard support, transparent window when playing, animations, better update system

CURRENT_VERSION = "1.1.8"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"

import os
import sys
import time
import threading
import re
import random
from datetime import datetime
import webbrowser
import subprocess
import json
import shutil

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

# ============= CONSTANTS =============
PEDAL_KEYS = {"*", "[", "]"}

RU_EN_MAPPING = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y', 'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
    'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h', 'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': '\'',
    'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n', 'ь': 'm', 'б': ',', 'ю': '.', 'ё': '`',
    'Й': 'Q', 'Ц': 'W', 'У': 'E', 'К': 'R', 'Е': 'T', 'Н': 'Y', 'Г': 'U', 'Ш': 'I', 'Щ': 'O', 'З': 'P', 'Х': '{', 'Ъ': '}',
    'Ф': 'A', 'Ы': 'S', 'В': 'D', 'А': 'F', 'П': 'G', 'Р': 'H', 'О': 'J', 'Л': 'K', 'Д': 'L', 'Ж': ':', 'Э': '"',
    'Я': 'Z', 'Ч': 'X', 'С': 'C', 'М': 'V', 'И': 'B', 'Т': 'N', 'Ь': 'M', 'Б': '<', 'Ю': '>', 'Ё': '~'
}

# ✅ ИСПРАВЛЕННЫЙ ФИЛЬТР - ТОЛЬКО БЕЛЫЕ КЛАВИШИ И СПЕЦИАЛЬНЫЕ СИМВОЛЫ
ROBLOX_KEYS = "[]!@$%^*+-#(QWERTYUIOPASDFGHJKLZXCVBNM1234567890qwertyuiopasdfghjklzxcvbnm"

# БЕЛЫЕ КЛАВИШИ ДЛЯ ОШИБОЧНОГО РЕЖИМА
WHITE_KEYS = "qwertyuiopasdfghjklzxcvbnm1234567890"

# ============= AUTO-UPDATE HELPERS =============
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
    """✨ Новая версия открывается ПЕРВОЙ, потом закрывается старая"""
    try:
        if is_frozen or sys.argv[0].lower().endswith(".exe"):
            current_exec = os.path.basename(sys.argv[0])
            current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            new_path = os.path.join(current_dir, new_file)
            target_path = os.path.join(current_dir, target_name)
            old_backup = os.path.join(current_dir, f"{target_name}.old")
            
            bat_content = f"""@echo off
timeout /t 1 >nul
start "" "{new_path}"
timeout /t 3 >nul
:kill_loop
taskkill /f /im "{current_exec}" >nul 2>&1
timeout /t 1 >nul
tasklist | findstr /i "{current_exec}" >nul && goto kill_loop
if exist "{target_path}" (
    if exist "{old_backup}" del "{old_backup}" >nul 2>&1
    rename "{target_path}" "{target_name}.old" >nul 2>&1
    timeout /t 1 >nul
    del "{old_backup}" >nul 2>&1
)
rename "{new_path}" "{target_name}" >nul 2>&1
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

# ============= ROBLOX HELPERS =============
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

# ============= BOT CORE =============
class RobloxPianoBot:
    def __init__(self, playlist_with_names, bpm=100):
        self.keyboard = Controller() if Controller else None
        self.lock = threading.Lock()
        self.playlist = []
        for name, song in playlist_with_names:
            sanitized = self.sanitize_song(song)
            if sanitized:
                self.playlist.append((name, sanitized))
        
        self.load_playlist()
        
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
        self.error_rate = 0.05
        self.start_delay = 0.03
        self.active_keys = set()
        self.last_played_time = time.time()
        
        # ✨ ИСПРАВКА: Сохраняем какие РЕАЛЬНО нажаты клавиши (для mode 4)
        self.played_chord = []  # Сохраняем реально нажатые клавиши
        
        print("🎹 AstraKeys Bot v" + CURRENT_VERSION + " initialized")
        print("▶ F1 Play/Pause | F2 Restart | F3 Skip25 | F4 Exit")
        print("⭐ [ or ] - Pedal | F6 Freeze | F7 Next Mode | F5 Prev Mode | F8 Next Song | F10 Force Roblox")
        
        if Listener:
            threading.Thread(target=self.listen_keys, daemon=True).start()
    
    def sanitize_song(self, song):
        """Фильтр: оставляем ТОЛЬКО нужные символы"""
        if not song:
            return ""
        return ''.join(ch for ch in song if ch in ROBLOX_KEYS + "\t\n\r[]")
    
    def save_playlist(self, filename="playlist.json"):
        """💾 Сохранить плейлист в файл"""
        try:
            data = [{"name": name, "content": content} for name, content in self.playlist]
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Playlist saved to {filename}")
            return True
        except Exception as e:
            print(f"❌ Error saving playlist: {e}")
            return False
    
    def load_playlist(self, filename="playlist.json"):
        """📂 Загрузить плейлист из файла"""
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        self.playlist = [(item.get("name", f"Song {i+1}"), item.get("content", "")) 
                                         for i, item in enumerate(data) 
                                         if item.get("content")]
                        if self.playlist:
                            self.song_index = 0
                            self.song_name, self.song = self.playlist[self.song_index]
                            print(f"✅ Loaded {len(self.playlist)} songs from {filename}")
                            return True
            return False
        except Exception as e:
            print(f"❌ Error loading playlist: {e}")
            return False
    
    def convert_to_english(self, key):
        """Convert Russian key to English equivalent for Roblox"""
        if not key or not isinstance(key, str) or len(key) != 1:
            return key
        if key in RU_EN_MAPPING:
            return RU_EN_MAPPING[key]
        if key.lower() in RU_EN_MAPPING:
            converted = RU_EN_MAPPING[key.lower()]
            return converted.upper() if key.isupper() else converted
        return key
    
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
            key = self.convert_to_english(key)
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
            key = self.convert_to_english(key)
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
    
    def get_adjacent_keys(self, key):
        """🎹 Получить соседние клавиши для ошибочного режима"""
        # Клавиша и её соседи (слева и справа)
        keyboard_layout = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
        try:
            idx = keyboard_layout.index(key)
            adjacent = []
            if idx > 0:
                adjacent.append(keyboard_layout[idx - 1])
            if idx < len(keyboard_layout) - 1:
                adjacent.append(keyboard_layout[idx + 1])
            return adjacent if adjacent else [key]
        except ValueError:
            return [key]
    
    def apply_error(self, k):
        """✨ ИСПРАВЛЕННЫЙ ОШИБОЧНЫЙ РЕЖИМ
        - Работает ТОЛЬКО на белые клавиши
        - С шансом error_rate меняет ноту на соседнюю
        - Показывает, что произошла ошибка в консоль
        """
        try:
            if len(k) != 1:
                return k
            
            # Проверяем что это белая клавиша
            if k not in WHITE_KEYS:
                return k
            
            # Проверяем шанс ошибки
            if random.random() < self.error_rate:
                # Получаем соседние клавиши
                adjacent = self.get_adjacent_keys(k)
                if adjacent:
                    # Выбираем случайную соседнюю
                    wrong_key = random.choice(adjacent)
                    print(f"⚠️ ERROR: {k} → {wrong_key} (chance: {self.error_rate*100:.0f}%)")
                    return wrong_key
            
            return k
        except:
            return k
    
    def listen_keys(self):
        def on_press(key):
            try:
                key_char = getattr(key, 'char', None)
                is_bracket = False
                
                if hasattr(key, 'vk'):
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
                elif (key_char in PEDAL_KEYS) or is_bracket:
                    self.hold_star = True
                    key_repr = key_char or ("[" if hasattr(key, 'vk') and key.vk == 219 else "]")
                    print(f"Pedal down ({key_repr})")
            except Exception as e:
                print(f"Error in on_press: {e}")
        
        def on_release(key):
            try:
                key_char = getattr(key, 'char', None)
                is_bracket = False
                
                if hasattr(key, 'vk'):
                    if key.vk in (219, 221):
                        is_bracket = True
                elif isinstance(key, KeyCode) and hasattr(key, 'char') and key.char in ["[", "]", "{", "}"]:
                    is_bracket = True
                elif key_char in ["[", "]"]:
                    is_bracket = True
                
                if (key_char in PEDAL_KEYS) or is_bracket:
                    self.hold_star = False
                    key_repr = key_char or ("[" if hasattr(key, 'vk') and key.vk == 219 else "]")
                    print(f"Pedal up ({key_repr})")
            except Exception as e:
                print(f"Error in on_release: {e}")
        
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
        # Сохраняем исходный аккорд
        self.played_chord = chord.copy()
        
        if self.mode == 4:
            # Ошибочный режим: применяем ошибки ПЕРЕД нажатием
            chord = [self.apply_error(k) for k in chord]
            # 🔴 ВАЖНО: Сохраняем РЕАЛЬНО нажатые клавиши (с ошибками)
            self.played_chord = chord.copy()
        
        if self.mode == 1:
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
        elif self.mode == 4:
            for k in chord:
                self.press_key(k)
    
    def release_chord(self, chord):
        """Release chord with mode-specific timing"""
        if not chord:
            return
        
        # 🔴 ИСПРАВКА: Отпускаем РЕАЛЬНО нажатые клавиши (те, что в self.played_chord)
        # А не исходные ноты из аккорда
        release_keys = self.played_chord if self.played_chord else chord
        
        if self.mode == 1:
            for k in release_keys:
                self.release_key(k)
        elif self.mode == 2:
            for k in release_keys:
                delay = random.uniform(0.05, 0.2)
                t = threading.Timer(delay, self.release_key, args=[k])
                t.daemon = True
                t.start()
        elif self.mode == 3:
            base_release_delay = random.uniform(0.015, 0.04)
            for i, k in enumerate(release_keys):
                release_delay = base_release_delay + (i * 0.005)
                t_release = threading.Timer(release_delay, self.release_key, args=[k])
                t_release.daemon = True
                t_release.start()
        else:
            for k in release_keys:
                self.release_key(k)
        
        # Очищаем после отпускания
        self.played_chord = []
    
    def play_song(self):
        time.sleep(0.5)
        current_chord = None
        while True:
            try:
                if self.restart:
                    self.restart = False
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.release_all()
                    current_chord = None
                    self.played_chord = []  # 🔴 ИСПРАВКА
                    print("Restarted")
                    while self.hold_star:
                        time.sleep(0.01)
                    time.sleep(0.1)
                    continue
                
                if not self.playing:
                    time.sleep(0.05)
                    continue
                
                current_index = self.frozen_note_index if self.freeze_note else self.note_index
                if current_index >= len(self.song):
                    time.sleep(0.05)
                    continue
                
                char = self.song[current_index]
                
                if char.isspace():
                    if not self.freeze_note:
                        self.note_index += 1
                    time.sleep(0.01)
                    continue
                
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
                
                if not self.hold_star:
                    time.sleep(0.01)
                    continue
                
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
                
                if chord and chord[0] in ["[", "]"]:
                    if not self.freeze_note:
                        self.note_index = next_index
                    time.sleep(0.01)
                    continue
                
                bring_roblox_to_front()
                time.sleep(0.01)
                
                if self.start_delay > 0:
                    time.sleep(self.start_delay)
                
                self.play_chord(chord)
                current_chord = chord
                print(f"Played: {chord} at pos {current_index} | Actual: {self.played_chord}")
                
                while self.hold_star and self.playing and not self.restart:
                    time.sleep(0.01)
                
                if current_chord:
                    self.release_chord(current_chord)
                    current_chord = None
                
                if not self.freeze_note:
                    self.note_index = next_index
                
                time.sleep(0.001)
            except Exception as e:
                print("Main loop error:", e)
                time.sleep(0.1)

# ============= ABOUT DIALOG =============
class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе — AstraKeys")
        self.setFixedSize(400, 340)
        self.setStyleSheet("""
            QDialog {
                background: #000000;
                color: #f5f3f1;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 14px;
            }
            QLabel.title {
                font-size: 20px;
                font-weight: bold;
                color: #cfa00a;
            }
            QPushButton {
                background: #0a0a0a;
                border: 1px solid #cfa00a;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1a1a1a;
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
            "Поддерживает русскую раскладку,\n"
            "автоматическое обновление и многое другое."
        )
        desc.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        new_features = QtWidgets.QLabel(
            "Новые возможности v2.1.0:\n"
            "- Окно поверх Roblox + прозрачное для кликов\n"
            "- Гладкие анимации при наведении\n"
            "- Сохранение и загрузка плейлиста\n"
            "- Улучшенная система обновлений"
        )
        new_features.setStyleSheet("color: #5fd7ff; margin-top: 10px;")
        layout.addWidget(new_features)
        
        link = QtWidgets.QLabel(f'<a href="{RELEASES_URL}" style="color:#cfa00a;text-decoration:underline;">Скачать обновление</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(link)
        
        author = QtWidgets.QLabel("Исходный код: SMisha2")
        author.setStyleSheet("color: #cfa00a;")
        author.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)
        
        btn = QtWidgets.QPushButton("Закрыть")
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
        self.setLayout(layout)

# ============= GUI =============
class BotGUI(QtWidgets.QWidget):
    def __init__(self, bot: RobloxPianoBot):
        super().__init__()
        self.bot = bot
        self._is_on_top = False
        self._is_transparent = False
        
        self.setWindowTitle("AstraKeys — Solar Gold x Pure Black")
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        default_width = 750
        default_height = 580
        x = (screen.width() - default_width) // 2
        y = (screen.height() - default_height) // 2
        self.setGeometry(x, y, default_width, default_height)
        
        self.load_window_state()
        self.dragging = False
        self.drag_position = None
        
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
        
        self.roblox_thread = threading.Thread(target=self.roblox_keepalive, daemon=True)
        self.roblox_thread.start()
        
        self.check_internet_status()
        
        # 🎨 Анимация появления
        QtCore.QTimer.singleShot(100, self.animate_show)
    
    def animate_show(self):
        """Плавное появление окна при запуске"""
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(600)
        self.opacity_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutQuad)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.start()
    
    def set_on_top_if_playing(self):
        """✨ Управляет флагами окна: поверх + прозрачное для кликов при playing"""
        want_on_top = bool(self.bot.playing)
        want_transparent = bool(self.bot.playing)
        
        if want_on_top != self._is_on_top or want_transparent != self._is_transparent:
            if want_on_top:
                # 🎮 Окно поверх других + пропускает клики сквозь
                self.setWindowFlags(
                    QtCore.Qt.WindowType.Window |
                    QtCore.Qt.WindowType.WindowStaysOnTopHint |
                    QtCore.Qt.WindowType.WindowTransparentForInput
                )
            else:
                # 📝 Нормальное окно с возможностью клика
                self.setWindowFlags(
                    QtCore.Qt.WindowType.Window |
                    QtCore.Qt.WindowType.WindowMaximizeButtonHint |
                    QtCore.Qt.WindowType.WindowMinimizeButtonHint
                )
            self.show()
            self._is_on_top = want_on_top
            self._is_transparent = want_transparent
    
    def init_ui(self):
        # 🎨 ЦВЕТА: Pure Black + Solar Gold (#cfa00a)
        black = '#000000'
        panel = 'rgba(10,10,10,0.85)'
        gold = '#cfa00a'
        text = '#f5f3f1'
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.central = QtWidgets.QFrame()
        self.central.setObjectName("central_frame")
        self.central.setStyleSheet(f"""
            QFrame#central_frame {{
                background: {black};
                border-radius: 8px;
            }}
        """)
        
        central_layout = QtWidgets.QVBoxLayout()
        central_layout.setContentsMargins(15, 10, 15, 15)
        central_layout.setSpacing(8)
        
        # Title bar
        title_bar = QtWidgets.QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background: transparent;")
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.setContentsMargins(12, 0, 12, 0)
        title_layout.setSpacing(8)
        
        title_label = QtWidgets.QLabel("AstraKeys — Solar Gold x Pure Black")
        title_label.setStyleSheet(f"font-weight:600; font-size:14px; color: {gold};")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 🎘 Кнопки с анимацией
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
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.2);
                color: {gold};
                transform: scale(1.05);
            }}
            QPushButton:pressed {{
                background: rgba(207,160,10,0.3);
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
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.2);
            }}
            QPushButton:pressed {{
                background: rgba(207,160,10,0.3);
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
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.2);
            }}
            QPushButton:pressed {{
                background: rgba(207,160,10,0.3);
            }}
        """)
        self.btn_restore.setToolTip("Развернуть")
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
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(255,80,80,0.2);
                color: #ff6b6b;
            }}
            QPushButton:pressed {{
                background: rgba(255,80,80,0.3);
            }}
        """)
        self.btn_close.setToolTip("Закрыть")
        title_layout.addWidget(self.btn_close)
        
        title_bar.setLayout(title_layout)
        central_layout.addWidget(title_bar)
        
        subtitle = QtWidgets.QLabel("Premium Color Scheme for Piano Bot")
        subtitle.setStyleSheet(f"color: {gold}; font-size:12px; margin-left:14px;")
        central_layout.addWidget(subtitle)
        
        # Song display
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
                border: 1px solid rgba(207,160,10,0);
                transition: all 0.3s ease;
            }}
            QTextEdit:hover {{
                border: 1px solid rgba(207,160,10,0.3);
            }}
        """)
        central_layout.addWidget(self.song_display)
        
        # Song input
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText("Вставьте текст песни сюда и нажмите 'Добавить'")
        self.song_input.setMinimumHeight(100)
        self.song_input.setStyleSheet(f"""
            QTextEdit {{
                background: {panel};
                border-radius:8px;
                padding:8px;
                color:{text};
                border: 1px solid rgba(207,160,10,0);
                transition: all 0.3s ease;
            }}
            QTextEdit:hover {{
                border: 1px solid rgba(207,160,10,0.2);
            }}
        """)
        central_layout.addWidget(self.song_input)
        
        # Add button with 🎨 animation
        add_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Добавить песню")
        self.add_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.add_btn.setFixedHeight(36)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:8px;
                border:1px solid rgba(207,160,10,0.2);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
                border:1px solid rgba(207,160,10,0.5);
                padding: -2px;
            }}
            QPushButton:pressed {{
                background: rgba(207,160,10,0.25);
            }}
        """)
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        central_layout.addLayout(add_row)
        self.add_btn.clicked.connect(self.add_song_from_input)
        
        # Control buttons with animation
        control_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start / Pause (F1)")
        self.next_btn = QtWidgets.QPushButton("Next Song (F8)")
        self.prev_mode_btn = QtWidgets.QPushButton("Prev Mode (F5)")
        self.next_mode_btn = QtWidgets.QPushButton("Next Mode (F7)")
        
        button_style = f"""
            QPushButton {{
                border-radius:8px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
                border:1px solid rgba(207,160,10,0.4);
            }}
            QPushButton:pressed {{
                background: rgba(207,160,10,0.25);
            }}
        """
        
        for btn in (self.start_btn, self.next_btn, self.prev_mode_btn, self.next_mode_btn):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(36)
            btn.setStyleSheet(button_style)
            control_row.addWidget(btn)
        
        central_layout.addLayout(control_row)
        
        # Middle layout
        mid = QtWidgets.QHBoxLayout()
        
        # Left column - song list
        leftcol = QtWidgets.QVBoxLayout()
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setStyleSheet(f"""
            QListWidget {{
                background: {panel};
                border-radius:10px;
                padding:6px;
                color:{text};
                border: 1px solid rgba(207,160,10,0.1);
                transition: all 0.3s ease;
            }}
            QListWidget:hover {{
                border: 1px solid rgba(207,160,10,0.2);
            }}
            QListWidget::item:selected {{
                background: rgba(207,160,10,0.2);
                color: {gold};
                border-radius: 4px;
            }}
        """)
        for name, content in self.bot.playlist:
            self.song_list.addItem(f"{name} — {len(content)} chars")
        self.song_list.setCurrentRow(self.bot.song_index)
        leftcol.addWidget(self.song_list)
        
        list_controls = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton("Удалить")
        self.remove_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.remove_btn.setFixedHeight(30)
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:6px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
            }}
        """)
        list_controls.addWidget(self.remove_btn)
        
        self.rename_btn = QtWidgets.QPushButton("Переименовать")
        self.rename_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.rename_btn.setFixedHeight(30)
        self.rename_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:6px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
            }}
        """)
        list_controls.addWidget(self.rename_btn)
        
        # 💾 КНОПКИ СОХРАНЕНИЯ ПЛЕЙЛИСТА
        self.save_btn = QtWidgets.QPushButton("Сохранить")
        self.save_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.save_btn.setFixedHeight(30)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:6px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(76, 200, 76, 0.15);
            }}
        """)
        list_controls.addWidget(self.save_btn)
        
        self.load_btn = QtWidgets.QPushButton("Загрузить")
        self.load_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.load_btn.setFixedHeight(30)
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:6px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background: rgba(100, 150, 255, 0.15);
            }}
        """)
        list_controls.addWidget(self.load_btn)
        
        list_controls.addStretch()
        leftcol.addLayout(list_controls)
        mid.addLayout(leftcol, 2)
        
        # Right column - status
        right = QtWidgets.QVBoxLayout()
        self.status_label = QtWidgets.QLabel("Status: Idle")
        self.mode_label = QtWidgets.QLabel("Mode: 1")
        self.pos_label = QtWidgets.QLabel(f"Pos: 0/{len(self.bot.song)}")
        self.error_rate_label = QtWidgets.QLabel(f"Error Rate: {self.bot.error_rate*100:.0f}%")
        
        for lbl in (self.status_label, self.mode_label, self.pos_label, self.error_rate_label):
            lbl.setStyleSheet("color: %s;" % text)
            right.addWidget(lbl)
        
        error_layout = QtWidgets.QHBoxLayout()
        error_layout.addWidget(QtWidgets.QLabel("Error Rate:"))
        self.error_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.error_slider.setMinimum(0)
        self.error_slider.setMaximum(100)
        self.error_slider.setValue(int(self.bot.error_rate * 100))
        self.error_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: rgba(255,255,255,0.03);
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {gold};
                width: 14px;
                border-radius: 7px;
                transition: all 0.2s ease;
            }}
            QSlider::handle:horizontal:hover {{
                background: #e8b81f;
                width: 16px;
            }}
        """)
        error_layout.addWidget(self.error_slider)
        right.addLayout(error_layout)
        
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        right.addWidget(self.progress)
        
        mid.addLayout(right, 1)
        central_layout.addLayout(mid)
        
        # Bottom layout
        bottom_layout = QtWidgets.QHBoxLayout()
        
        delay_layout = QtWidgets.QHBoxLayout()
        self.delay_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.delay_slider.setMinimum(0)
        self.delay_slider.setMaximum(200)
        self.delay_slider.setValue(int(self.bot.start_delay * 1000))
        self.delay_label = QtWidgets.QLabel(f"Start Delay: {self.bot.start_delay:.3f}s")
        self.delay_label.setStyleSheet("color: %s;" % text)
        delay_layout.addWidget(self.delay_label)
        delay_layout.addWidget(self.delay_slider)
        
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(QtWidgets.QLabel("Mode:"))
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["1 - Ровный", "2 - Живой", "3 - Гибридный", "4 - Ошибочный"])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 6px;
                border-radius: 6px;
                background: rgba(207,160,10,0.05);
                border: 1px solid rgba(207,160,10,0.2);
                color:{text};
                transition: all 0.3s ease;
            }}
            QComboBox:hover {{
                background: rgba(207,160,10,0.12);
            }}
        """)
        mode_layout.addWidget(self.mode_combo)
        
        bottom_layout.addLayout(delay_layout, 2)
        bottom_layout.addLayout(mode_layout, 1)
        central_layout.addLayout(bottom_layout)
        
        help_label = QtWidgets.QLabel("F1 Start/Pause | F2 Restart | F3 Skip25 | F4 Exit | F5 PrevMode | F6 Freeze | F7 NextMode | F8 NextSong | F10 Force Roblox")
        help_label.setStyleSheet("color: #9b9b9b; font-size: 11px;")
        help_label.setWordWrap(True)
        central_layout.addWidget(help_label)
        
        # Update section
        update_layout = QtWidgets.QHBoxLayout()
        self.check_update_btn = QtWidgets.QPushButton("Проверить обновление")
        self.check_update_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.check_update_btn.setFixedHeight(36)
        self.check_update_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:8px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
            }}
        """)
        
        self.download_btn = QtWidgets.QPushButton("Скачать последнюю версию")
        self.download_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.download_btn.setFixedHeight(36)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                border-radius:8px;
                border:1px solid rgba(207,160,10,0.15);
                background: rgba(207,160,10,0.05);
                color:{text};
                transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            }}
            QPushButton:hover {{
                background: rgba(207,160,10,0.15);
            }}
        """)
        
        update_layout.addWidget(self.check_update_btn)
        update_layout.addWidget(self.download_btn)
        central_layout.addLayout(update_layout)
        
        self.check_update_btn.clicked.connect(self.gui_check_update)
        self.download_btn.clicked.connect(self.open_releases_page)
        
        footer = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("Исходный код: SMisha2")
        self.signature.setStyleSheet(f"color: {gold};")
        build_date = datetime.now().strftime("%d.%m.%Y")
        self.version_label = QtWidgets.QLabel(f"v{CURRENT_VERSION} · {build_date}")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.28); font-size: 11px; margin-right: 8px;")
        footer.addWidget(self.signature)
        footer.addStretch()
        footer.addWidget(self.version_label)
        central_layout.addLayout(footer)
        
        self.central.setLayout(central_layout)
        main_layout.addWidget(self.central)
        
        # Stylesheets
        self.setStyleSheet(f"""
            QWidget {{ 
                font-family: 'Segoe UI', Arial, sans-serif; 
                background: {black};
                color: {text};
            }}
            QSlider::groove:horizontal {{
                height: 8px; 
                background: rgba(255,255,255,0.03); 
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {gold}; 
                width: 14px; 
                border-radius: 7px;
                transition: all 0.2s ease;
            }}
            QProgressBar {{
                background: rgba(255,255,255,0.02); 
                border-radius: 8px; 
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gold}, stop:1 {gold}); 
                border-radius: 8px;
            }}
        """)
        
        # Connect signals
        self.btn_close.clicked.connect(self.close_application)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_restore.clicked.connect(self.toggle_maximized)
        self.btn_about.clicked.connect(self.show_about)
        
        self.add_btn.clicked.connect(self.add_song_from_input)
        self.start_btn.clicked.connect(self.toggle_start)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_mode_btn.clicked.connect(self.prev_mode)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.song_list.itemDoubleClicked.connect(self.rename_selected)
        self.delay_slider.valueChanged.connect(self.delay_changed)
        self.mode_combo.currentIndexChanged.connect(self.mode_combo_changed)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.rename_btn.clicked.connect(self.rename_selected)
        self.error_slider.valueChanged.connect(self.error_rate_changed)
        self.save_btn.clicked.connect(self.save_playlist)
        self.load_btn.clicked.connect(self.load_playlist)
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMaximizeButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint)
    
    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_restore.setText("❐")
        else:
            self.showMaximized()
            self.btn_restore.setText("❐")
    
    def close_application(self):
        self.save_window_state()
        self.bot.save_playlist()
        self.close()
    
    def save_window_state(self):
        try:
            state = {
                "geometry": {"x": self.x(), "y": self.y(), "width": self.width(), "height": self.height()},
                "maximized": self.isMaximized()
            }
            with open("window_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving window state: {e}")
    
    def load_window_state(self):
        try:
            if os.path.exists("window_state.json"):
                with open("window_state.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if not state.get("maximized", False):
                        geom = state.get("geometry", {})
                        if all(k in geom for k in ["x", "y", "width", "height"]):
                            self.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
        except Exception as e:
            print(f"Error loading window state: {e}")
    
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
    
    def save_playlist(self):
        """💾 Сохранить плейлист"""
        if self.bot.save_playlist():
            QtWidgets.QMessageBox.information(self, "✅ Успешно", "Плейлист сохранен в файл playlist.json")
        else:
            QtWidgets.QMessageBox.warning(self, "❌ Ошибка", "Не удалось сохранить плейлист")
    
    def load_playlist(self):
        """📂 Загрузить плейлист"""
        if self.bot.load_playlist():
            self.song_list.clear()
            for name, content in self.bot.playlist:
                self.song_list.addItem(f"{name} — {len(content)} chars")
            self.song_list.setCurrentRow(self.bot.song_index)
            QtWidgets.QMessageBox.information(self, "✅ Успешно", "Плейлист загружен из файла playlist.json")
        else:
            QtWidgets.QMessageBox.warning(self, "❌ Ошибка", "Не удалось загрузить плейлист")
    
    def toggle_start(self):
        self.bot.playing = not self.bot.playing
        self.set_on_top_if_playing()
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
    
    def error_rate_changed(self, val):
        self.bot.error_rate = val / 100.0
        self.error_rate_label.setText(f"Error Rate: {self.bot.error_rate*100:.0f}%")
    
    def mode_combo_changed(self, idx):
        self.bot.mode = idx + 1
        self.refresh_status()
    
    def update_song_display(self):
        """Update the song display with current position highlighting"""
        if not self.bot.song:
            self.song_display.setPlainText("")
            return
        
        chars_per_line = 45
        lines_to_show = 3
        total_chars = chars_per_line * lines_to_show
        
        current_pos = self.bot.frozen_note_index if self.bot.freeze_note else self.bot.note_index
        
        if current_pos >= len(self.bot.song):
            start_pos = max(0, len(self.bot.song) - total_chars)
            display_text = self.bot.song[start_pos:]
            self.song_display.setPlainText(display_text)
            return
        
        start_pos = max(0, current_pos - (total_chars // 3))
        display_text = self.bot.song[start_pos:start_pos + total_chars]
        
        if len(display_text) < total_chars and start_pos + total_chars > len(self.bot.song):
            start_pos = max(0, len(self.bot.song) - total_chars)
            display_text = self.bot.song[start_pos:start_pos + total_chars]
        
        current_in_display = current_pos - start_pos
        
        if 0 <= current_in_display < len(display_text):
            if current_in_display < len(display_text) - 1 and display_text[current_in_display] == '[':
                end_bracket = -1
                for i in range(current_in_display + 1, min(current_in_display + 20, len(display_text))):
                    if display_text[i] == ']':
                        end_bracket = i
                        break
                
                if end_bracket != -1 and end_bracket < len(display_text):
                    before = display_text[:current_in_display]
                    chord = display_text[current_in_display:end_bracket + 1]
                    after = display_text[end_bracket + 1:]
                    
                    highlighted = (
                        f'<span style="color: #ccc;">{before}</span>'
                        f'<span style="background-color: rgba(207,160,10,0.4); border-radius: 3px; padding: 0 2px; color: #cfa00a; font-weight: bold;">'
                        f'{chord}'
                        f'</span>'
                        f'<span style="color: #ccc;">{after}</span>'
                    )
                    self.song_display.setHtml(highlighted)
                    return
            
            if current_in_display < len(display_text):
                before = display_text[:current_in_display]
                current_char = display_text[current_in_display]
                after = display_text[current_in_display + 1:] if current_in_display + 1 < len(display_text) else ''
                
                highlighted = (
                    f'<span style="color: #ccc;">{before}</span>'
                    f'<span style="background-color: rgba(207,160,10,0.5); border-radius: 3px; padding: 0 2px; color: #cfa00a; font-weight: bold;">'
                    f'{current_char}'
                    f'</span>'
                    f'<span style="color: #ccc;">{after}</span>'
                )
                self.song_display.setHtml(highlighted)
                return
        
        self.song_display.setPlainText(display_text)
    
    def refresh_status(self):
        """Обновляем статус и проверяем флаги окна"""
        self.set_on_top_if_playing()
        
        st = "Playing" if self.bot.playing else "Paused"
        self.status_label.setText(f"Status: {st}")
        mode_names = {1: "Ровный", 2: "Живой", 3: "Гибридный", 4: "Ошибочный"}
        self.mode_label.setText(f"Mode: {self.bot.mode} — {mode_names.get(self.bot.mode,'?')}")
        
        try:
            self.pos_label.setText(f"Pos: {self.bot.note_index}/{len(self.bot.song)}")
            self.error_rate_label.setText(f"Error Rate: {self.bot.error_rate*100:.0f}%")
            if self.bot.mode == 4:
                self.error_rate_label.setVisible(True)
                self.error_slider.setVisible(True)
            else:
                self.error_rate_label.setVisible(False)
                self.error_slider.setVisible(False)
        except:
            self.pos_label.setText("Pos: 0/0")
        
        if self.mode_combo.currentIndex() != self.bot.mode - 1:
            self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)
        
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

# ============= MAIN RUNNER =============
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
    
    try:
        font_db = QtGui.QFontDatabase()
        if 'Montserrat' not in font_db.families():
            local_ttf = os.path.join(os.path.dirname(__file__) if '__file__' in globals() else '.', 'Montserrat-Regular.ttf')
            if os.path.exists(local_ttf):
                font_db.addApplicationFont(local_ttf)
    except Exception:
        pass
    
    font = QtGui.QFont("Segoe UI", 9)
    app.setFont(font)
    
    gui = BotGUI(bot)
    gui.show()
    
    sys.exit(app.exec())
