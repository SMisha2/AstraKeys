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
import html
import requests
from PyQt6 import QtWidgets, QtCore, QtGui

try:
    from midiutil import MIDIFile
    HAS_MIDI = True
except ImportError:
    HAS_MIDI = False

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

CURRENT_VERSION = "1.1.92"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
LOG_FILE = "astrakeys.log"
PLAYLIST_FILE = "playlist.json"

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

LANGUAGES = {
    'ru': {
        'app_title': 'AstraKeys — by SMisha2',
        'status': 'Статус:',
        'mode': 'Режим:',
        'pos': 'Поз:',
        'mode1': '1 - Без задержек',
        'mode2': '2 - С задержками',
        'delay_group': 'Случайные задержки для нот (режим 2)',
        'min_delay': 'Мин. задержка (мс):',
        'max_delay': 'Макс. задержка (мс):',
        'start_delay': 'Задержка запуска (мс):',
        'pedal_settings': 'Настройка педалей',
        'update_client': 'Обновить клиент',
        'show_log': 'Показать лог',
        'playlist_import': 'Импорт плейлиста',
        'playlist_export': 'Экспорт плейлиста',
        'add_song': 'Добавить',
        'save_playlist': 'Сохранить',
        'load_playlist': 'Загрузить',
        'start_btn': 'Старт / Пауза (F1)',
        'record_btn': 'Запись (F12)',
        'playback_btn': 'Воспр. запись',
        'stop_playback_btn': 'Остановить (F9)',
        'next_song_btn': 'След. песня (F8)',
        'next_mode_btn': 'След. режим (F7)',
        'remove_btn': 'Удалить',
        'rename_btn': 'Переименовать',
        'overlay_btn': 'Показать/Скрыть ноты',
        'recordings_btn': 'Управление записями',
        'help_text': 'F1 Старт/Пауза | F2 Рестарт | F3 Вперёд 25 нот | F4 Назад 25 нот | F6 Заморозка\nF7 След. режим | F8 След. песня | F9 Стоп воспр. | F12 Запись',
        'status_idle': 'Ожидание',
        'status_playing': 'Играет',
        'status_paused': 'Пауза',
        'status_playback': 'Воспроизведение',
        'mode_names': {1: 'Без задержек', 2: 'С задержками'},
        'about_title': 'О программе',
        'about_text': f'AstraKeys v{CURRENT_VERSION}\nАвтор: SMisha2\n\nПрограмма для игры на пианино в Roblox.\nПоддерживает запись и воспроизведение нажатий, экспорт в MIDI, настройку педалей, управление записями.',
        'no_recordings': 'Нет записей',
        'no_recordings_folder': 'Папка recordings не найдена',
        'no_recordings_files': 'Нет файлов записей',
        'load_error': 'Ошибка',
        'load_failed': 'Не удалось загрузить запись',
        'file_not_found': 'Файл записи не найден',
        'recording_name': 'Название записи',
        'enter_name': 'Введите название для записи:',
        'playlist_saved': 'Плейлист сохранён в {file}',
        'playlist_loaded': 'Плейлист загружен из {file}',
        'playlist_imported': 'Плейлист импортирован из {file}',
        'playlist_exported': 'Плейлист экспортирован в {file}',
        'export_dialog_title': 'Экспорт плейлиста',
        'export_filter': 'JSON-файлы (*.json)',
        'import_dialog_title': 'Импорт плейлиста',
        'import_filter': 'JSON-файлы (*.json)',
        'confirm_delete': 'Подтверждение удаления',
        'delete_song': 'Удалить \'{name}\'?',
        'rename_song': 'Переименовать',
        'new_name': 'Новое название:',
        'song_name': 'Название песни',
        'enter_song_name': 'Введите название:',
        'song_added': 'Песня \'{name}\' добавлена',
        'song_removed': 'Песня удалена. Теперь {count} песен в плейлисте.',
        'renamed': 'Переименовано в \'{name}\'',
        'overwrite_existing': 'Песня с названием \'{name}\' уже существует. Заменить?',
        'no_internet': 'Нет интернета',
        'internet_available': 'Интернет доступен',
        'update_check': 'Проверка обновлений...',
        'update_available': 'Доступно обновление!',
        'update_not_available': 'Установлена последняя версия.',
        'update_error': 'Ошибка обновления',
        'update_downloading': 'Загрузка обновления...',
        'update_complete': 'Обновление завершено',
        'log_window_title': 'Лог-файл',
        'log_copy': 'Копировать',
        'log_close': 'Закрыть',
        'playback_pause': 'Пауза',
        'playback_resume': 'Продолжить',
        'playback_paused_status': 'Пауза',
    },
    'en': {
        'app_title': 'AstraKeys — by SMisha2',
        'status': 'Status:',
        'mode': 'Mode:',
        'pos': 'Pos:',
        'mode1': '1 - No delays',
        'mode2': '2 - With delays',
        'delay_group': 'Random delays for notes (mode 2)',
        'min_delay': 'Min delay (ms):',
        'max_delay': 'Max delay (ms):',
        'start_delay': 'Start delay (ms):',
        'pedal_settings': 'Pedal settings',
        'update_client': 'Update client',
        'show_log': 'Show log',
        'playlist_import': 'Import playlist',
        'playlist_export': 'Export playlist',
        'add_song': 'Add',
        'save_playlist': 'Save',
        'load_playlist': 'Load',
        'start_btn': 'Start / Pause (F1)',
        'record_btn': 'Record (F12)',
        'playback_btn': 'Play recording',
        'stop_playback_btn': 'Stop (F9)',
        'next_song_btn': 'Next Song (F8)',
        'next_mode_btn': 'Next Mode (F7)',
        'remove_btn': 'Remove',
        'rename_btn': 'Rename',
        'overlay_btn': 'Show/Hide notes',
        'recordings_btn': 'Manage recordings',
        'help_text': 'F1 Play/Pause | F2 Restart | F3 Forward 25 notes | F4 Back 25 notes | F6 Freeze\nF7 Next Mode | F8 Next Song | F9 Stop playback | F12 Record',
        'status_idle': 'Idle',
        'status_playing': 'Playing',
        'status_paused': 'Paused',
        'status_playback': 'Playback',
        'mode_names': {1: 'No delays', 2: 'With delays'},
        'about_title': 'About',
        'about_text': f'AstraKeys v{CURRENT_VERSION}\nAuthor: SMisha2\n\nProgram for playing piano in Roblox.\nSupports recording and playback, MIDI export, pedal settings, recording management.',
        'no_recordings': 'No recordings',
        'no_recordings_folder': 'Recordings folder not found',
        'no_recordings_files': 'No recording files',
        'load_error': 'Error',
        'load_failed': 'Failed to load recording',
        'file_not_found': 'Recording file not found',
        'recording_name': 'Recording name',
        'enter_name': 'Enter name for recording:',
        'playlist_saved': 'Playlist saved to {file}',
        'playlist_loaded': 'Playlist loaded from {file}',
        'playlist_imported': 'Playlist imported from {file}',
        'playlist_exported': 'Playlist exported to {file}',
        'export_dialog_title': 'Export playlist',
        'export_filter': 'JSON Files (*.json)',
        'import_dialog_title': 'Import playlist',
        'import_filter': 'JSON Files (*.json)',
        'confirm_delete': 'Confirm deletion',
        'delete_song': 'Delete \'{name}\'?',
        'rename_song': 'Rename',
        'new_name': 'New name:',
        'song_name': 'Song name',
        'enter_song_name': 'Enter name:',
        'song_added': 'Song \'{name}\' added',
        'song_removed': 'Song removed. Now {count} songs in playlist.',
        'renamed': 'Renamed to \'{name}\'',
        'overwrite_existing': 'Song \'{name}\' already exists. Replace?',
        'no_internet': 'No internet',
        'internet_available': 'Internet available',
        'update_check': 'Checking for updates...',
        'update_available': 'Update available!',
        'update_not_available': 'Latest version installed.',
        'update_error': 'Update error',
        'update_downloading': 'Downloading update...',
        'update_complete': 'Update complete',
        'log_window_title': 'Log file',
        'log_copy': 'Copy',
        'log_close': 'Close',
        'playback_pause': 'Pause',
        'playback_resume': 'Resume',
        'playback_paused_status': 'Paused',
    },
    'uk': {
        'app_title': 'AstraKeys — by SMisha2',
        'status': 'Статус:',
        'mode': 'Режим:',
        'pos': 'Поз:',
        'mode1': '1 - Без затримок',
        'mode2': '2 - Із затримками',
        'delay_group': 'Випадкові затримки для нот (режим 2)',
        'min_delay': 'Мін. затримка (мс):',
        'max_delay': 'Макс. затримка (мс):',
        'start_delay': 'Затримка запуску (мс):',
        'pedal_settings': 'Налаштування педалей',
        'update_client': 'Оновити клієнт',
        'show_log': 'Показати лог',
        'playlist_import': 'Імпорт плейлиста',
        'playlist_export': 'Експорт плейлиста',
        'add_song': 'Додати',
        'save_playlist': 'Зберегти',
        'load_playlist': 'Завантажити',
        'start_btn': 'Старт / Пауза (F1)',
        'record_btn': 'Запис (F12)',
        'playback_btn': 'Відтворити запис',
        'stop_playback_btn': 'Зупинити (F9)',
        'next_song_btn': 'Наст. пісня (F8)',
        'next_mode_btn': 'Наст. режим (F7)',
        'remove_btn': 'Видалити',
        'rename_btn': 'Перейменувати',
        'overlay_btn': 'Показати/Сховати ноти',
        'recordings_btn': 'Керування записами',
        'help_text': 'F1 Старт/Пауза | F2 Рестарт | F3 Вперед 25 нот | F4 Назад 25 нот | F6 Заморозка\nF7 Наст. режим | F8 Наст. пісня | F9 Стоп відтворення | F12 Запис',
        'status_idle': 'Очікування',
        'status_playing': 'Грає',
        'status_paused': 'Пауза',
        'status_playback': 'Відтворення',
        'mode_names': {1: 'Без затримок', 2: 'Із затримками'},
        'about_title': 'Про програму',
        'about_text': f'AstraKeys v{CURRENT_VERSION}\nАвтор: SMisha2\n\nПрограма для гри на піаніно в Roblox.\nПідтримує запис і відтворення натискань, експорт у MIDI, налаштування педалей, керування записами.',
        'no_recordings': 'Немає записів',
        'no_recordings_folder': 'Папку recordings не знайдено',
        'no_recordings_files': 'Немає файлів записів',
        'load_error': 'Помилка',
        'load_failed': 'Не вдалося завантажити запис',
        'file_not_found': 'Файл запису не знайдено',
        'recording_name': 'Назва запису',
        'enter_name': 'Введіть назву для запису:',
        'playlist_saved': 'Плейлист збережено у {file}',
        'playlist_loaded': 'Плейлист завантажено з {file}',
        'playlist_imported': 'Плейлист імпортовано з {file}',
        'playlist_exported': 'Плейлист експортовано у {file}',
        'export_dialog_title': 'Експорт плейлиста',
        'export_filter': 'JSON-файли (*.json)',
        'import_dialog_title': 'Імпорт плейлиста',
        'import_filter': 'JSON-файли (*.json)',
        'confirm_delete': 'Підтвердження видалення',
        'delete_song': 'Видалити \'{name}\'?',
        'rename_song': 'Перейменувати',
        'new_name': 'Нова назва:',
        'song_name': 'Назва пісні',
        'enter_song_name': 'Введіть назву:',
        'song_added': 'Пісню \'{name}\' додано',
        'song_removed': 'Пісню видалено. Тепер {count} пісень у плейлисті.',
        'renamed': 'Перейменовано на \'{name}\'',
        'overwrite_existing': 'Пісня з назвою \'{name}\' вже існує. Замінити?',
        'no_internet': 'Немає інтернету',
        'internet_available': 'Інтернет доступний',
        'update_check': 'Перевірка оновлень...',
        'update_available': 'Доступне оновлення!',
        'update_not_available': 'Встановлено останню версію.',
        'update_error': 'Помилка оновлення',
        'update_downloading': 'Завантаження оновлення...',
        'update_complete': 'Оновлення завершено',
        'log_window_title': 'Лог-файл',
        'log_copy': 'Копіювати',
        'log_close': 'Закрити',
        'playback_pause': 'Пауза',
        'playback_resume': 'Продовжити',
        'playback_paused_status': 'Пауза',
    }
}

class Translator:
    _instance = None
    def __init__(self):
        self.lang = 'ru'
        self.load_lang()

    def load_lang(self):
        try:
            if os.path.exists('app_settings.json'):
                with open('app_settings.json', 'r', encoding='utf-8') as f:
                    s = json.load(f)
                    self.lang = s.get('lang', 'ru')
        except:
            pass

    def save_lang(self):
        try:
            with open('app_settings.json', 'r', encoding='utf-8') as f:
                s = json.load(f)
            s['lang'] = self.lang
            with open('app_settings.json', 'w', encoding='utf-8') as f:
                json.dump(s, f, indent=2)
        except:
            pass

    def set_lang(self, lang):
        if lang in LANGUAGES:
            self.lang = lang
            self.save_lang()

    def tr(self, key):
        return LANGUAGES.get(self.lang, {}).get(key, key)

tr_obj = Translator()
def tr(key):
    return tr_obj.tr(key)

DEFAULT_PEDAL_KEYS = {"-", "=", "[", "]"}
RU_EN_MAPPING = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y', 'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
    'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h', 'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': '\'',
    'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n', 'ь': 'm', 'б': ',', 'ю': '.', 'ё': '`',
    'Й': 'Q', 'Ц': 'W', 'У': 'E', 'К': 'R', 'Е': 'T', 'Н': 'Y', 'Г': 'U', 'Ш': 'I', 'Щ': 'O', 'З': 'P', 'Х': '{', 'Ъ': '}',
    'Ф': 'A', 'Ы': 'S', 'В': 'D', 'А': 'F', 'П': 'G', 'Р': 'H', 'О': 'J', 'Л': 'K', 'Д': 'L', 'Ж': ':', 'Э': '"',
    'Я': 'Z', 'Ч': 'X', 'С': 'C', 'М': 'V', 'И': 'B', 'Т': 'N', 'Ь': 'M', 'Б': '<', 'Ю': '>', 'Ё': '~',
    '!': '!', '@': '@', '#': '#', '$': '$', '%': '%', '^': '^', '&': '&', '*': '*',
    '(': '(', ')': ')', '-': '-', '_': '_', '=': '=', '+': '+', '\\': '\\', '|': '|',
    '/': '/', '?': '?', '.': '.', ',': ',', '"': '"', "'": "'", ';': ';', ':': ':',
    '<': '<', '>': '>', '[': '[', ']': ']', '{': '{', '}': '}' 
}
ROBLOX_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM!@$%^*()"

def is_valid_key(key):
    if not key or not isinstance(key, str) or len(key) != 1:
        return False
    return key in ROBLOX_KEYS

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

def fetch_latest_release_info():
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    try:
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        logger.error(f"Failed to fetch release info: {e}")
        return None, str(e)

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
                        try:
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                        except Exception as e:
                            logger.error(f"Failed to remove incomplete file: {e}")
                        continue
                    return False, "File size mismatch"
        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(f"Download failed (attempt {attempt+1}): {e}. Retrying...")
                time.sleep(2)
                try:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                except Exception as e2:
                    logger.error(f"Failed to remove file after error: {e2}")
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
            if os.path.exists(new_file):
                try:
                    os.remove(new_file)
                except Exception as e:
                    logger.error(f"Failed to remove temp file: {e}")
            os.execv(sys.executable, [sys.executable, target])
    except Exception as e:
        logger.error(f"Replacement error: {e}")
        raise

def version_tuple(v):
    try:
        return tuple(map(int, v.split(".")))
    except:
        return (0, 0, 0)

class NoteOverlayWindow(QtWidgets.QWidget):
    def __init__(self, bot=None, parent_gui=None):
        super().__init__(parent_gui)
        self.bot = bot
        self.parent_gui = parent_gui
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(0.92)

        self.opacity = 0.92
        self.font_size = 18
        self.lines = 4
        self.chars_per_line = 50
        self.bg_color = "#0a0a0a"
        self.text_color = "#ffd86a"
        self.highlight_bg = "rgba(255,216,106,0.35)"
        self.accent_color = "#d4af37"

        self.dragging = False
        self.drag_pos = None

        self.init_ui()
        self.load_settings()
        self.apply_settings()

        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.resize(520, 240)
        self.move(screen.width() // 2 - self.width() // 2, screen.height() - self.height() - 80)

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._perform_update)
        self.update_timer.start(100)
        self.pending_update = None

        self.current_song_name = ""
        self.current_progress = 0
        self.is_playing = False
        self.is_playback = False

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        top_bar = QtWidgets.QWidget()
        top_bar.setStyleSheet("background: transparent;")
        top_bar_layout = QtWidgets.QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.song_title = QtWidgets.QLabel("AstraKeys")
        self.song_title.setStyleSheet(f"color: {self.text_color}; font-weight: bold; font-size: 13px;")
        top_bar_layout.addWidget(self.song_title)

        self.progress_label = QtWidgets.QLabel("0%")
        self.progress_label.setStyleSheet(f"color: {self.accent_color}; font-size: 12px;")
        self.progress_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        top_bar_layout.addWidget(self.progress_label, 1)

        self.pin_btn = self._make_control_btn("📌", "Закрепить")
        self.opacity_btn = self._make_control_btn("👁️", "Прозрачность")
        self.close_btn = self._make_control_btn("✕", "Скрыть")
        top_bar_layout.addWidget(self.pin_btn)
        top_bar_layout.addWidget(self.opacity_btn)
        top_bar_layout.addWidget(self.close_btn)

        layout.addWidget(top_bar)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.bg_color};
                border: 1px solid {self.accent_color};
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: {self.text_color};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.accent_color}, stop:1 #ffd86a);
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self.note_label = QtWidgets.QLabel()
        self.note_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"""
            QLabel {{
                background: {self.bg_color};
                color: {self.text_color};
                font-family: 'Courier New', monospace;
                font-size: {self.font_size}px;
                border: 1px solid {self.accent_color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        layout.addWidget(self.note_label)

        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setStyleSheet("background: transparent;")
        bottom_bar_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QtWidgets.QLabel("Idle")
        self.status_label.setStyleSheet(f"color: {self.accent_color}; font-size: 11px;")
        bottom_bar_layout.addWidget(self.status_label)

        self.pos_label = QtWidgets.QLabel("0/0")
        self.pos_label.setStyleSheet(f"color: {self.text_color}; font-size: 11px;")
        self.pos_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        bottom_bar_layout.addWidget(self.pos_label, 1)

        layout.addWidget(bottom_bar)

        self.pin_btn.clicked.connect(self.toggle_pin)
        self.opacity_btn.clicked.connect(self.show_opacity_menu)
        self.close_btn.clicked.connect(self.hide)

        self.title_bar = top_bar

    def _make_control_btn(self, text, tip):
        btn = QtWidgets.QPushButton(text)
        btn.setFixedSize(26, 26)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(212,175,55,0.3);
                border-radius: 4px;
                color: #ccc;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(212,175,55,0.15);
                border-color: #ffd86a;
                color: #ffd86a;
            }
            QPushButton:pressed {
                background: rgba(212,175,55,0.3);
            }
        """)
        btn.setToolTip(tip)
        return btn

    def update_metadata(self, song_name, progress, is_playing, is_playback):
        self.current_song_name = song_name or "AstraKeys"
        self.current_progress = progress if progress is not None else 0
        self.is_playing = is_playing
        self.is_playback = is_playback
        self.song_title.setText(self.current_song_name[:30])
        self.progress_label.setText(f"{self.current_progress}%")
        self.progress_bar.setValue(self.current_progress)
        if is_playback:
            status = tr('status_playback')
        else:
            status = tr('status_playing') if is_playing else tr('status_paused')
        self.status_label.setText(status)

    def update_notes(self, song, current_pos, lines=None, chars_per_line=None):
        if lines is None:
            lines = self.lines
        if chars_per_line is None:
            chars_per_line = self.chars_per_line
        self.pending_update = (song, current_pos, lines, chars_per_line)

    def _perform_update(self):
        if self.pending_update is None:
            return
        song, current_pos, lines, chars_per_line = self.pending_update
        self.pending_update = None

        try:
            if not song or current_pos >= len(song):
                self.note_label.setText("")
                return

            end_pos = min(len(song), current_pos + lines * chars_per_line)
            display_text = song[current_pos:end_pos]

            lines_text = []
            current_line = ""
            i = 0
            while i < len(display_text):
                char = display_text[i]
                current_line += char
                if char == '[':
                    j = i + 1
                    while j < len(display_text) and display_text[j] != ']':
                        j += 1
                    if j < len(display_text):
                        current_line += display_text[i+1:j+1]
                        i = j + 1
                        if len(current_line) >= chars_per_line:
                            lines_text.append(current_line)
                            current_line = ""
                        continue
                i += 1
                if len(current_line) >= chars_per_line:
                    lines_text.append(current_line)
                    current_line = ""
            if current_line:
                lines_text.append(current_line)

            lines_text = lines_text[:lines]

            html_parts = []
            if lines_text:
                first_line = lines_text[0]
                if first_line:
                    first_char = html.escape(first_line[0])
                    rest = html.escape(first_line[1:]) if len(first_line) > 1 else ""
                    highlighted = (
                        f'<span style="background-color:{self.highlight_bg}; color:#ffd86a; font-weight:bold; padding:0 3px; border-radius:3px; border:1px solid #d4af37;">{first_char}</span>'
                        f'<span style="color:{self.text_color};">{rest}</span>'
                    )
                    html_parts.append(highlighted)
                else:
                    html_parts.append('<span style="color:{self.text_color};">&nbsp;</span>')
                for line in lines_text[1:]:
                    html_parts.append(f'<span style="color:{self.text_color};">{html.escape(line)}</span>')

            full_html = "<br>".join(html_parts)
            self.note_label.setText(full_html)

            if song:
                self.pos_label.setText(f"{current_pos}/{len(song)}")
            else:
                self.pos_label.setText("0/0")

        except Exception as e:
            logger.error(f"Overlay update error: {e}")

    def apply_settings(self):
        self.setWindowOpacity(self.opacity)
        self.note_label.setStyleSheet(f"""
            QLabel {{
                background: {self.bg_color};
                color: {self.text_color};
                font-family: 'Courier New', monospace;
                font-size: {self.font_size}px;
                border: 1px solid {self.accent_color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        self.song_title.setStyleSheet(f"color: {self.text_color}; font-weight: bold; font-size: 13px;")
        self.progress_label.setStyleSheet(f"color: {self.accent_color}; font-size: 12px;")
        self.status_label.setStyleSheet(f"color: {self.accent_color}; font-size: 11px;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.bg_color};
                border: 1px solid {self.accent_color};
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: {self.text_color};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.accent_color}, stop:1 #ffd86a);
                border-radius: 4px;
            }}
        """)

    def contextMenuEvent(self, event):
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
        font_sub = menu.addMenu("Размер шрифта")
        for size in [14, 16, 18, 20, 24, 28]:
            act = font_sub.addAction(f"{size}px")
            act.setData(size)
            act.triggered.connect(lambda checked, s=size: self.set_font_size(s))

        lines_sub = menu.addMenu("Строк")
        for l in [2, 3, 4, 5, 6]:
            act = lines_sub.addAction(f"{l}")
            act.setData(l)
            act.triggered.connect(lambda checked, l=l: self.set_lines(l))

        menu.addSeparator()
        reset_act = menu.addAction("Сбросить настройки")
        reset_act.triggered.connect(self.reset_settings)

        menu.exec(event.globalPos())

    def set_font_size(self, size):
        self.font_size = size
        self.apply_settings()
        self.save_settings()

    def set_lines(self, lines):
        self.lines = lines
        self.save_settings()

    def reset_settings(self):
        self.opacity = 0.92
        self.font_size = 18
        self.lines = 4
        self.chars_per_line = 50
        self.bg_color = "#0a0a0a"
        self.text_color = "#ffd86a"
        self.highlight_bg = "rgba(255,216,106,0.35)"
        self.accent_color = "#d4af37"
        self.apply_settings()
        self.save_settings()

    def load_settings(self):
        try:
            if os.path.exists("overlay_settings.json"):
                with open("overlay_settings.json", "r", encoding="utf-8") as f:
                    s = json.load(f)
                self.opacity = s.get("opacity", self.opacity)
                self.font_size = s.get("font_size", self.font_size)
                self.lines = s.get("lines", self.lines)
                self.chars_per_line = s.get("chars_per_line", self.chars_per_line)
                self.bg_color = s.get("bg_color", self.bg_color)
                self.text_color = s.get("text_color", self.text_color)
                self.highlight_bg = s.get("highlight_bg", self.highlight_bg)
                self.accent_color = s.get("accent_color", self.accent_color)
        except Exception as e:
            logger.error(f"Load overlay settings error: {e}")

    def save_settings(self):
        try:
            with open("overlay_settings.json", "w", encoding="utf-8") as f:
                json.dump({
                    "opacity": self.opacity,
                    "font_size": self.font_size,
                    "lines": self.lines,
                    "chars_per_line": self.chars_per_line,
                    "bg_color": self.bg_color,
                    "text_color": self.text_color,
                    "highlight_bg": self.highlight_bg,
                    "accent_color": self.accent_color
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Save overlay settings error: {e}")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self.dragging = True
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
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
        self.show()

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
        act = menu.addAction("1%")
        act.setData(0.01)
        for val in range(5, 101, 5):
            act = menu.addAction(f"{val}%")
            act.setData(val / 100.0)
        action = menu.exec(self.opacity_btn.mapToGlobal(QtCore.QPoint(0, self.opacity_btn.height())))
        if action:
            self.opacity = action.data()
            self.setWindowOpacity(self.opacity)
            self.save_settings()

    def closeEvent(self, event):
        self.save_settings()
        self.hide()
        event.ignore()

class PedalSettingsDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('pedal_settings'))
        self.setMinimumSize(300, 400)
        self.setStyleSheet("""
            QDialog { background-color: #0b0b0b; color: #f5f3f1; }
            QPushButton { background: #1a1a1a; border: 1px solid #d4af37; border-radius: 4px; padding: 6px; color: #f5f3f1; }
            QPushButton:hover { background: #2a2a2a; }
            QListWidget { background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; }
            QLineEdit { background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; padding: 4px; color: #f5f3f1; }
            QLabel { color: #f5f3f1; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel(tr('pedal_settings'))
        layout.addWidget(self.label)

        self.list_widget = QtWidgets.QListWidget()
        for key in sorted(self.bot.pedal_keys):
            self.list_widget.addItem(key)
        layout.addWidget(self.list_widget)

        input_layout = QtWidgets.QHBoxLayout()
        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setPlaceholderText("Введите символ")
        self.key_input.setMaxLength(1)
        input_layout.addWidget(self.key_input)

        self.add_btn = QtWidgets.QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_key)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton("Удалить выбранное")
        self.remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.remove_btn)

        self.reset_btn = QtWidgets.QPushButton("Сброс к стандартным")
        self.reset_btn.clicked.connect(self.reset_default)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_key(self):
        text = self.key_input.text().strip()
        if text and len(text) == 1:
            if text not in self.bot.pedal_keys:
                self.bot.pedal_keys.add(text)
                self.list_widget.addItem(text)
                self.key_input.clear()
                self.save_pedal_settings()

    def remove_selected(self):
        current = self.list_widget.currentRow()
        if current >= 0:
            item = self.list_widget.takeItem(current)
            key = item.text()
            if key in self.bot.pedal_keys:
                self.bot.pedal_keys.remove(key)
                self.save_pedal_settings()

    def reset_default(self):
        self.bot.pedal_keys = set(DEFAULT_PEDAL_KEYS)
        self.list_widget.clear()
        for key in sorted(self.bot.pedal_keys):
            self.list_widget.addItem(key)
        self.save_pedal_settings()

    def save_pedal_settings(self):
        try:
            with open("pedal_settings.json", "w", encoding="utf-8") as f:
                json.dump(list(self.bot.pedal_keys), f)
        except Exception as e:
            logger.error(f"Save pedal settings error: {e}")

    def load_pedal_settings(self):
        try:
            if os.path.exists("pedal_settings.json"):
                with open("pedal_settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    self.bot.pedal_keys = set(data)
                    self.list_widget.clear()
                    for key in sorted(self.bot.pedal_keys):
                        self.list_widget.addItem(key)
        except Exception as e:
            logger.error(f"Load pedal settings error: {e}")

    def accept(self):
        self.save_pedal_settings()
        super().accept()

class RobloxPianoBot:
    def __init__(self, playlist_with_names):
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
        self.min_note_delay = 0
        self.max_note_delay = 10
        self.pending_timers = []
        self.is_recording = False
        self.recording_events = []
        self.recording_start_time = None
        self.recording_song_name = ""
        self.is_playback = False
        self.playback_events = []
        self.playback_thread = None
        self.playback_stop = False
        self.playback_paused = False
        self.playback_pause_time = 0
        self.playback_elapsed = 0
        self.gui_update_callback = None
        self.overlay_window = None
        self.progress = 0

        self.pedal_keys = set(DEFAULT_PEDAL_KEYS)
        self.load_pedal_settings()

        self.recordings_index = []
        self.load_recordings_index()

        self.load_app_settings()

        logger.info("Bot initialized")
        if Listener:
            threading.Thread(target=self.listen_keys, daemon=True).start()

    def load_app_settings(self):
        try:
            if os.path.exists("app_settings.json"):
                with open("app_settings.json", "r", encoding="utf-8") as f:
                    s = json.load(f)
                self.mode = s.get("mode", 1)
                self.min_note_delay = s.get("min_delay", 0)
                self.max_note_delay = s.get("max_delay", 10)
                self.start_delay = s.get("start_delay", 0.03)
        except Exception as e:
            logger.error(f"Load app settings error: {e}")

    def save_app_settings(self):
        try:
            with open("app_settings.json", "w", encoding="utf-8") as f:
                json.dump({
                    "mode": self.mode,
                    "min_delay": self.min_note_delay,
                    "max_delay": self.max_note_delay,
                    "start_delay": self.start_delay,
                    "lang": tr_obj.lang
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Save app settings error: {e}")

    def load_pedal_settings(self):
        try:
            if os.path.exists("pedal_settings.json"):
                with open("pedal_settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    self.pedal_keys = set(data)
        except Exception as e:
            logger.error(f"Load pedal settings error: {e}")

    def load_recordings_index(self):
        try:
            if os.path.exists("recordings_index.json"):
                with open("recordings_index.json", "r", encoding="utf-8") as f:
                    self.recordings_index = json.load(f)
        except Exception as e:
            logger.error(f"Load recordings index error: {e}")

    def save_recordings_index(self):
        try:
            with open("recordings_index.json", "w", encoding="utf-8") as f:
                json.dump(self.recordings_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save recordings index error: {e}")

    def set_overlay_window(self, win):
        self.overlay_window = win

    def set_gui_update_callback(self, cb):
        self.gui_update_callback = cb

    def _gui_update(self):
        if self.gui_update_callback:
            QtCore.QTimer.singleShot(0, self.gui_update_callback)

    def sanitize_song(self, song):
        allowed = set(ROBLOX_KEYS + " \t\r[]")
        ru_keys = set(RU_EN_MAPPING.keys())
        return ''.join(ch for ch in song if ch in allowed or ch in ru_keys)

    def get_random_delay(self):
        return random.uniform(self.min_note_delay, self.max_note_delay) / 1000.0

    def press_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            key = self.convert_to_english(key)
            if not is_valid_key(key):
                return
            if key in self.active_keys and self.active_keys[key]:
                return
            try:
                needs_shift = key.isupper() and key.isalpha()
                base_key = key.lower() if needs_shift else key
                if needs_shift:
                    self.keyboard.press(Key.shift)
                    time.sleep(0.0001)
                self.keyboard.press(base_key)
                self.active_keys[key] = True
                if needs_shift:
                    time.sleep(0.0001)
                    self.keyboard.release(Key.shift)
            except Exception as e:
                logger.error(f"Press error: {e}")

    def release_key(self, key):
        with self.lock:
            if not self.keyboard:
                return
            key = self.convert_to_english(key)
            if not is_valid_key(key):
                return
            if key not in self.active_keys or not self.active_keys[key]:
                return
            try:
                needs_shift = key.isupper() and key.isalpha()
                base_key = key.lower() if needs_shift else key
                self.keyboard.release(base_key)
                self.active_keys[key] = False
            except Exception as e:
                logger.error(f"Release error: {e}")

    def convert_to_english(self, key):
        if not key or not isinstance(key, str):
            return key
        special = {
            '{': '[', '}': ']', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/', '|': '\\', '~': '`',
            '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
            '_': '-', '+': '='
        }
        if key in special:
            return special[key]
        lower = key.lower()
        if lower in RU_EN_MAPPING:
            conv = RU_EN_MAPPING[lower]
            if key.isupper() and conv.isalpha():
                return conv.upper()
            return conv
        return key

    def release_all(self):
        with self.lock:
            for k in list(self.active_keys.keys()):
                if self.active_keys.get(k, False):
                    try:
                        self.keyboard.release(k)
                    except:
                        pass
            self.active_keys.clear()
            for t in self.pending_timers:
                try:
                    t.cancel()
                except:
                    pass
            self.pending_timers.clear()

    def play_chord(self, chord):
        if self.mode == 1:
            for k in chord:
                self.press_key(k)
            time.sleep(0.001)
        else:
            delays = [self.get_random_delay() for _ in chord]
            threads = []
            for i, k in enumerate(chord):
                t = threading.Timer(delays[i], self.press_key, args=[k])
                t.daemon = True
                t.start()
                threads.append(t)
                self.pending_timers.append(t)
            time.sleep(max(delays) + 0.001)

    def release_chord(self, chord):
        if not chord:
            return
        if self.mode == 1:
            for k in reversed(chord):
                self.release_key(k)
            time.sleep(0.001)
        else:
            delays = [self.get_random_delay() for _ in chord]
            threads = []
            for i, k in enumerate(reversed(chord)):
                t = threading.Timer(delays[i], self.release_key, args=[k])
                t.daemon = True
                t.start()
                threads.append(t)
                self.pending_timers.append(t)
            time.sleep(max(delays) + 0.001)

    def next_song(self):
        n = len(self.playlist)
        if n == 0:
            return
        old = self.song_index
        for _ in range(n):
            self.song_index = (self.song_index + 1) % n
            if self.playlist[self.song_index][1]:
                self.song_name, self.song = self.playlist[self.song_index]
                self.note_index = 0
                self.frozen_note_index = 0
                self.progress = 0
                logger.info(f"Next song: {self.song_name}")
                self._gui_update()
                return
        self.song_index = old

    def export_recording_to_midi(self, events, filename):
        if not HAS_MIDI:
            logger.warning("MIDI export disabled: midiutil not installed")
            return
        if not events:
            return
        midi = MIDIFile(1)
        track = 0
        channel = 0
        min_time = min(ev['time'] for ev in events)
        tempo = 120
        midi.addTempo(track, 0, tempo)

        base_note = 60
        note_map = {}
        for i, letter in enumerate(['c', 'd', 'e', 'f', 'g', 'a', 'b']):
            note_map[letter] = base_note + i
        for i in range(1, 8):
            note_map[str(i)] = base_note + i + 5
        for i, letter in enumerate(['C', 'D', 'E', 'F', 'G', 'A', 'B']):
            note_map[letter] = base_note + i + 12
        special_map = {
            '!': 62, '@': 64, '#': 65, '$': 67, '%': 69, '^': 71, '&': 72, '*': 74,
            '(': 76, ')': 77, '_': 79, '+': 81, '{': 83, '}': 85, ':': 87, '"': 89,
            '<': 91, '>': 93, '?': 95, '/': 97, '|': 99, '\\': 101, '`': 103, '~': 105
        }
        note_map.update(special_map)

        press_times = {}
        for ev in events:
            if ev['action'] == 'press':
                chord = ev['key']
                note_char = chord[0] if chord else 'c'
                midi_note = note_map.get(note_char, 60)
                press_times[note_char] = (ev['time'] - min_time, midi_note)
            elif ev['action'] == 'release':
                note_char = ev['key']
                if note_char in press_times:
                    start_time, midi_note = press_times.pop(note_char)
                    duration = ev.get('duration', 0.2)
                    midi.addNote(track, channel, midi_note, start_time, duration, 100)
        for note_char, (start_time, midi_note) in press_times.items():
            midi.addNote(track, channel, midi_note, start_time, 0.2, 100)

        try:
            with open(filename, "wb") as f:
                midi.writeFile(f)
            logger.info(f"MIDI exported to {filename}")
        except Exception as e:
            logger.error(f"MIDI export error: {e}")

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.recording_events = []
        self.recording_start_time = time.time()
        self.recording_song_name = self.song_name
        logger.info("Recording started")
        self._gui_update()

    def stop_recording(self, custom_name=None):
        if not self.is_recording:
            return
        self.is_recording = False
        if not self.recording_events:
            logger.info("No events")
            self._gui_update()
            return
        press_times = {}
        processed = []
        for ev in self.recording_events:
            if ev['action'] == 'press':
                press_times[ev['key']] = ev['time']
            else:
                key = ev['key']
                if key in press_times:
                    dur = ev['time'] - press_times.pop(key)
                    processed.append({'time': ev['time'], 'key': key, 'action': 'release', 'duration': round(dur, 3)})
        data = {
            'song_name': self.recording_song_name,
            'start_time': datetime.now().isoformat(),
            'mode': self.mode,
            'min_delay': self.min_note_delay,
            'max_delay': self.max_note_delay,
            'start_delay': self.start_delay,
            'events': processed
        }
        os.makedirs("recordings", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = re.sub(r'[^\w\-_]', '_', self.recording_song_name)
        json_fname = f"recordings/{safe_name}_{timestamp}.json"
        try:
            with open(json_fname, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved recording to {json_fname}")
        except Exception as e:
            logger.error(f"Save recording error: {e}")
            return

        midi_fname = None
        if HAS_MIDI:
            midi_fname = f"recordings/{safe_name}_{timestamp}.mid"
            self.export_recording_to_midi(processed, midi_fname)

        entry = {
            "name": custom_name or self.recording_song_name,
            "json_file": os.path.basename(json_fname),
            "midi_file": os.path.basename(midi_fname) if midi_fname else None,
            "date": datetime.now().isoformat(),
            "favorite": False,
            "duration": round(processed[-1]['time'] if processed else 0, 2)
        }
        self.recordings_index.append(entry)
        self.save_recordings_index()

        self.recording_events = []
        self._gui_update()

    def load_recording(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.playback_events = data.get('events', [])
            if not self.playback_events:
                logger.warning("Recording file has no events")
                return False
            logger.info(f"Loaded {len(self.playback_events)} events from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Load recording error: {e}")
            return False

    def start_playback(self):
        if self.is_playback or not self.playback_events:
            return
        self.is_playback = True
        self.playback_stop = False
        self.playback_paused = False
        self.playback_elapsed = 0
        self.release_all()
        activate_roblox_window()
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        logger.info("Playback started")
        self._gui_update()

    def stop_playback(self):
        if not self.is_playback:
            return
        self.playback_stop = True
        if self.playback_thread:
            self.playback_thread.join(0.5)
        self.is_playback = False
        self.release_all()
        logger.info("Playback stopped")
        self._gui_update()

    def toggle_playback_pause(self):
        if not self.is_playback:
            return
        self.playback_paused = not self.playback_paused
        if self.playback_paused:
            self.playback_pause_time = time.time()
            logger.info("Playback paused")
        else:
            self.playback_elapsed += time.time() - self.playback_pause_time
            logger.info("Playback resumed")
        self._gui_update()

    def _playback_worker(self):
        start = time.time()
        self.playback_elapsed = 0
        for ev in self.playback_events:
            if self.playback_stop:
                break
            target = start + ev['time'] + self.playback_elapsed
            while time.time() < target - 0.001:
                if self.playback_stop:
                    break
                if self.playback_paused:
                    self.playback_elapsed += time.time() - self.playback_pause_time
                    self.playback_pause_time = time.time()
                    target = start + ev['time'] + self.playback_elapsed
                    time.sleep(0.05)
                    continue
                time.sleep(0.001)
            if self.playback_stop:
                break
            if self.playback_paused:
                while self.playback_paused and not self.playback_stop:
                    time.sleep(0.05)
                if self.playback_stop:
                    break
                self.playback_pause_time = time.time()
            chord_str = ev['key']
            action = ev['action']
            if action == 'press':
                for k in chord_str:
                    self.press_key(k)
            elif action == 'release':
                for k in chord_str:
                    self.release_key(k)
            else:
                logger.warning(f"Unknown action in playback: {action}")
            time.sleep(0.0005)
        self.release_all()
        self.is_playback = False
        self._gui_update()
        logger.info("Playback finished")

    def play_song(self):
        time.sleep(0.5)
        current_chord = None
        while True:
            try:
                if self.is_playback:
                    time.sleep(0.05)
                    continue

                if self.overlay_window and self.overlay_window.isVisible():
                    pos = self.frozen_note_index if self.freeze_note else self.note_index
                    self.overlay_window.update_notes(self.song, pos)

                if self.restart:
                    self.restart = False
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.progress = 0
                    self.release_all()
                    current_chord = None
                    while self.hold_star:
                        time.sleep(0.01)
                    time.sleep(0.1)
                    self._gui_update()
                    continue

                if not self.playing:
                    time.sleep(0.05)
                    continue

                idx = self.frozen_note_index if self.freeze_note else self.note_index
                if idx >= len(self.song):
                    self.playing = False
                    self.progress = 100
                    self._gui_update()
                    time.sleep(0.5)
                    continue

                char = self.song[idx]
                if char.isspace():
                    if not self.freeze_note:
                        self.note_index += 1
                    else:
                        self.frozen_note_index += 1
                    time.sleep(0.001)
                    continue

                if self.skip_notes != 0 and not self.freeze_note:
                    direction = 1 if self.skip_notes > 0 else -1
                    notes = abs(self.skip_notes)
                    for _ in range(notes):
                        char = self.song[self.note_index]
                        if direction > 0:
                            if char == '[':
                                end = self.song.find(']', self.note_index)
                                self.note_index = end + 1 if end != -1 else self.note_index + 1
                            else:
                                self.note_index += 1
                        else:
                            if self.note_index > 0:
                                prev = self.note_index - 1
                                while prev > 0 and self.song[prev].isspace():
                                    prev -= 1
                                if prev > 0 and self.song[prev] == ']':
                                    start = prev - 1
                                    while start > 0 and self.song[start] != '[':
                                        start -= 1
                                    self.note_index = start if start > 0 else prev
                                else:
                                    self.note_index = prev
                        if self.note_index < 0:
                            self.note_index = 0
                        if self.note_index >= len(self.song):
                            break
                    self.skip_notes = 0
                    continue

                if not self.hold_star:
                    time.sleep(0.001)
                    continue

                if char == '[':
                    end = self.song.find(']', idx)
                    if end == -1:
                        chord = [char]
                        next_idx = idx + 1
                    else:
                        chord_notes = ''.join(self.song[idx+1:end].split())
                        chord = list(chord_notes)
                        next_idx = end + 1
                else:
                    chord = [char]
                    next_idx = idx + 1

                if self.start_delay > 0:
                    time.sleep(self.start_delay)

                if self.is_recording:
                    elapsed = time.time() - self.recording_start_time
                    self.recording_events.append({'time': round(elapsed, 3), 'key': ''.join(chord), 'action': 'press'})

                self.play_chord(chord)
                current_chord = chord

                while self.hold_star and self.playing and not self.restart:
                    time.sleep(0.001)

                if current_chord:
                    if self.is_recording:
                        elapsed = time.time() - self.recording_start_time
                        self.recording_events.append({'time': round(elapsed, 3), 'key': ''.join(current_chord), 'action': 'release'})
                    self.release_chord(current_chord)
                    current_chord = None

                if not self.freeze_note:
                    self.note_index = next_idx

                if self.song:
                    self.progress = int(self.note_index * 100 / len(self.song))
                self._gui_update()

                time.sleep(0.0005)

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(0.05)

    def listen_keys(self):
        def on_press(key):
            try:
                key_char = getattr(key, 'char', None)
                if key == Key.f1:
                    self.playing = not self.playing
                    self._gui_update()
                    logger.info("Play/Pause")
                elif key == Key.f2:
                    self.restart = True
                    logger.info("Restart")
                elif key == Key.f3:
                    self.skip_notes += 25
                elif key == Key.f4:
                    self.skip_notes -= 25
                elif key == Key.f6:
                    self.freeze_note = not self.freeze_note
                    self.frozen_note_index = self.note_index if self.freeze_note else self.frozen_note_index
                    self._gui_update()
                    logger.info(f"Freeze: {self.freeze_note}")
                elif key == Key.f7:
                    self.mode = 2 if self.mode == 1 else 1
                    self._gui_update()
                    logger.info(f"Mode: {self.mode}")
                elif key == Key.f8:
                    self.next_song()
                elif key == Key.f9:
                    self.toggle_playback_pause()
                elif key == Key.f12:
                    if self.is_recording:
                        self.stop_recording()
                    else:
                        self.start_recording()
                    self._gui_update()
                elif key_char is not None and key_char in self.pedal_keys:
                    self.hold_star = True
                else:
                    if self.is_recording and key_char and len(key_char) == 1 and is_valid_key(key_char):
                        elapsed = time.time() - self.recording_start_time
                        self.recording_events.append({'time': round(elapsed, 3), 'key': key_char, 'action': 'press'})
            except Exception as e:
                logger.error(f"on_press error: {e}")

        def on_release(key):
            try:
                key_char = getattr(key, 'char', None)
                if key_char is not None and key_char in self.pedal_keys:
                    self.hold_star = False
                else:
                    if self.is_recording and key_char and len(key_char) == 1 and is_valid_key(key_char):
                        elapsed = time.time() - self.recording_start_time
                        self.recording_events.append({'time': round(elapsed, 3), 'key': key_char, 'action': 'release'})
            except Exception as e:
                logger.error(f"on_release error: {e}")

        try:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            logger.error(f"Listener failed: {e}")

class RecordingsManagerDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('recordings_btn'))
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #0b0b0b; color: #f5f3f1; }
            QPushButton { background: #1a1a1a; border: 1px solid #d4af37; border-radius: 4px; padding: 6px; color: #f5f3f1; }
            QPushButton:hover { background: #2a2a2a; }
            QListWidget { background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; }
            QLineEdit { background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; padding: 4px; color: #f5f3f1; }
            QLabel { color: #f5f3f1; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.list_widget = QtWidgets.QListWidget()
        self.refresh_list()
        layout.addWidget(self.list_widget)

        control_layout = QtWidgets.QHBoxLayout()
        self.rename_btn = QtWidgets.QPushButton(tr('rename_btn'))
        self.rename_btn.clicked.connect(self.rename_selected)
        control_layout.addWidget(self.rename_btn)

        self.fav_btn = QtWidgets.QPushButton("⭐ Избранное")
        self.fav_btn.clicked.connect(self.toggle_favorite)
        control_layout.addWidget(self.fav_btn)

        self.delete_btn = QtWidgets.QPushButton(tr('remove_btn'))
        self.delete_btn.clicked.connect(self.delete_selected)
        control_layout.addWidget(self.delete_btn)

        self.clean_btn = QtWidgets.QPushButton("🧹 Очистить не избранные")
        self.clean_btn.clicked.connect(self.clean_non_favorite)
        control_layout.addWidget(self.clean_btn)

        layout.addLayout(control_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def refresh_list(self):
        self.list_widget.clear()
        for idx, entry in enumerate(self.bot.recordings_index):
            name = entry.get('name', 'Без названия')
            date = entry.get('date', '')
            fav = '⭐' if entry.get('favorite', False) else ''
            dur = entry.get('duration', 0)
            display = f"{fav} {name}  (длит: {dur:.1f}с)  {date[:16] if date else ''}"
            self.list_widget.addItem(display)
            self.list_widget.item(self.list_widget.count()-1).setData(QtCore.Qt.ItemDataRole.UserRole, idx)

    def get_selected_index(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            return self.list_widget.item(row).data(QtCore.Qt.ItemDataRole.UserRole)
        return None

    def rename_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        entry = self.bot.recordings_index[idx]
        new_name, ok = QtWidgets.QInputDialog.getText(self, tr('rename_song'), tr('new_name'), text=entry.get('name', ''))
        if ok and new_name.strip():
            entry['name'] = new_name.strip()
            self.bot.save_recordings_index()
            self.refresh_list()

    def toggle_favorite(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        entry = self.bot.recordings_index[idx]
        entry['favorite'] = not entry.get('favorite', False)
        self.bot.save_recordings_index()
        self.refresh_list()

    def delete_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        entry = self.bot.recordings_index[idx]
        reply = QtWidgets.QMessageBox.question(
            self,
            tr('confirm_delete'),
            f"Удалить запись '{entry.get('name')}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        json_path = os.path.join("recordings", entry['json_file'])
        if os.path.exists(json_path):
            os.remove(json_path)
        if entry.get('midi_file'):
            midi_path = os.path.join("recordings", entry['midi_file'])
            if os.path.exists(midi_path):
                os.remove(midi_path)
        self.bot.recordings_index.pop(idx)
        self.bot.save_recordings_index()
        self.refresh_list()

    def clean_non_favorite(self):
        to_delete = [i for i, entry in enumerate(self.bot.recordings_index) if not entry.get('favorite', False)]
        if not to_delete:
            QtWidgets.QMessageBox.information(
                self,
                "Очистка",
                "Нет не избранных записей.",
                QtWidgets.QMessageBox.StandardButton.Ok
            )
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Очистка",
            f"Удалить {len(to_delete)} не избранных записей?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        for i in sorted(to_delete, reverse=True):
            entry = self.bot.recordings_index[i]
            json_path = os.path.join("recordings", entry['json_file'])
            if os.path.exists(json_path):
                os.remove(json_path)
            if entry.get('midi_file'):
                midi_path = os.path.join("recordings", entry['midi_file'])
                if os.path.exists(midi_path):
                    os.remove(midi_path)
            self.bot.recordings_index.pop(i)
        self.bot.save_recordings_index()
        self.refresh_list()
        QtWidgets.QMessageBox.information(
            self,
            "Очистка",
            f"Удалено {len(to_delete)} записей.",
            QtWidgets.QMessageBox.StandardButton.Ok
        )

class LogViewerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('log_window_title'))
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #0b0b0b; color: #f5f3f1; }
            QPushButton { background: #1a1a1a; border: 1px solid #d4af37; border-radius: 4px; padding: 6px; color: #f5f3f1; }
            QPushButton:hover { background: #2a2a2a; }
            QTextEdit { background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; font-family: monospace; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self.load_log())
        layout.addWidget(self.text_edit)

        btn_layout = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton(tr('log_copy'))
        copy_btn.clicked.connect(self.copy_log)
        btn_layout.addWidget(copy_btn)

        close_btn = QtWidgets.QPushButton(tr('log_close'))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def load_log(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return ''.join(lines[-1000:])
            return "Лог-файл не найден."
        except Exception as e:
            return f"Ошибка чтения лога: {e}"

    def copy_log(self):
        QtWidgets.QApplication.clipboard().setText(self.text_edit.toPlainText())
        QtWidgets.QMessageBox.information(
            self,
            "Копирование",
            "Текст скопирован в буфер обмена.",
            QtWidgets.QMessageBox.StandardButton.Ok
        )

class BotGUI(QtWidgets.QWidget):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.bot.set_gui_update_callback(self.on_state_changed)
        self.setWindowTitle(tr('app_title'))
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width()//2 - 390, screen.height()//2 - 325, 780, 650)
        self.load_window_state()
        self.init_ui()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(150)

        self.overlay_window = NoteOverlayWindow(bot=self.bot, parent_gui=self)
        self.bot.set_overlay_window(self.overlay_window)

        self.check_internet()
        self.load_playlist()

    def init_ui(self):
        dark = '#0b0b0b'
        panel = 'rgba(11,11,11,0.92)'
        gold = '#d4af37'
        soft_gold = '#ffd86a'
        text = '#f5f3f1'

        self.central = QtWidgets.QFrame()
        self.central.setObjectName("central_frame")
        self.central.setStyleSheet(f"QFrame#central_frame {{ background: {dark}; border-radius: 8px; }}")

        layout = QtWidgets.QVBoxLayout(self.central)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(8)

        title_bar = QtWidgets.QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QtWidgets.QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 0, 12, 0)
        title_label = QtWidgets.QLabel(tr('app_title'))
        title_label.setStyleSheet(f"font-weight:600; font-size:14px; color: {soft_gold};")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        self.about_btn = QtWidgets.QPushButton("?")
        self.about_btn.setFixedSize(30, 28)
        self.about_btn.setStyleSheet(f"border:none; background:transparent; color:{text}; font-size:14px;")
        self.about_btn.setToolTip(tr('about_title'))
        title_bar_layout.addWidget(self.about_btn)
        layout.addWidget(title_bar)

        self.song_display = QtWidgets.QTextEdit()
        self.song_display.setReadOnly(True)
        self.song_display.setMinimumHeight(80)
        self.song_display.setStyleSheet(f"background: {panel}; border-radius:8px; padding:8px; color:{text}; font-family: 'Courier New', monospace; font-size:13px;")
        layout.addWidget(self.song_display)

        input_layout = QtWidgets.QHBoxLayout()
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText("Вставьте текст песни сюда и нажмите 'Добавить'")
        self.song_input.setMinimumHeight(80)
        self.song_input.setStyleSheet(f"background:{panel}; border-radius:8px; padding:8px; color:{text};")
        input_layout.addWidget(self.song_input, 3)

        btn_layout = QtWidgets.QVBoxLayout()
        self.add_btn = QtWidgets.QPushButton(tr('add_song'))
        self.save_btn = QtWidgets.QPushButton(tr('save_playlist'))
        self.load_btn = QtWidgets.QPushButton(tr('load_playlist'))
        self.import_btn = QtWidgets.QPushButton(tr('playlist_import'))
        self.export_btn = QtWidgets.QPushButton(tr('playlist_export'))
        for b in (self.add_btn, self.save_btn, self.load_btn, self.import_btn, self.export_btn):
            b.setFixedHeight(30)
            b.setStyleSheet(f"border-radius:6px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout, 1)
        layout.addLayout(input_layout)

        control_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton(tr('start_btn'))
        self.record_btn = QtWidgets.QPushButton(tr('record_btn'))
        self.playback_btn = QtWidgets.QPushButton(tr('playback_btn'))
        self.stop_playback_btn = QtWidgets.QPushButton(tr('stop_playback_btn'))
        self.stop_playback_btn.setVisible(False)
        self.pause_playback_btn = QtWidgets.QPushButton(tr('playback_pause'))
        self.pause_playback_btn.setVisible(False)
        self.next_btn = QtWidgets.QPushButton(tr('next_song_btn'))
        self.next_mode_btn = QtWidgets.QPushButton(tr('next_mode_btn'))
        for b in (self.start_btn, self.record_btn, self.playback_btn, self.stop_playback_btn, self.pause_playback_btn, self.next_btn, self.next_mode_btn):
            b.setFixedHeight(36)
            b.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.08); background:transparent; color:{text};")
        control_row.addWidget(self.start_btn)
        control_row.addWidget(self.record_btn)
        control_row.addWidget(self.playback_btn)
        control_row.addWidget(self.stop_playback_btn)
        control_row.addWidget(self.pause_playback_btn)
        control_row.addWidget(self.next_btn)
        control_row.addWidget(self.next_mode_btn)
        layout.addLayout(control_row)

        split = QtWidgets.QHBoxLayout()
        left = QtWidgets.QVBoxLayout()
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.song_list.setStyleSheet(f"background:{panel}; border-radius:10px; padding:6px; color:{text}; border:1px solid rgba(255,255,255,0.05);")
        for name, _ in self.bot.playlist:
            self.song_list.addItem(name)
        self.song_list.setCurrentRow(self.bot.song_index)
        left.addWidget(self.song_list)

        list_controls = QtWidgets.QHBoxLayout()
        self.remove_btn = QtWidgets.QPushButton(tr('remove_btn'))
        self.rename_btn = QtWidgets.QPushButton(tr('rename_btn'))
        for b in (self.remove_btn, self.rename_btn):
            b.setFixedHeight(30)
            b.setStyleSheet(f"border-radius:6px; border:1px solid rgba(212,175,55,0.08); background:transparent; color:{text};")
        list_controls.addWidget(self.remove_btn)
        list_controls.addWidget(self.rename_btn)
        list_controls.addStretch()
        left.addLayout(list_controls)

        self.overlay_btn = QtWidgets.QPushButton(tr('overlay_btn'))
        self.overlay_btn.setFixedHeight(36)
        self.overlay_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        left.addWidget(self.overlay_btn)

        self.recordings_btn = QtWidgets.QPushButton(tr('recordings_btn'))
        self.recordings_btn.setFixedHeight(36)
        self.recordings_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        self.recordings_btn.clicked.connect(self.open_recordings_manager)
        left.addWidget(self.recordings_btn)

        split.addLayout(left, 2)

        right = QtWidgets.QVBoxLayout()
        self.status_label = QtWidgets.QLabel(tr('status') + " " + tr('status_idle'))
        self.mode_label = QtWidgets.QLabel(tr('mode') + " 1 — " + tr('mode_names')[1])
        self.pos_label = QtWidgets.QLabel(tr('pos') + " 0/0")
        for lbl in (self.status_label, self.mode_label, self.pos_label):
            lbl.setStyleSheet(f"color:{text};")
        right.addWidget(self.status_label)
        right.addWidget(self.mode_label)
        right.addWidget(self.pos_label)

        lang_layout = QtWidgets.QHBoxLayout()
        lang_layout.addWidget(QtWidgets.QLabel("Язык / Language:"))
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(['Русский', 'English', 'Українська'])
        lang_codes = ['ru', 'en', 'uk']
        current_lang = tr_obj.lang
        self.lang_combo.setCurrentIndex(lang_codes.index(current_lang) if current_lang in lang_codes else 0)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        right.addLayout(lang_layout)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([tr('mode1'), tr('mode2')])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.setStyleSheet(f"background:{panel}; color:{text}; border-radius:6px; padding:6px;")
        right.addWidget(self.mode_combo)

        delay_group = QtWidgets.QGroupBox(tr('delay_group'))
        delay_group.setObjectName("delay_group")
        delay_group.setStyleSheet(f"QGroupBox {{ color: {text}; border:1px solid rgba(255,255,255,0.1); border-radius:6px; margin-top:1ex; }} QGroupBox::title {{ subcontrol-origin:margin; left:8px; padding:0 3px; }}")
        delay_layout = QtWidgets.QVBoxLayout()

        min_layout = QtWidgets.QHBoxLayout()
        min_layout.addWidget(QtWidgets.QLabel(tr('min_delay')))
        self.min_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.min_slider.setMinimum(0)
        self.min_slider.setMaximum(200)
        self.min_slider.setValue(self.bot.min_note_delay)
        min_layout.addWidget(self.min_slider)
        self.min_label = QtWidgets.QLabel(str(self.bot.min_note_delay))
        min_layout.addWidget(self.min_label)
        delay_layout.addLayout(min_layout)

        max_layout = QtWidgets.QHBoxLayout()
        max_layout.addWidget(QtWidgets.QLabel(tr('max_delay')))
        self.max_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.max_slider.setMinimum(0)
        self.max_slider.setMaximum(500)
        self.max_slider.setValue(self.bot.max_note_delay)
        max_layout.addWidget(self.max_slider)
        self.max_label = QtWidgets.QLabel(str(self.bot.max_note_delay))
        max_layout.addWidget(self.max_label)
        delay_layout.addLayout(max_layout)

        delay_group.setLayout(delay_layout)
        right.addWidget(delay_group)

        start_delay_layout = QtWidgets.QHBoxLayout()
        start_delay_layout.addWidget(QtWidgets.QLabel(tr('start_delay')))
        self.start_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.start_slider.setMinimum(0)
        self.start_slider.setMaximum(100)
        self.start_slider.setValue(int(self.bot.start_delay * 1000))
        start_delay_layout.addWidget(self.start_slider)
        self.start_label = QtWidgets.QLabel(f"{self.bot.start_delay*1000:.0f}")
        start_delay_layout.addWidget(self.start_label)
        right.addLayout(start_delay_layout)

        pedal_btn = QtWidgets.QPushButton(tr('pedal_settings'))
        pedal_btn.setFixedHeight(36)
        pedal_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        pedal_btn.clicked.connect(self.open_pedal_settings)
        right.addWidget(pedal_btn)

        show_log_btn = QtWidgets.QPushButton(tr('show_log'))
        show_log_btn.setFixedHeight(36)
        show_log_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        show_log_btn.clicked.connect(self.show_log)
        right.addWidget(show_log_btn)

        self.update_progress = QtWidgets.QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setRange(0, 100)
        self.update_progress.setValue(0)
        right.addWidget(self.update_progress)

        update_layout = QtWidgets.QHBoxLayout()
        self.update_btn = QtWidgets.QPushButton(tr('update_client'))
        self.update_btn.setFixedHeight(40)
        self.update_btn.setStyleSheet(f"border-radius:8px; border:1px solid rgba(212,175,55,0.12); background:transparent; color:{text};")
        update_layout.addWidget(self.update_btn)
        update_layout.addStretch()
        right.addLayout(update_layout)

        split.addLayout(right, 1)
        layout.addLayout(split)

        help_label = QtWidgets.QLabel(tr('help_text'))
        help_label.setObjectName("help_text")
        help_label.setStyleSheet("color: #9b9b9b; font-size: 11px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        footer = QtWidgets.QHBoxLayout()
        self.signature = QtWidgets.QLabel("AstraKeys — by SMisha2")
        self.signature.setStyleSheet(f"color:{gold};")
        footer.addWidget(self.signature)
        footer.addStretch()
        self.version_label = QtWidgets.QLabel(f"v{CURRENT_VERSION} · {datetime.now().strftime('%d.%m.%Y')}")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.28); font-size:11px;")
        footer.addWidget(self.version_label)
        layout.addLayout(footer)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.central)

        self.about_btn.clicked.connect(self.show_about)
        self.add_btn.clicked.connect(self.add_song)
        self.save_btn.clicked.connect(self.save_playlist)
        self.load_btn.clicked.connect(self.load_playlist_dialog)
        self.import_btn.clicked.connect(self.import_playlist)
        self.export_btn.clicked.connect(self.export_playlist)
        self.start_btn.clicked.connect(self.toggle_play)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.playback_btn.clicked.connect(self.load_and_play)
        self.stop_playback_btn.clicked.connect(self.bot.stop_playback)
        self.pause_playback_btn.clicked.connect(self.bot.toggle_playback_pause)
        self.next_btn.clicked.connect(self.next_song)
        self.next_mode_btn.clicked.connect(self.next_mode)
        self.remove_btn.clicked.connect(self.remove_song)
        self.rename_btn.clicked.connect(self.rename_song)
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        self.min_slider.valueChanged.connect(self.min_delay_changed)
        self.max_slider.valueChanged.connect(self.max_delay_changed)
        self.start_slider.valueChanged.connect(self.start_delay_changed)
        self.update_btn.clicked.connect(self.gui_update_client)
        self.song_list.model().rowsMoved.connect(self.handle_rows_moved)

        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; background:transparent; color:{text}; }}
            QSlider::groove:horizontal {{ height:6px; background:rgba(255,255,255,0.03); border-radius:3px; }}
            QSlider::handle:horizontal {{ background:{soft_gold}; width:14px; border-radius:7px; }}
            QComboBox {{ padding:6px; border-radius:6px; background:{panel}; border:1px solid rgba(255,255,255,0.1); }}
            QPushButton:hover {{ border-color:{gold}; }}
        """)

    def change_language(self, idx):
        lang_codes = ['ru', 'en', 'uk']
        new_lang = lang_codes[idx]
        tr_obj.set_lang(new_lang)
        self.bot.save_app_settings()
        self.retranslate_ui()
        self.refresh_status()

    def retranslate_ui(self):
        self.setWindowTitle(tr('app_title'))
        self.about_btn.setToolTip(tr('about_title'))
        self.add_btn.setText(tr('add_song'))
        self.save_btn.setText(tr('save_playlist'))
        self.load_btn.setText(tr('load_playlist'))
        self.import_btn.setText(tr('playlist_import'))
        self.export_btn.setText(tr('playlist_export'))
        self.start_btn.setText(tr('start_btn'))
        self.record_btn.setText(tr('record_btn'))
        self.playback_btn.setText(tr('playback_btn'))
        self.stop_playback_btn.setText(tr('stop_playback_btn'))
        self.pause_playback_btn.setText(tr('playback_pause'))
        self.next_btn.setText(tr('next_song_btn'))
        self.next_mode_btn.setText(tr('next_mode_btn'))
        self.remove_btn.setText(tr('remove_btn'))
        self.rename_btn.setText(tr('rename_btn'))
        self.overlay_btn.setText(tr('overlay_btn'))
        self.recordings_btn.setText(tr('recordings_btn'))
        self.status_label.setText(tr('status') + " " + tr('status_idle'))
        self.mode_label.setText(tr('mode') + " " + self.mode_combo.currentText())
        self.update_btn.setText(tr('update_client'))
        delay_group = self.findChild(QtWidgets.QGroupBox, "delay_group")
        if delay_group:
            delay_group.setTitle(tr('delay_group'))
        self.mode_combo.clear()
        self.mode_combo.addItems([tr('mode1'), tr('mode2')])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        for child in self.findChildren(QtWidgets.QLabel):
            if child.text() in ('Мин. задержка (мс):', 'Min delay (ms):', 'Мін. затримка (мс):'):
                child.setText(tr('min_delay'))
            elif child.text() in ('Макс. задержка (мс):', 'Max delay (ms):', 'Макс. затримка (мс):'):
                child.setText(tr('max_delay'))
            elif child.text() in ('Задержка запуска (мс):', 'Start delay (ms):', 'Затримка запуску (мс):'):
                child.setText(tr('start_delay'))
        help_label = self.findChild(QtWidgets.QLabel, "help_text")
        if help_label:
            help_label.setText(tr('help_text'))

    def open_recordings_manager(self):
        dialog = RecordingsManagerDialog(self.bot, self)
        dialog.exec()

    def open_pedal_settings(self):
        dialog = PedalSettingsDialog(self.bot, self)
        dialog.exec()

    def show_log(self):
        dialog = LogViewerDialog(self)
        dialog.exec()

    def export_playlist(self):
        downloads_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.getcwd()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            tr('export_dialog_title'),
            os.path.join(downloads_dir, "playlist_export.json"),
            tr('export_filter')
        )
        if file_path:
            try:
                data = [{"name": n, "content": c} for n, c in self.bot.playlist]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                QtWidgets.QMessageBox.information(
                    self,
                    tr('playlist_exported').format(file=os.path.basename(file_path)),
                    tr('playlist_exported').format(file=os.path.basename(file_path)),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    tr('load_error'),
                    str(e),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )

    def import_playlist(self):
        downloads_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.getcwd()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            tr('import_dialog_title'),
            downloads_dir,
            tr('import_filter')
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                imported = [(d['name'], d['content']) for d in data]
                self.bot.playlist.extend(imported)
                self.refresh_list()
                QtWidgets.QMessageBox.information(
                    self,
                    tr('playlist_imported').format(file=os.path.basename(file_path)),
                    tr('playlist_imported').format(file=os.path.basename(file_path)),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    tr('load_error'),
                    str(e),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )

    def gui_update_client(self):
        self.update_btn.setEnabled(False)
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            logger.info("Starting update check")
            info, err = fetch_latest_release_info()
            if err or not info:
                self.show_message_box(tr('update_error'), f"{tr('update_error')}: {err or 'unknown'}")
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
                self.show_message_box(tr('update_error'), "Не удалось определить номер версии.")
                self.update_ui_after_update(False)
                return
            if version_tuple(latest_version) <= version_tuple(CURRENT_VERSION):
                self.show_message_box(tr('update_not_available'), tr('update_not_available'))
                self.update_ui_after_update(False)
                return
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self.show_message_box(tr('update_error'), "Новая версия найдена, но файл не найден в релизе.")
                self.update_ui_after_update(False)
                return
            tmp_name = "AstraKeys_update_tmp.exe"

            def prog_cb(pct):
                QtCore.QTimer.singleShot(0, lambda: self.update_progress.setValue(pct))

            logger.info(f"Downloading update from {asset_url}")
            ok, derr = download_asset_to_file(asset_url, tmp_name, progress_callback=prog_cb)
            if not ok:
                self.show_message_box(tr('update_error'), f"Ошибка скачивания: {derr}")
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
                self.show_message_box(tr('update_error'), f"Ошибка замены: {e}")
                self.update_ui_after_update(False)
                return
        except Exception as e:
            logger.error(f"Update process failed: {e}")
            self.show_message_box(tr('update_error'), f"Ошибка обновления: {e}")
        finally:
            QtCore.QTimer.singleShot(0, lambda: self.update_ui_after_update(False))

    def update_ui_after_update(self, busy=True):
        self.update_btn.setEnabled(True)
        self.update_progress.setVisible(False)
        self.update_progress.setValue(0)

    def show_message_box(self, title, text):
        def show():
            mb = QtWidgets.QMessageBox(self)
            mb.setWindowTitle(title)
            mb.setText(text)
            mb.exec()
        QtCore.QTimer.singleShot(0, show)

    def toggle_play(self):
        self.bot.playing = not self.bot.playing
        self.start_btn.setText(tr('start_btn') if not self.bot.playing else "Пауза (F1)")

    def toggle_recording(self):
        if self.bot.is_recording:
            name, ok = QtWidgets.QInputDialog.getText(self, tr('recording_name'), tr('enter_name'), text=self.bot.recording_song_name)
            if ok:
                self.bot.stop_recording(custom_name=name.strip() if name.strip() else None)
            else:
                self.bot.stop_recording()
        else:
            self.bot.start_recording()

    def load_and_play(self):
        manager = RecordingsManagerDialog(self.bot, self)
        if manager.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            row = manager.list_widget.currentRow()
            if row >= 0:
                idx = manager.list_widget.item(row).data(QtCore.Qt.ItemDataRole.UserRole)
                entry = self.bot.recordings_index[idx]
                json_path = os.path.join("recordings", entry['json_file'])
                if os.path.exists(json_path):
                    if self.bot.load_recording(json_path):
                        self.bot.start_playback()
                    else:
                        QtWidgets.QMessageBox.warning(
                            self,
                            tr('load_error'),
                            tr('load_failed'),
                            QtWidgets.QMessageBox.StandardButton.Ok
                        )
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        tr('load_error'),
                        tr('file_not_found'),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

    def toggle_overlay(self):
        if self.overlay_window.isVisible():
            self.overlay_window.hide()
        else:
            self.overlay_window.show()

    def next_song(self):
        self.bot.next_song()
        self.refresh_status()

    def next_mode(self):
        self.bot.mode = 2 if self.bot.mode == 1 else 1
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.refresh_status()

    def mode_changed(self, idx):
        self.bot.mode = idx + 1
        self.refresh_status()

    def min_delay_changed(self, val):
        self.bot.min_note_delay = val
        self.min_label.setText(str(val))
        if val > self.bot.max_note_delay:
            self.bot.max_note_delay = val
            self.max_slider.setValue(val)
            self.max_label.setText(str(val))

    def max_delay_changed(self, val):
        self.bot.max_note_delay = val
        self.max_label.setText(str(val))
        if val < self.bot.min_note_delay:
            self.bot.min_note_delay = val
            self.min_slider.setValue(val)
            self.min_label.setText(str(val))

    def start_delay_changed(self, val):
        self.bot.start_delay = val / 1000.0
        self.start_label.setText(f"{val}")

    def add_song(self):
        text = self.song_input.toPlainText().strip()
        if text:
            name, ok = QtWidgets.QInputDialog.getText(self, tr('song_name'), tr('enter_song_name'), text=f"Песня {len(self.bot.playlist)+1}")
            if not ok or not name.strip():
                name = f"Песня {len(self.bot.playlist)+1}"
            sanitized = self.bot.sanitize_song(text)
            self.bot.playlist.append((name, sanitized))
            self.song_list.addItem(name)
            self.song_input.clear()

    def remove_song(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            reply = QtWidgets.QMessageBox.question(
                self,
                tr('confirm_delete'),
                tr('delete_song').format(name=self.bot.playlist[row][0]),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.bot.playlist.pop(row)
                self.song_list.takeItem(row)
                if self.bot.song_index >= len(self.bot.playlist):
                    self.bot.song_index = max(0, len(self.bot.playlist)-1)
                if self.bot.playlist:
                    self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]

    def rename_song(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            name, content = self.bot.playlist[row]
            new_name, ok = QtWidgets.QInputDialog.getText(self, tr('rename_song'), tr('new_name'), text=name)
            if ok and new_name.strip():
                self.bot.playlist[row] = (new_name.strip(), content)
                if row == self.bot.song_index:
                    self.bot.song_name = new_name.strip()
                self.song_list.item(row).setText(new_name.strip())

    def save_playlist(self):
        try:
            data = [{"name": n, "content": c} for n, c in self.bot.playlist]
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(
                self,
                tr('playlist_saved').format(file=PLAYLIST_FILE),
                tr('playlist_saved').format(file=PLAYLIST_FILE),
                QtWidgets.QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                tr('load_error'),
                str(e),
                QtWidgets.QMessageBox.StandardButton.Ok
            )

    def load_playlist(self):
        try:
            if os.path.exists(PLAYLIST_FILE):
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.bot.playlist = [(d['name'], d['content']) for d in data]
                self.bot.song_index = 0
                if self.bot.playlist:
                    self.bot.song_name, self.bot.song = self.bot.playlist[0]
                self.refresh_list()
                logger.info("Playlist loaded")
        except Exception as e:
            logger.error(f"Load playlist error: {e}")

    def load_playlist_dialog(self):
        self.load_playlist()
        self.refresh_list()

    def refresh_list(self):
        self.song_list.clear()
        for name, _ in self.bot.playlist:
            self.song_list.addItem(name)
        self.song_list.setCurrentRow(self.bot.song_index)

    def handle_rows_moved(self, parent, start, end, dest, row):
        if start == end:
            return
        self.song_list.blockSignals(True)
        items = self.bot.playlist[start:end+1]
        del self.bot.playlist[start:end+1]
        insert_pos = row
        if row > end:
            insert_pos -= (end - start + 1)
        insert_pos = max(0, min(insert_pos, len(self.bot.playlist)))
        for i, item in enumerate(items):
            self.bot.playlist.insert(insert_pos + i, item)
        current_name = self.bot.song_name
        for i, (name, _) in enumerate(self.bot.playlist):
            if name == current_name:
                self.bot.song_index = i
                break
        self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
        self.refresh_list()
        self.song_list.blockSignals(False)

    def refresh_status(self):
        st = tr('status_playing') if self.bot.playing else tr('status_paused')
        if self.bot.is_playback:
            st = tr('status_playback')
            if self.bot.playback_paused:
                st += " (" + tr('playback_paused_status') + ")"
        self.status_label.setText(tr('status') + " " + st)
        self.mode_label.setText(tr('mode') + " " + self.mode_combo.currentText())
        try:
            self.pos_label.setText(tr('pos') + f" {self.bot.note_index}/{len(self.bot.song)}")
        except:
            self.pos_label.setText(tr('pos') + " 0/0")
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)
        self.update_song_display()
        if self.overlay_window and self.overlay_window.isVisible():
            self.overlay_window.update_metadata(self.bot.song_name, self.bot.progress, self.bot.playing, self.bot.is_playback)

        if self.bot.is_playback:
            self.playback_btn.setVisible(False)
            self.stop_playback_btn.setVisible(True)
            self.pause_playback_btn.setVisible(True)
            if self.bot.playback_paused:
                self.pause_playback_btn.setText(tr('playback_resume'))
            else:
                self.pause_playback_btn.setText(tr('playback_pause'))
        else:
            self.playback_btn.setVisible(True)
            self.stop_playback_btn.setVisible(False)
            self.pause_playback_btn.setVisible(False)

    def update_song_display(self):
        if not self.bot.song:
            self.song_display.setPlainText("")
            return
        chars_per_line = 45
        lines = 3
        total = chars_per_line * lines
        pos = self.bot.frozen_note_index if self.bot.freeze_note else self.bot.note_index
        if pos >= len(self.bot.song):
            start = max(0, len(self.bot.song) - total)
            display = self.bot.song[start:]
            self.song_display.setPlainText(display)
            return
        start = max(0, pos - total//3)
        display = self.bot.song[start:start+total]
        if len(display) < total and start + total > len(self.bot.song):
            start = max(0, len(self.bot.song) - total)
            display = self.bot.song[start:start+total]
        current_in_display = pos - start
        if 0 <= current_in_display < len(display):
            if current_in_display < len(display)-1 and display[current_in_display] == '[':
                end = display.find(']', current_in_display+1)
                if end != -1:
                    before = html.escape(display[:current_in_display])
                    chord = html.escape(display[current_in_display:end+1])
                    after = html.escape(display[end+1:])
                    html_text = f'<span style="color:#ccc;">{before}</span><span style="background-color:rgba(255,216,106,0.4); border-radius:3px; padding:0 2px; color:#ffd86a; font-weight:bold;">{chord}</span><span style="color:#ccc;">{after}</span>'
                    self.song_display.setHtml(html_text)
                    return
            before = html.escape(display[:current_in_display])
            current = html.escape(display[current_in_display:current_in_display+1])
            after = html.escape(display[current_in_display+1:])
            html_text = f'<span style="color:#ccc;">{before}</span><span style="background-color:rgba(255,216,106,0.5); border-radius:3px; padding:0 2px; color:#ffd86a; font-weight:bold;">{current}</span><span style="color:#ccc;">{after}</span>'
            self.song_display.setHtml(html_text)
        else:
            self.song_display.setPlainText(display)

    def on_state_changed(self):
        if self.bot.is_recording:
            self.record_btn.setText("⏹ Остановить (F12)")
            self.record_btn.setStyleSheet("border-radius:8px; border:1px solid #ff4444; background: rgba(255,68,68,0.1); color: #ff4444;")
        else:
            self.record_btn.setText(tr('record_btn'))
            self.record_btn.setStyleSheet("border-radius:8px; border:1px solid rgba(212,175,55,0.08); background: transparent; color: #f5f3f1;")
        self.refresh_status()

    def show_about(self):
        QtWidgets.QMessageBox.about(self, tr('about_title'), tr('about_text'))

    def check_internet(self):
        def worker():
            try:
                requests.get("https://api.github.com", timeout=3)
                logger.info("Internet available")
            except:
                logger.warning("No internet")
        threading.Thread(target=worker, daemon=True).start()

    def save_window_state(self):
        try:
            state = {"geometry": {"x": self.x(), "y": self.y(), "width": self.width(), "height": self.height()}, "maximized": self.isMaximized()}
            with open("window_state.json", "w") as f:
                json.dump(state, f)
        except:
            pass

    def load_window_state(self):
        try:
            if os.path.exists("window_state.json"):
                with open("window_state.json", "r") as f:
                    state = json.load(f)
                if not state.get("maximized", False):
                    g = state.get("geometry", {})
                    if all(k in g for k in ["x","y","width","height"]):
                        self.setGeometry(g["x"], g["y"], g["width"], g["height"])
        except:
            pass

    def closeEvent(self, event):
        self.bot.save_app_settings()
        self.bot.save_recordings_index()
        self.save_window_state()
        self.bot.stop_playback()
        self.bot.release_all()
        self.overlay_window.save_settings()
        self.overlay_window.close()
        event.accept()

if __name__ == "__main__":
    default_playlist = [
        ("random_starting, good_ending", r"[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe] 6 [QPS] C [Sc] [*Ti] Z [SO] [HO] i L [Wsl] Z [ESi] L [LP] [EZ] c P"),
        ("tags:atleast", r"l--l--l--l-lzlklzl"),
        ("GG", r"fffff[4qf]spsfspsg"),
        ("add_to_the_corner", r"d h f j [Ffd][xbgf][xd]")
    ]
    bot = RobloxPianoBot(default_playlist)
    threading.Thread(target=bot.play_song, daemon=True).start()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QtGui.QFont("Segoe UI", 9)
    app.setFont(font)
    gui = BotGUI(bot)
    gui.show()
    logger.info("Application started successfully")
    sys.exit(app.exec())
