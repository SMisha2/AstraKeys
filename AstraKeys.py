# -*- coding: utf-8 -*-
"""
AstraKeys v1.2.0 — smooth theme + hover animations + clearer icons
"""

import os
import sys
import time
import threading
import re
import random
import json
import logging
import zipfile
import html
from datetime import datetime

import requests
from PyQt6 import QtWidgets, QtCore, QtGui

try:
    from midiutil import MIDIFile
    HAS_MIDI = True
except ImportError:
    HAS_MIDI = False

try:
    import mido
    HAS_MIDI_OUT = True
except ImportError:
    mido = None
    HAS_MIDI_OUT = False

try:
    import win32gui, win32con
except Exception:
    win32gui = win32con = None

try:
    from pynput.keyboard import Controller, Key, Listener
except Exception:
    Controller = Key = Listener = None

try:
    import numpy as np
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    np = None
    sd = None
    HAS_AUDIO = False


# ═══════════════════════════════════════════════════════════════════
#                            CONSTANTS
# ═══════════════════════════════════════════════════════════════════

CURRENT_VERSION = "1.2.0"
GITHUB_OWNER = "SMisha2"
GITHUB_REPO = "AstraKeys"
ASSET_NAME = "AstraKeys.exe"
LOG_FILE = "astrakeys.log"
PLAYLIST_FILE = "playlist.json"
SETTINGS_FILE = "app_settings.json"
PEDAL_FILE = "pedal_settings.json"
RECORDINGS_INDEX = "recordings_index.json"
OVERLAY_FILE = "overlay_settings.json"
WINDOW_FILE = "window_state.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("AstraKeys")
logger.info(f"Starting AstraKeys v{CURRENT_VERSION}")


# ═══════════════════════════════════════════════════════════════════
#                            THEMES
# ═══════════════════════════════════════════════════════════════════

THEMES = {
    "gold": {
        "key": "gold", "name_key": "theme.gold", "is_dark": True,
        "bg": "#0a0a0a", "bg_alt": "#0f0f0f",
        "panel": "#151515", "panel_alt": "#1c1c1c", "input": "#181818",
        "text": "#f5f3f1", "text_muted": "#8a8a8a", "text_dim": "#5a5a5a",
        "accent": "#d4af37", "accent_hover": "#ffd86a", "accent_press": "#b8942a",
        "accent_text": "#0a0a0a", "accent_soft": "rgba(212,175,55,0.10)",
        "border": "#262626", "border_accent": "rgba(212,175,55,0.28)",
        "danger": "#e05a4d", "danger_hover": "#ff6a5d", "success": "#5cb85c",
        "selection": "rgba(212,175,55,0.22)",
        "scrollbar": "#2a2a2a", "scrollbar_hover": "#3a3a3a",
        "overlay_bg": "#0a0a0a", "overlay_text": "#ffd86a",
        "overlay_accent": "#d4af37", "overlay_highlight": "rgba(255,216,106,0.35)",
    },
    "sand": {
        "key": "sand", "name_key": "theme.sand", "is_dark": False,
        "bg": "#f5efe1", "bg_alt": "#ece4d0",
        "panel": "#ffffff", "panel_alt": "#faf6ec", "input": "#ffffff",
        "text": "#2b2418", "text_muted": "#7c7160", "text_dim": "#ab9f88",
        "accent": "#a67c00", "accent_hover": "#c99612", "accent_press": "#8a6508",
        "accent_text": "#ffffff", "accent_soft": "rgba(166,124,0,0.09)",
        "border": "#e6dcc3", "border_accent": "rgba(166,124,0,0.38)",
        "danger": "#c53030", "danger_hover": "#e53e3e", "success": "#2f855a",
        "selection": "rgba(166,124,0,0.16)",
        "scrollbar": "#d9cfb7", "scrollbar_hover": "#c4b89b",
        "overlay_bg": "#faf6ec", "overlay_text": "#8a6508",
        "overlay_accent": "#a67c00", "overlay_highlight": "rgba(166,124,0,0.20)",
    },
}

_current_theme_key = "gold"


def get_theme():
    return THEMES.get(_current_theme_key, THEMES["gold"])


# ─── color helpers for smooth theme transitions ───
def _parse_color(s):
    try:
        if not isinstance(s, str):
            return (255, 255, 255, 255)
        if s.startswith('#'):
            h = s[1:]
            if len(h) == 3:
                h = ''.join(c * 2 for c in h)
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        if s.startswith('rgba'):
            parts = s[5:-1].split(',')
            return (int(float(parts[0])), int(float(parts[1])),
                    int(float(parts[2])), int(float(parts[3]) * 255))
        if s.startswith('rgb'):
            parts = s[4:-1].split(',')
            return (int(float(parts[0])), int(float(parts[1])),
                    int(float(parts[2])), 255)
    except Exception:
        pass
    return (255, 255, 255, 255)


def _rgba_to_str(c):
    r, g, b, a = (max(0, min(255, int(x))) for x in c)
    if a >= 255:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{a / 255:.3f})"


def _lerp_rgba(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def build_qss(t):
    return f"""
    QWidget {{
        background: {t['bg']};
        color: {t['text']};
        font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
        font-size: 9pt;
    }}
    QToolTip {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border_accent']};
        padding: 4px 8px;
        border-radius: 4px;
    }}

    QPushButton {{
        background: {t['panel_alt']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 7px;
        padding: 6px 14px;
        min-height: 20px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {t['panel']};
        border-color: {t['border_accent']};
    }}
    QPushButton:pressed {{ background: {t['bg_alt']}; }}
    QPushButton:disabled {{
        color: {t['text_dim']};
        border-color: {t['border']};
        background: {t['bg_alt']};
    }}

    QPushButton[role="primary"] {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {t['accent_hover']}, stop:1 {t['accent']});
        color: {t['accent_text']};
        border: 1px solid {t['accent']};
        font-weight: 600;
        padding: 6px 16px;
    }}
    QPushButton[role="primary"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {t['accent_hover']}, stop:1 {t['accent_hover']});
        border-color: {t['accent_hover']};
    }}
    QPushButton[role="primary"]:pressed {{ background: {t['accent_press']}; }}

    QPushButton[role="danger"] {{
        background: {t['panel_alt']};
        color: {t['danger']};
        border: 1px solid {t['danger']};
    }}
    QPushButton[role="danger"]:hover {{
        background: {t['danger']};
        color: #ffffff;
    }}

    QPushButton[role="icon"] {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 7px;
        padding: 0 6px;
        font-size: 12pt;
    }}
    QPushButton[role="icon"]:hover {{
        background: {t['accent_soft']};
        border-color: {t['border_accent']};
    }}
    QPushButton[role="icon"]:checked {{
        background: {t['selection']};
        border-color: {t['accent']};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background: {t['input']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 7px;
        padding: 6px 9px;
        selection-background-color: {t['accent']};
        selection-color: {t['accent_text']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {t['accent']};
    }}
    QComboBox {{
        background: {t['input']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 7px;
        padding: 5px 10px;
        min-height: 22px;
    }}
    QComboBox:hover {{ border-color: {t['border_accent']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border_accent']};
        border-radius: 7px;
        selection-background-color: {t['selection']};
        selection-color: {t['text']};
        outline: none;
        padding: 4px;
    }}

    QCheckBox {{ color: {t['text']}; spacing: 8px; padding: 2px; }}
    QCheckBox::indicator {{
        width: 15px; height: 15px;
        border: 1.5px solid {t['border_accent']};
        border-radius: 4px;
        background: {t['input']};
    }}
    QCheckBox::indicator:hover {{ border-color: {t['accent']}; }}
    QCheckBox::indicator:checked {{
        background: {t['accent']};
        border-color: {t['accent']};
    }}

    QListWidget, QTreeWidget, QTableWidget {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        outline: none;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-radius: 5px;
        min-height: 18px;
    }}
    QListWidget::item:hover {{ background: {t['panel_alt']}; }}
    QListWidget::item:selected {{
        background: {t['selection']};
        color: {t['text']};
    }}

    QSlider::groove:horizontal {{
        height: 5px; background: {t['border']}; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {t['accent']};
        width: 14px; height: 14px;
        margin: -5px 0; border-radius: 7px;
        border: 2px solid {t['panel']};
    }}
    QSlider::handle:horizontal:hover {{ background: {t['accent_hover']}; }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {t['accent']}, stop:1 {t['accent_hover']});
        border-radius: 3px;
    }}

    QProgressBar {{
        background: {t['input']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        height: 9px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {t['accent']}, stop:1 {t['accent_hover']});
        border-radius: 4px;
    }}

    QTabWidget::pane {{
        border: 1px solid {t['border']};
        border-radius: 10px;
        top: -1px;
        background: {t['panel']};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {t['text_muted']};
        padding: 8px 18px;
        border: none;
        border-bottom: 2px solid transparent;
        margin-right: 2px;
        font-weight: 500;
    }}
    QTabBar::tab:hover {{ color: {t['text']}; }}
    QTabBar::tab:selected {{
        color: {t['accent']};
        border-bottom: 2px solid {t['accent']};
    }}

    QGroupBox {{
        border: 1px solid {t['border']};
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 12px;
        color: {t['text_muted']};
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {t['accent']};
    }}

    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scrollbar']}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t['scrollbar_hover']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QScrollBar:horizontal {{
        background: transparent; height: 10px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['scrollbar']}; border-radius: 5px; min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t['scrollbar_hover']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

    QFrame#titlebar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {t['bg_alt']}, stop:1 {t['bg']});
        border: none;
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#accent_line {{
        background: {t['accent']};
        max-height: 1px; min-height: 1px; border: none;
    }}
    QLabel#app_title {{
        font-size: 13pt; font-weight: 700; color: {t['accent']};
        background: transparent;
    }}
    QLabel#section_label {{
        color: {t['text_muted']};
        font-size: 8pt; font-weight: 700;
        letter-spacing: 2px;
        background: transparent;
    }}
    QLabel#status_normal {{
        color: {t['text_muted']}; font-size: 8pt; background: transparent;
    }}
    QLabel#status_accent {{
        color: {t['accent']}; font-size: 9pt; font-weight: 600;
        background: transparent;
    }}
    QLabel#status_pos {{
        color: {t['text_dim']}; font-size: 8pt;
        font-family: 'Consolas', 'Courier New', monospace;
        background: transparent;
    }}
    QTextEdit#song_display {{
        background: {t['input']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11pt;
    }}

    QDialog {{ background: {t['bg']}; }}
    QMessageBox {{ background: {t['panel']}; }}
    QMessageBox QLabel {{ color: {t['text']}; }}
    QMenu {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border_accent']};
        border-radius: 7px;
        padding: 5px;
    }}
    QMenu::item {{ padding: 6px 22px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t['selection']}; }}
    QMenu::separator {{
        height: 1px; background: {t['border']}; margin: 4px 8px;
    }}
    """


def apply_theme(app):
    if app is None:
        return
    app.setStyleSheet(build_qss(get_theme()))


# ═══════════════════════════════════════════════════════════════════
#                         TRANSLATIONS
# ═══════════════════════════════════════════════════════════════════

LANGUAGES = {
    'ru': {
        'app.title': 'AstraKeys',
        'app.about_title': 'О программе',
        'app.about_text': (
            'AstraKeys v{version}\n'
            'Автор: SMisha2\n\n'
            'Программа для игры на пианино в Roblox.\n\n'
            'Возможности:\n'
            '• Воспроизведение плейлистов\n'
            '• Запись и воспроизведение нажатий\n'
            '• Экспорт в MIDI\n'
            '• MIDI-выход для FreePiano\n'
            '• Локальный звук через динамики\n'
            '• Редактор обрезки и склейки записей\n'
            '• Полная локализация (RU / EN / UK)\n'
            '• Светлая и тёмная темы'
        ),
        'ui.ok': 'OK', 'ui.cancel': 'Отмена', 'ui.close': 'Закрыть',
        'ui.yes': 'Да', 'ui.no': 'Нет', 'ui.add': 'Добавить',
        'ui.remove': 'Удалить', 'ui.save': 'Сохранить', 'ui.load': 'Загрузить',
        'ui.import': 'Импорт', 'ui.export': 'Экспорт', 'ui.reset': 'Сбросить',
        'ui.refresh': 'Обновить', 'ui.error': 'Ошибка',
        'ui.warning': 'Предупреждение', 'ui.info': 'Информация',
        'ui.done': 'Готово', 'ui.confirm': 'Подтверждение',

        'theme.gold': 'Золото', 'theme.sand': 'Песок',

        'titlebar.about_tooltip': 'О программе',
        'titlebar.theme_tooltip': 'Сменить тему (плавный переход)',
        'titlebar.log_tooltip': 'Показать лог',
        'titlebar.lang_tooltip': 'Язык интерфейса',

        'playlist.section': 'ПЛЕЙЛИСТ',
        'playlist.add_tooltip': 'Добавить песню',
        'playlist.remove_tooltip': 'Удалить песню',
        'playlist.rename_tooltip': 'Переименовать',
        'playlist.save_tooltip': 'Сохранить плейлист',
        'playlist.load_tooltip': 'Загрузить плейлист',
        'playlist.manage_recordings': 'Записи',
        'playlist.overlay': 'Ноты',

        'player.section': 'ПРОИГРЫВАТЕЛЬ',
        'player.input_placeholder': 'Вставьте текст песни сюда...',
        'player.start_tooltip': 'Начать воспроизведение (F1)',
        'player.pause_tooltip': 'Приостановить (F1)',
        'player.record_tooltip': 'Начать/остановить запись (F12)',
        'player.playback_tooltip': 'Открыть список записей',
        'player.stop_playback_tooltip': 'Остановить воспроизведение (F9)',
        'player.next_song_tooltip': 'Следующая песня (F8)',
        'player.next_mode_tooltip': 'Сменить режим (F7)',
        'player.btn_play': 'Играть',
        'player.btn_pause': 'Пауза',
        'player.btn_record': 'Запись',
        'player.btn_stop_rec': 'Стоп',
        'player.btn_playback': 'Записи',
        'player.btn_stop_playback': 'Стоп',
        'player.btn_pause_playback': 'Пауза',
        'player.btn_resume_playback': 'Продолжить',

        'settings.tab_params': 'Параметры',
        'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Режим',
        'settings.mode1': 'Без задержек',
        'settings.mode2': 'С задержками',
        'settings.min_delay': 'Мин. задержка, мс',
        'settings.max_delay': 'Макс. задержка, мс',
        'settings.start_delay': 'Задержка запуска, мс',
        'settings.speaker_enable': 'Звук нот в динамиках',
        'settings.auto_update': 'Проверять обновления при запуске',
        'settings.update_btn': 'Проверить обновления',
        'settings.pedal_btn': 'Педали',

        'audio.auto_play': 'Играть без педали',
        'audio.auto_hold': 'Авто-удержание, мс',
        'audio.warn_title': 'Звук недоступен',
        'audio.warn_text': 'Установите библиотеки:\npip install sounddevice numpy',

        'midi.enable': 'Отправлять ноты через MIDI',
        'midi.port': 'Порт',
        'midi.test': 'Тест (C-мажор)',
        'midi.no_ports': '(нет MIDI-портов)',
        'midi.hint': 'Установите loopMIDI и выберите порт',
        'midi.no_lib': 'mido не установлен: pip install mido python-rtmidi',
        'midi.connected': 'Подключено: {name}',
        'midi.error': 'Ошибка MIDI',
        'midi.select_port': 'Сначала выберите MIDI-порт',
        'midi.refresh_tooltip': 'Обновить список портов',

        'status.idle': 'Готов',
        'status.playing': 'Играет',
        'status.paused': 'Пауза',
        'status.recording': 'Запись',
        'status.playback': 'Воспроизведение',
        'status.preview': 'Превью',

        'help.text': (
            'F1 пуск/пауза · F2 рестарт · F3/F4 ±25 нот · F5 пауза воспр. · '
            'F6 заморозка · F7 режим · F8 песня · F9 стоп · F10 последняя запись · F12 запись'
        ),

        'overlay.pin_tooltip': 'Закрепить поверх окон',
        'overlay.opacity_tooltip': 'Прозрачность',
        'overlay.close_tooltip': 'Скрыть',
        'overlay.font_size': 'Размер шрифта',
        'overlay.lines': 'Строк',
        'overlay.reset': 'Сбросить',
        'overlay.opacity_1pct': '1%',

        'pedal.title': 'Настройка педалей',
        'pedal.placeholder': 'Символ',
        'pedal.add': 'Добавить',
        'pedal.remove': 'Удалить выбранное',
        'pedal.reset': 'Сброс к стандартным',

        'recordings.title': 'Записи',
        'recordings.search': 'Поиск...',
        'recordings.sort_new': 'Сначала новые',
        'recordings.sort_old': 'Сначала старые',
        'recordings.sort_az': 'По имени А-Я',
        'recordings.sort_za': 'По имени Я-А',
        'recordings.sort_dur': 'По длительности',
        'recordings.sort_fav': 'Избранные',
        'recordings.preview': 'Прослушать',
        'recordings.favorite': 'Избранное',
        'recordings.rename': 'Переименовать',
        'recordings.editor': 'Редактор',
        'recordings.delete': 'Удалить',
        'recordings.export_zip': 'Экспорт ZIP',
        'recordings.import_zip': 'Импорт ZIP',
        'recordings.open_folder': 'Папка',
        'recordings.clean': 'Очистить не избранные',
        'recordings.confirm_delete': 'Удалить «{name}»?',
        'recordings.confirm_clean': 'Удалить {n} не избранных записей?',
        'recordings.import_ok': 'Добавлено записей: {n}',

        'editor.title': 'Редактор записей',
        'editor.trim': 'Обрезка',
        'editor.concat': 'Склейка',
        'editor.select': 'Выберите запись:',
        'editor.duration': 'Длительность',
        'editor.start': 'Начало, с',
        'editor.end': 'Конец, с',
        'editor.preview': 'Прослушать',
        'editor.save_new': 'Сохранить как новую',
        'editor.first': 'Первая запись:',
        'editor.second': 'Вторая (приклеивается в конец):',
        'editor.gap': 'Пауза, с',
        'editor.concat_btn': 'Склеить и сохранить',

        'log.title': 'Лог-файл',
        'log.copy': 'Копировать',
        'log.close': 'Закрыть',

        'update.error': 'Ошибка обновления',
        'update.latest': 'Установлена последняя версия',
        'update.asset_missing': 'Файл обновления не найден в релизе',
        'update.version_unknown': 'Не удалось определить версию',

        'songs.name_title': 'Название песни',
        'songs.name_label': 'Введите название:',
        'songs.new_name': 'Новое название:',
        'songs.delete_title': 'Подтверждение удаления',
        'songs.delete_text': 'Удалить «{name}»?',
        'songs.default_name': 'Песня {n}',

        'recording.name_title': 'Название записи',
        'recording.name_label': 'Введите название для записи:',
        'recording.empty': 'Не записано ни одной ноты',

        'file.json': 'JSON-файлы (*.json)',
        'file.zip': 'ZIP-архивы (*.zip)',
    },
    'en': {
        'app.title': 'AstraKeys',
        'app.about_title': 'About',
        'app.about_text': (
            'AstraKeys v{version}\n'
            'Author: SMisha2\n\n'
            'Piano-playing helper for Roblox.\n\n'
            'Features:\n'
            '• Playlist playback\n'
            '• Recording and playback of keystrokes\n'
            '• MIDI file export\n'
            '• MIDI output for FreePiano\n'
            '• Local speaker audio\n'
            '• Trim & concat editor\n'
            '• Full localization (RU / EN / UK)\n'
            '• Light and dark themes'
        ),
        'ui.ok': 'OK', 'ui.cancel': 'Cancel', 'ui.close': 'Close',
        'ui.yes': 'Yes', 'ui.no': 'No', 'ui.add': 'Add',
        'ui.remove': 'Remove', 'ui.save': 'Save', 'ui.load': 'Load',
        'ui.import': 'Import', 'ui.export': 'Export', 'ui.reset': 'Reset',
        'ui.refresh': 'Refresh', 'ui.error': 'Error',
        'ui.warning': 'Warning', 'ui.info': 'Info',
        'ui.done': 'Done', 'ui.confirm': 'Confirm',

        'theme.gold': 'Gold', 'theme.sand': 'Sand',

        'titlebar.about_tooltip': 'About',
        'titlebar.theme_tooltip': 'Switch theme (smooth)',
        'titlebar.log_tooltip': 'Show log',
        'titlebar.lang_tooltip': 'Interface language',

        'playlist.section': 'PLAYLIST',
        'playlist.add_tooltip': 'Add song',
        'playlist.remove_tooltip': 'Remove song',
        'playlist.rename_tooltip': 'Rename',
        'playlist.save_tooltip': 'Save playlist',
        'playlist.load_tooltip': 'Load playlist',
        'playlist.manage_recordings': 'Recordings',
        'playlist.overlay': 'Notes',

        'player.section': 'PLAYER',
        'player.input_placeholder': 'Paste song text here...',
        'player.start_tooltip': 'Start playback (F1)',
        'player.pause_tooltip': 'Pause (F1)',
        'player.record_tooltip': 'Start/stop recording (F12)',
        'player.playback_tooltip': 'Open recordings list',
        'player.stop_playback_tooltip': 'Stop playback (F9)',
        'player.next_song_tooltip': 'Next song (F8)',
        'player.next_mode_tooltip': 'Switch mode (F7)',
        'player.btn_play': 'Play',
        'player.btn_pause': 'Pause',
        'player.btn_record': 'Record',
        'player.btn_stop_rec': 'Stop',
        'player.btn_playback': 'Records',
        'player.btn_stop_playback': 'Stop',
        'player.btn_pause_playback': 'Pause',
        'player.btn_resume_playback': 'Resume',

        'settings.tab_params': 'Settings',
        'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Mode',
        'settings.mode1': 'No delays',
        'settings.mode2': 'With delays',
        'settings.min_delay': 'Min delay, ms',
        'settings.max_delay': 'Max delay, ms',
        'settings.start_delay': 'Start delay, ms',
        'settings.speaker_enable': 'Note sound in speakers',
        'settings.auto_update': 'Check for updates on startup',
        'settings.update_btn': 'Check for updates',
        'settings.pedal_btn': 'Pedals',

        'audio.auto_play': 'Play without pedal',
        'audio.auto_hold': 'Auto-hold, ms',
        'audio.warn_title': 'Audio unavailable',
        'audio.warn_text': 'Install libraries:\npip install sounddevice numpy',

        'midi.enable': 'Send notes via MIDI',
        'midi.port': 'Port',
        'midi.test': 'Test (C-major)',
        'midi.no_ports': '(no MIDI ports)',
        'midi.hint': 'Install loopMIDI and select a port',
        'midi.no_lib': 'mido not installed: pip install mido python-rtmidi',
        'midi.connected': 'Connected: {name}',
        'midi.error': 'MIDI error',
        'midi.select_port': 'Select a MIDI port first',
        'midi.refresh_tooltip': 'Refresh port list',

        'status.idle': 'Ready',
        'status.playing': 'Playing',
        'status.paused': 'Paused',
        'status.recording': 'Recording',
        'status.playback': 'Playback',
        'status.preview': 'Preview',

        'help.text': (
            'F1 play/pause · F2 restart · F3/F4 ±25 notes · F5 pause playback · '
            'F6 freeze · F7 mode · F8 song · F9 stop · F10 latest recording · F12 record'
        ),

        'overlay.pin_tooltip': 'Pin on top',
        'overlay.opacity_tooltip': 'Opacity',
        'overlay.close_tooltip': 'Hide',
        'overlay.font_size': 'Font size',
        'overlay.lines': 'Lines',
        'overlay.reset': 'Reset',
        'overlay.opacity_1pct': '1%',

        'pedal.title': 'Pedal settings',
        'pedal.placeholder': 'Char',
        'pedal.add': 'Add',
        'pedal.remove': 'Remove selected',
        'pedal.reset': 'Reset to default',

        'recordings.title': 'Recordings',
        'recordings.search': 'Search...',
        'recordings.sort_new': 'Newest first',
        'recordings.sort_old': 'Oldest first',
        'recordings.sort_az': 'Name A-Z',
        'recordings.sort_za': 'Name Z-A',
        'recordings.sort_dur': 'By duration',
        'recordings.sort_fav': 'Favorites',
        'recordings.preview': 'Preview',
        'recordings.favorite': 'Favorite',
        'recordings.rename': 'Rename',
        'recordings.editor': 'Editor',
        'recordings.delete': 'Delete',
        'recordings.export_zip': 'Export ZIP',
        'recordings.import_zip': 'Import ZIP',
        'recordings.open_folder': 'Folder',
        'recordings.clean': 'Clean non-favorites',
        'recordings.confirm_delete': 'Delete "{name}"?',
        'recordings.confirm_clean': 'Delete {n} non-favorite recordings?',
        'recordings.import_ok': 'Added recordings: {n}',

        'editor.title': 'Recording editor',
        'editor.trim': 'Trim',
        'editor.concat': 'Concat',
        'editor.select': 'Select recording:',
        'editor.duration': 'Duration',
        'editor.start': 'Start, s',
        'editor.end': 'End, s',
        'editor.preview': 'Preview',
        'editor.save_new': 'Save as new',
        'editor.first': 'First recording:',
        'editor.second': 'Second (appended):',
        'editor.gap': 'Gap, s',
        'editor.concat_btn': 'Concat and save',

        'log.title': 'Log file',
        'log.copy': 'Copy',
        'log.close': 'Close',

        'update.error': 'Update error',
        'update.latest': 'Latest version installed',
        'update.asset_missing': 'Update asset not found in release',
        'update.version_unknown': 'Could not determine version',

        'songs.name_title': 'Song name',
        'songs.name_label': 'Enter name:',
        'songs.new_name': 'New name:',
        'songs.delete_title': 'Confirm deletion',
        'songs.delete_text': 'Delete "{name}"?',
        'songs.default_name': 'Song {n}',

        'recording.name_title': 'Recording name',
        'recording.name_label': 'Enter recording name:',
        'recording.empty': 'No notes recorded',

        'file.json': 'JSON files (*.json)',
        'file.zip': 'ZIP archives (*.zip)',
    },
    'uk': {
        'app.title': 'AstraKeys',
        'app.about_title': 'Про програму',
        'app.about_text': (
            'AstraKeys v{version}\n'
            'Автор: SMisha2\n\n'
            'Програма для гри на піаніно в Roblox.\n\n'
            'Можливості:\n'
            '• Відтворення плейлистів\n'
            '• Запис і відтворення натискань\n'
            '• Експорт у MIDI\n'
            '• MIDI-вихід для FreePiano\n'
            '• Локальний звук через динаміки\n'
            '• Редактор обрізки та склейки записів\n'
            '• Повна локалізація (RU / EN / UK)\n'
            '• Світла та темна теми'
        ),
        'ui.ok': 'OK', 'ui.cancel': 'Скасувати', 'ui.close': 'Закрити',
        'ui.yes': 'Так', 'ui.no': 'Ні', 'ui.add': 'Додати',
        'ui.remove': 'Видалити', 'ui.save': 'Зберегти', 'ui.load': 'Завантажити',
        'ui.import': 'Імпорт', 'ui.export': 'Експорт', 'ui.reset': 'Скинути',
        'ui.refresh': 'Оновити', 'ui.error': 'Помилка',
        'ui.warning': 'Попередження', 'ui.info': 'Інформація',
        'ui.done': 'Готово', 'ui.confirm': 'Підтвердження',

        'theme.gold': 'Золото', 'theme.sand': 'Пісок',

        'titlebar.about_tooltip': 'Про програму',
        'titlebar.theme_tooltip': 'Змінити тему (плавно)',
        'titlebar.log_tooltip': 'Показати лог',
        'titlebar.lang_tooltip': 'Мова інтерфейсу',

        'playlist.section': 'ПЛЕЙЛИСТ',
        'playlist.add_tooltip': 'Додати пісню',
        'playlist.remove_tooltip': 'Видалити пісню',
        'playlist.rename_tooltip': 'Перейменувати',
        'playlist.save_tooltip': 'Зберегти плейлист',
        'playlist.load_tooltip': 'Завантажити плейлист',
        'playlist.manage_recordings': 'Записи',
        'playlist.overlay': 'Ноти',

        'player.section': 'ПРОГРАВАЧ',
        'player.input_placeholder': 'Вставте текст пісні сюди...',
        'player.start_tooltip': 'Почати відтворення (F1)',
        'player.pause_tooltip': 'Призупинити (F1)',
        'player.record_tooltip': 'Почати/зупинити запис (F12)',
        'player.playback_tooltip': 'Відкрити список записів',
        'player.stop_playback_tooltip': 'Зупинити відтворення (F9)',
        'player.next_song_tooltip': 'Наступна пісня (F8)',
        'player.next_mode_tooltip': 'Змінити режим (F7)',
        'player.btn_play': 'Грати',
        'player.btn_pause': 'Пауза',
        'player.btn_record': 'Запис',
        'player.btn_stop_rec': 'Стоп',
        'player.btn_playback': 'Записи',
        'player.btn_stop_playback': 'Стоп',
        'player.btn_pause_playback': 'Пауза',
        'player.btn_resume_playback': 'Продовжити',

        'settings.tab_params': 'Параметри',
        'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Режим',
        'settings.mode1': 'Без затримок',
        'settings.mode2': 'Із затримками',
        'settings.min_delay': 'Мін. затримка, мс',
        'settings.max_delay': 'Макс. затримка, мс',
        'settings.start_delay': 'Затримка запуску, мс',
        'settings.speaker_enable': 'Звук нот у динаміках',
        'settings.auto_update': 'Перевіряти оновлення при запуску',
        'settings.update_btn': 'Перевірити оновлення',
        'settings.pedal_btn': 'Педалі',

        'audio.auto_play': 'Грати без педалі',
        'audio.auto_hold': 'Авто-утримання, мс',
        'audio.warn_title': 'Звук недоступний',
        'audio.warn_text': 'Встановіть бібліотеки:\npip install sounddevice numpy',

        'midi.enable': 'Надсилати ноти через MIDI',
        'midi.port': 'Порт',
        'midi.test': 'Тест (C-мажор)',
        'midi.no_ports': '(немає MIDI-портів)',
        'midi.hint': 'Встановіть loopMIDI та виберіть порт',
        'midi.no_lib': 'mido не встановлено: pip install mido python-rtmidi',
        'midi.connected': 'Підключено: {name}',
        'midi.error': 'Помилка MIDI',
        'midi.select_port': 'Спочатку виберіть MIDI-порт',
        'midi.refresh_tooltip': 'Оновити список портів',

        'status.idle': 'Готовий',
        'status.playing': 'Грає',
        'status.paused': 'Пауза',
        'status.recording': 'Запис',
        'status.playback': 'Відтворення',
        'status.preview': 'Прев\'ю',

        'help.text': (
            'F1 пуск/пауза · F2 рестарт · F3/F4 ±25 нот · F5 пауза відтворення · '
            'F6 заморозка · F7 режим · F8 пісня · F9 стоп · F10 останній запис · F12 запис'
        ),

        'overlay.pin_tooltip': 'Закріпити поверх вікон',
        'overlay.opacity_tooltip': 'Прозорість',
        'overlay.close_tooltip': 'Сховати',
        'overlay.font_size': 'Розмір шрифту',
        'overlay.lines': 'Рядків',
        'overlay.reset': 'Скинути',
        'overlay.opacity_1pct': '1%',

        'pedal.title': 'Налаштування педалей',
        'pedal.placeholder': 'Символ',
        'pedal.add': 'Додати',
        'pedal.remove': 'Видалити вибране',
        'pedal.reset': 'Скинути до стандартних',

        'recordings.title': 'Записи',
        'recordings.search': 'Пошук...',
        'recordings.sort_new': 'Спочатку нові',
        'recordings.sort_old': 'Спочатку старі',
        'recordings.sort_az': 'За іменем А-Я',
        'recordings.sort_za': 'За іменем Я-А',
        'recordings.sort_dur': 'За тривалістю',
        'recordings.sort_fav': 'Обрані',
        'recordings.preview': 'Прослухати',
        'recordings.favorite': 'Обране',
        'recordings.rename': 'Перейменувати',
        'recordings.editor': 'Редактор',
        'recordings.delete': 'Видалити',
        'recordings.export_zip': 'Експорт ZIP',
        'recordings.import_zip': 'Імпорт ZIP',
        'recordings.open_folder': 'Папка',
        'recordings.clean': 'Очистити не обрані',
        'recordings.confirm_delete': 'Видалити «{name}»?',
        'recordings.confirm_clean': 'Видалити {n} не обраних записів?',
        'recordings.import_ok': 'Додано записів: {n}',

        'editor.title': 'Редактор записів',
        'editor.trim': 'Обрізка',
        'editor.concat': 'Склейка',
        'editor.select': 'Виберіть запис:',
        'editor.duration': 'Тривалість',
        'editor.start': 'Початок, с',
        'editor.end': 'Кінець, с',
        'editor.preview': 'Прослухати',
        'editor.save_new': 'Зберегти як новий',
        'editor.first': 'Перший запис:',
        'editor.second': 'Другий (приклеюється в кінець):',
        'editor.gap': 'Пауза, с',
        'editor.concat_btn': 'Склеїти та зберегти',

        'log.title': 'Лог-файл',
        'log.copy': 'Копіювати',
        'log.close': 'Закрити',

        'update.error': 'Помилка оновлення',
        'update.latest': 'Встановлено останню версію',
        'update.asset_missing': 'Файл оновлення не знайдено у релізі',
        'update.version_unknown': 'Не вдалося визначити версію',

        'songs.name_title': 'Назва пісні',
        'songs.name_label': 'Введіть назву:',
        'songs.new_name': 'Нова назва:',
        'songs.delete_title': 'Підтвердження видалення',
        'songs.delete_text': 'Видалити «{name}»?',
        'songs.default_name': 'Пісня {n}',

        'recording.name_title': 'Назва запису',
        'recording.name_label': 'Введіть назву для запису:',
        'recording.empty': 'Не записано жодної ноти',

        'file.json': 'JSON-файли (*.json)',
        'file.zip': 'ZIP-архіви (*.zip)',
    },
}

SUPPORTED_LANGS = ['ru', 'en', 'uk']
LANG_LABELS = {'ru': 'Русский', 'en': 'English', 'uk': 'Українська'}


class Translator:
    def __init__(self):
        self.lang = 'ru'
        self.load()

    def load(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.lang = json.load(f).get('lang', 'ru')
        except Exception:
            pass
        if self.lang not in SUPPORTED_LANGS:
            self.lang = 'ru'

    def save(self):
        try:
            s = {}
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        s = json.load(f)
                except Exception:
                    s = {}
            s['lang'] = self.lang
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"save lang: {e}")

    def set_lang(self, lang):
        if lang in SUPPORTED_LANGS:
            self.lang = lang
            self.save()

    def tr(self, key):
        d = LANGUAGES.get(self.lang, LANGUAGES['ru'])
        return d.get(key, LANGUAGES['ru'].get(key, key))


tr_obj = Translator()


def tr(key, **kw):
    s = tr_obj.tr(key)
    if kw:
        try:
            return s.format(**kw)
        except Exception:
            return s
    return s


# ═══════════════════════════════════════════════════════════════════
#                            HELPERS
# ═══════════════════════════════════════════════════════════════════

DEFAULT_PEDAL_KEYS = {"-", "=", "[", "]"}
ROBLOX_KEYS = (
    "1234567890"
    "qwertyuiopasdfghjklzxcvbnm"
    "QWERTYUIOPASDFGHJKLZXCVBNM"
    "!@#$%^*()"
    "_-+{}:;\"'<>,.?/|\\~"
)
KEY_TO_MIDI = {
    '1': 36, '2': 38, '3': 40, '4': 41, '5': 43, '6': 45, '7': 47,
    '8': 48, '9': 50, '0': 52,
    'q': 53, 'w': 55, 'e': 57, 'r': 59, 't': 60, 'y': 62, 'u': 64,
    'i': 65, 'o': 67, 'p': 69,
    'a': 71, 's': 72, 'd': 74, 'f': 76, 'g': 77, 'h': 79, 'j': 81,
    'k': 83, 'l': 84,
    'z': 86, 'x': 88, 'c': 89, 'v': 91, 'b': 93, 'n': 95, 'm': 96,
}
SHARP_ALIASES = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6',
    '&': '7', '*': '8', '(': '9', ')': '0',
}
SHIFT_SYMBOL_MAP = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6',
    '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', ':': ';', '"': "'",
    '<': ',', '>': '.', '?': '/', '|': '\\', '~': '`',
}


def get_keyboard_parts(key):
    if not key or not isinstance(key, str) or len(key) != 1:
        return None, False
    if key.isupper() and key.isalpha():
        return key.lower(), True
    if key in SHIFT_SYMBOL_MAP:
        return SHIFT_SYMBOL_MAP[key], True
    if key.isalpha():
        return key.lower(), False
    return key, False


def key_to_midi(key):
    if not key or not isinstance(key, str) or len(key) != 1:
        return None
    sharp = False
    if key in SHARP_ALIASES:
        key = SHARP_ALIASES[key]
        sharp = True
    elif key.isupper():
        key = key.lower()
        sharp = True
    base = KEY_TO_MIDI.get(key)
    if base is None:
        return None
    return base + (1 if sharp else 0)


def is_valid_key(key):
    return bool(key and isinstance(key, str) and len(key) == 1 and key in ROBLOX_KEYS)


def find_roblox_window():
    if not win32gui:
        return None
    try:
        found = None

        def cb(hwnd, _):
            nonlocal found
            try:
                if (win32gui.IsWindowVisible(hwnd)
                        and "Roblox" in win32gui.GetWindowText(hwnd)
                        and found is None):
                    found = hwnd
            except Exception:
                pass

        win32gui.EnumWindows(cb, None)
        return found
    except Exception:
        return None


def activate_roblox_window():
    hwnd = find_roblox_window()
    if hwnd:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            pass
    return False


def fetch_latest_release_info():
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    try:
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def download_asset_to_file(url, dest, progress_callback=None, chunk_size=65536, max_retries=3):
    for attempt in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = r.headers.get("content-length")
                total = int(total) if total else None
                written = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size):
                        if chunk:
                            f.write(chunk)
                            written += len(chunk)
                            if progress_callback and total:
                                progress_callback(int(written * 100 // total))
                if total is None or os.path.getsize(dest) == total:
                    if progress_callback:
                        progress_callback(100)
                    return True, None
                if attempt < max_retries - 1:
                    time.sleep(1)
                    try:
                        os.remove(dest)
                    except Exception:
                        pass
                    continue
                return False, "Size mismatch"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                try:
                    if os.path.exists(dest):
                        os.remove(dest)
                except Exception:
                    pass
            else:
                return False, str(e)
    return False, "Retries exceeded"


def perform_replacement_and_restart(new_file, target_name, is_frozen):
    try:
        if is_frozen or sys.argv[0].lower().endswith(".exe"):
            current = os.path.basename(sys.argv[0])
            backup = current + ".bak"
            bat = f"""@echo off
setlocal
:kill
taskkill /f /im "{current}" >nul 2>&1
timeout /t 1 >nul
tasklist /fi "IMAGENAME eq {current}" 2>nul | findstr /i "{current}" >nul && goto kill
timeout /t 1 >nul
if exist "{backup}" del /f /q "{backup}" >nul 2>&1
if exist "{current}" move /y "{current}" "{backup}" >nul 2>&1
if exist "{new_file}" move /y "{new_file}" "{target_name}" >nul 2>&1
if exist "{target_name}" (
    start "" "{target_name}"
    del /f /q "{backup}" >nul 2>&1
) else (
    if exist "{backup}" (
        move /y "{backup}" "{current}" >nul 2>&1
        start "" "{current}"
    )
)
del /f /q "%~f0" >nul 2>&1 & exit
"""
            with open("update.bat", "w", encoding="utf-8") as f:
                f.write(bat)
            try:
                os.startfile("update.bat")
            except Exception:
                os.system("start update.bat")
            sys.exit(0)
        else:
            target = os.path.abspath(sys.argv[0])
            backup = target + ".bak"
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(target, backup)
                os.replace(new_file, target)
            except Exception as e:
                logger.error(f"replace error: {e}")
                raise
            os.execv(sys.executable, [sys.executable, target])
    except Exception as e:
        logger.error(f"Replacement error: {e}")
        raise


def version_tuple(v):
    try:
        return tuple(map(int, v.split(".")))
    except Exception:
        return (0, 0, 0)


# ═══════════════════════════════════════════════════════════════════
#                         ANIMATED BUTTONS
# ═══════════════════════════════════════════════════════════════════

class HoverButton(QtWidgets.QPushButton):
    """QPushButton with a subtle opacity fade on hover (≈60 FPS)."""

    _HOVER_OPACITY = 0.82
    _DURATION = 140

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._hover_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._hover_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._hover_effect)
        self._hover_anim = QtCore.QPropertyAnimation(self._hover_effect, b"opacity")
        self._hover_anim.setDuration(self._DURATION)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    def _animate_opacity(self, target):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_effect.opacity())
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, event):
        self._animate_opacity(self._HOVER_OPACITY)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_opacity(1.0)
        super().leaveEvent(event)


# ═══════════════════════════════════════════════════════════════════
#                         AUDIO PLAYER
# ═══════════════════════════════════════════════════════════════════

class AudioNotePlayer:
    SAMPLE_RATE = 44100
    BLOCK_SIZE = 256
    MAX_VOICES = 32

    def __init__(self, volume=0.7):
        self.ok = HAS_AUDIO
        self.sample_rate = self.SAMPLE_RATE
        self.volume = max(0.0, min(1.0, volume))
        self._voices_lock = threading.Lock()
        self._voices = {}
        self._frame = 0
        self._stream = None
        self._stream_lock = threading.Lock()

    def _ensure_stream(self):
        if not self.ok:
            return False
        if self._stream is not None:
            return True
        with self._stream_lock:
            if self._stream is not None:
                return True
            try:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate, channels=2, dtype="float32",
                    blocksize=self.BLOCK_SIZE, callback=self._callback,
                )
                self._stream.start()
                logger.info("Audio stream started")
                return True
            except Exception as e:
                logger.error(f"Audio stream init failed: {e}")
                self.ok = False
                return False

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, float(volume)))

    def note_on(self, note, velocity=100):
        if not self.ok or note is None:
            return
        try:
            note = int(note)
        except Exception:
            return
        if not self._ensure_stream():
            return
        freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
        vel = max(0.0, min(127.0, float(velocity))) / 127.0
        with self._voices_lock:
            if len(self._voices) >= self.MAX_VOICES and note not in self._voices:
                oldest = min(self._voices.items(), key=lambda kv: kv[1]["start_frame"])[0]
                self._voices.pop(oldest, None)
            self._voices[note] = {
                "freq": freq, "start_frame": self._frame,
                "release_frame": None, "velocity": vel,
            }

    def note_off(self, note):
        if not self.ok or note is None:
            return
        try:
            note = int(note)
        except Exception:
            return
        with self._voices_lock:
            v = self._voices.get(note)
            if v and v["release_frame"] is None:
                v["release_frame"] = self._frame

    def all_notes_off(self):
        if not self.ok:
            return
        with self._voices_lock:
            for v in self._voices.values():
                if v["release_frame"] is None:
                    v["release_frame"] = self._frame

    def close(self):
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        except Exception as e:
            logger.error(f"Audio close error: {e}")

    def _callback(self, outdata, frames, time_info, status):
        try:
            if not self.ok or np is None:
                outdata.fill(0.0)
                return
            n_arr = np.arange(frames, dtype=np.float32)
            with self._voices_lock:
                current_frame = self._frame
                voices_snapshot = list(self._voices.items())
            if not voices_snapshot:
                with self._voices_lock:
                    self._frame += frames
                outdata.fill(0.0)
                return
            mix = np.zeros(frames, dtype=np.float32)
            remove_notes = []
            attack, decay, sustain = 0.004, 0.08, 0.65
            for note, voice in voices_snapshot:
                age_frames = current_frame + n_arr - voice["start_frame"]
                age = np.maximum(0.0, age_frames) / self.sample_rate
                env = np.full(frames, sustain, dtype=np.float32)
                attack_mask = age < attack
                if np.any(attack_mask):
                    env[attack_mask] = age[attack_mask] / attack
                decay_mask = (age >= attack) & (age < attack + decay)
                if np.any(decay_mask):
                    env[decay_mask] = 1.0 - (1.0 - sustain) * ((age[decay_mask] - attack) / decay)
                if voice["release_frame"] is not None:
                    rel = (current_frame + n_arr - voice["release_frame"]) / self.sample_rate
                    rel_mask = rel >= 0.0
                    if np.any(rel_mask):
                        env = env * np.where(rel_mask, np.exp(-8.0 * rel), 1.0)
                    if rel[-1] > 0.3:
                        remove_notes.append(note)
                phase = 2.0 * np.pi * voice["freq"] * age_frames / self.sample_rate
                wave = (np.sin(phase) + 0.35 * np.sin(2.0 * phase)
                        + 0.18 * np.sin(3.0 * phase) + 0.08 * np.sin(4.0 * phase))
                mix += wave * (0.22 * voice["velocity"] * env)
            with self._voices_lock:
                for note in remove_notes:
                    self._voices.pop(note, None)
                self._frame += frames
            mix *= self.volume
            mix = np.tanh(mix * 0.8) * 0.9
            outdata[:, 0] = mix
            outdata[:, 1] = mix
        except Exception as e:
            logger.error(f"Audio callback error: {e}")
            try:
                outdata.fill(0.0)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════
#                          OVERLAY WINDOW
# ═══════════════════════════════════════════════════════════════════

class NoteOverlayWindow(QtWidgets.QWidget):
    def __init__(self, bot=None, parent_gui=None):
        super().__init__(parent_gui)
        self.bot = bot
        self._opacity_anim = None
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
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
        self._apply_theme_from_current()
        self.apply_settings()
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.resize(520, 240)
        self.move(screen.width() // 2 - self.width() // 2,
                  screen.height() - self.height() - 80)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._perform_update)
        self.update_timer.start(100)
        self.pending_update = None
        self.setWindowOpacity(0.0)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        top_bar = QtWidgets.QWidget()
        top_bar.setStyleSheet("background: transparent;")
        tbl = QtWidgets.QHBoxLayout(top_bar)
        tbl.setContentsMargins(0, 0, 0, 0)

        self.song_title = QtWidgets.QLabel("AstraKeys")
        tbl.addWidget(self.song_title)

        self.progress_label = QtWidgets.QLabel("0%")
        self.progress_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        tbl.addWidget(self.progress_label, 1)

        self.pin_btn = self._btn("📌", 'overlay.pin_tooltip')
        self.opacity_btn = self._btn("◐", 'overlay.opacity_tooltip')
        self.close_btn = self._btn("✕", 'overlay.close_tooltip')
        tbl.addWidget(self.pin_btn)
        tbl.addWidget(self.opacity_btn)
        tbl.addWidget(self.close_btn)
        layout.addWidget(top_bar)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.note_label = QtWidgets.QLabel()
        self.note_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

        bottom = QtWidgets.QWidget()
        bottom.setStyleSheet("background: transparent;")
        bbl = QtWidgets.QHBoxLayout(bottom)
        bbl.setContentsMargins(0, 0, 0, 0)
        self.status_label = QtWidgets.QLabel("—")
        bbl.addWidget(self.status_label)
        self.pos_label = QtWidgets.QLabel("0/0")
        self.pos_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        bbl.addWidget(self.pos_label, 1)
        layout.addWidget(bottom)

        self.pin_btn.clicked.connect(self.toggle_pin)
        self.opacity_btn.clicked.connect(self.show_opacity_menu)
        self.close_btn.clicked.connect(self.hide_with_fade)
        self.title_bar = top_bar

    def _btn(self, text, tip_key):
        b = QtWidgets.QPushButton(text)
        b.setFixedSize(26, 26)
        b.setToolTip(tr(tip_key))
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {self.accent_color}55;
                border-radius: 6px;
                color: {self.text_color};
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {self.highlight_bg};
                border-color: {self.accent_color};
            }}
        """)
        return b

    def refresh_tooltips(self):
        self.pin_btn.setToolTip(tr('overlay.pin_tooltip'))
        self.opacity_btn.setToolTip(tr('overlay.opacity_tooltip'))
        self.close_btn.setToolTip(tr('overlay.close_tooltip'))

    def _apply_theme_from_current(self):
        t = get_theme()
        self.bg_color = t['overlay_bg']
        self.text_color = t['overlay_text']
        self.accent_color = t['overlay_accent']
        self.highlight_bg = t['overlay_highlight']

    def update_metadata(self, song_name, progress, is_playing, is_playback):
        self.song_title.setText((song_name or "AstraKeys")[:30])
        p = progress if progress is not None else 0
        self.progress_label.setText(f"{p}%")
        self.progress_bar.setValue(p)
        if is_playback:
            status = tr('status.playback')
        else:
            status = tr('status.playing') if is_playing else tr('status.paused')
        self.status_label.setText(status)

    def update_notes(self, song, current_pos, lines=None, cpl=None):
        self.pending_update = (song, current_pos, lines or self.lines,
                                cpl or self.chars_per_line)

    def _perform_update(self):
        if self.pending_update is None:
            return
        song, pos, lines, cpl = self.pending_update
        self.pending_update = None
        try:
            if not song or pos >= len(song):
                self.note_label.setText("")
                return
            end = min(len(song), pos + lines * cpl)
            text = song[pos:end]
            chunks = []
            cur = ""
            i = 0
            while i < len(text):
                c = text[i]
                cur += c
                if c == '[':
                    j = i + 1
                    while j < len(text) and text[j] != ']':
                        j += 1
                    if j < len(text):
                        cur += text[i + 1:j + 1]
                        i = j + 1
                        if len(cur) >= cpl:
                            chunks.append(cur)
                            cur = ""
                        continue
                i += 1
                if len(cur) >= cpl:
                    chunks.append(cur)
                    cur = ""
            if cur:
                chunks.append(cur)
            chunks = chunks[:lines]
            parts = []
            if chunks:
                first = chunks[0]
                if first:
                    parts.append(
                        f'<span style="background-color:{self.highlight_bg}; '
                        f'color:{self.text_color}; font-weight:bold; '
                        f'padding:0 3px; border-radius:3px; '
                        f'border:1px solid {self.accent_color};">'
                        f'{html.escape(first[0])}</span>'
                        f'<span style="color:{self.text_color};">{html.escape(first[1:])}</span>'
                    )
                for line in chunks[1:]:
                    parts.append(
                        f'<span style="color:{self.text_color};">{html.escape(line)}</span>')
            self.note_label.setText("<br>".join(parts))
            self.pos_label.setText(f"{pos}/{len(song)}")
        except Exception as e:
            logger.error(f"overlay update: {e}")

    def apply_settings(self):
        self.note_label.setStyleSheet(f"""
            QLabel {{
                background: {self.bg_color};
                color: {self.text_color};
                font-family: 'Consolas','Courier New',monospace;
                font-size: {self.font_size}px;
                border: 1px solid {self.accent_color};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        self.song_title.setStyleSheet(
            f"color:{self.text_color};font-weight:bold;font-size:13px;background:transparent;")
        self.progress_label.setStyleSheet(
            f"color:{self.accent_color};font-size:12px;background:transparent;")
        self.status_label.setStyleSheet(
            f"color:{self.accent_color};font-size:11px;background:transparent;")
        self.pos_label.setStyleSheet(
            f"color:{self.text_color};font-size:11px;background:transparent;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.bg_color};
                border: 1px solid {self.accent_color}66;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.accent_color}, stop:1 {self.text_color});
                border-radius: 3px;
            }}
        """)

    def load_settings(self):
        try:
            if os.path.exists(OVERLAY_FILE):
                s = json.load(open(OVERLAY_FILE, encoding="utf-8"))
                for k in ("opacity", "font_size", "lines", "chars_per_line",
                          "bg_color", "text_color", "highlight_bg", "accent_color"):
                    if k in s:
                        setattr(self, k, s[k])
        except Exception:
            pass

    def save_settings(self):
        try:
            json.dump({k: getattr(self, k) for k in
                       ("opacity", "font_size", "lines", "chars_per_line",
                        "bg_color", "text_color", "highlight_bg", "accent_color")},
                      open(OVERLAY_FILE, "w", encoding="utf-8"), indent=2)
        except Exception:
            pass

    def contextMenuEvent(self, e):
        m = QtWidgets.QMenu(self)
        fs = m.addMenu(tr('overlay.font_size'))
        for s in (14, 16, 18, 20, 24, 28):
            a = fs.addAction(f"{s}px")
            a.triggered.connect(lambda _, s=s: self._set_font_size(s))
        ls = m.addMenu(tr('overlay.lines'))
        for l in (2, 3, 4, 5, 6):
            a = ls.addAction(str(l))
            a.triggered.connect(lambda _, l=l: self._set_lines(l))
        m.addSeparator()
        r = m.addAction(tr('overlay.reset'))
        r.triggered.connect(self.reset_settings)
        m.exec(e.globalPos())

    def _set_font_size(self, s):
        self.font_size = s
        self.apply_settings()
        self.save_settings()

    def _set_lines(self, l):
        self.lines = l
        self.save_settings()

    def reset_settings(self):
        self._apply_theme_from_current()
        self.opacity = 0.92
        self.font_size = 18
        self.lines = 4
        self.chars_per_line = 50
        self.apply_settings()
        self.save_settings()

    def show_with_fade(self):
        self.setWindowOpacity(0.0)
        super().show()
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(self.opacity)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._opacity_anim = anim
        anim.start()

    def hide_with_fade(self):
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(220)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        anim.finished.connect(super().hide)
        self._opacity_anim = anim
        anim.start()

    def mousePressEvent(self, e):
        if (e.button() == QtCore.Qt.MouseButton.LeftButton
                and self.title_bar.geometry().contains(e.position().toPoint())):
            self.dragging = True
            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.dragging and e.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self.dragging = False
        super().mouseReleaseEvent(e)

    def toggle_pin(self):
        flags = self.windowFlags()
        if flags & QtCore.Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, False)
            self.pin_btn.setText("◻")
        else:
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
            self.pin_btn.setText("📌")
        self.show()

    def show_opacity_menu(self):
        m = QtWidgets.QMenu(self)
        a = m.addAction(tr('overlay.opacity_1pct'))
        a.setData(0.01)
        for v in range(5, 101, 5):
            a = m.addAction(f"{v}%")
            a.setData(v / 100.0)
        act = m.exec(self.opacity_btn.mapToGlobal(
            QtCore.QPoint(0, self.opacity_btn.height())))
        if act:
            self.opacity = act.data()
            self.setWindowOpacity(self.opacity)
            self.save_settings()

    def closeEvent(self, e):
        self.save_settings()
        self.hide()
        e.ignore()


# ═══════════════════════════════════════════════════════════════════
#                        PEDAL DIALOG
# ═══════════════════════════════════════════════════════════════════

class PedalSettingsDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('pedal.title'))
        self.setMinimumSize(320, 420)
        v = QtWidgets.QVBoxLayout(self)
        self.list = QtWidgets.QListWidget()
        for k in sorted(self.bot.pedal_keys):
            self.list.addItem(k)
        v.addWidget(self.list)

        row = QtWidgets.QHBoxLayout()
        self.inp = QtWidgets.QLineEdit()
        self.inp.setMaxLength(1)
        self.inp.setPlaceholderText(tr('pedal.placeholder'))
        row.addWidget(self.inp)
        add = HoverButton(tr('pedal.add'))
        add.setProperty("role", "primary")
        add.clicked.connect(self._add)
        row.addWidget(add)
        v.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        rem = HoverButton(tr('pedal.remove'))
        rem.clicked.connect(self._rem)
        row2.addWidget(rem)
        rst = HoverButton(tr('pedal.reset'))
        rst.clicked.connect(self._reset)
        row2.addWidget(rst)
        v.addLayout(row2)

        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(tr('ui.ok'))
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText(tr('ui.cancel'))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _add(self):
        c = self.inp.text().strip()
        if c and len(c) == 1 and c not in self.bot.pedal_keys:
            self.bot.pedal_keys.add(c)
            self.list.addItem(c)
            self.inp.clear()
            self._save()

    def _rem(self):
        r = self.list.currentRow()
        if r >= 0:
            k = self.list.takeItem(r).text()
            self.bot.pedal_keys.discard(k)
            self._save()

    def _reset(self):
        self.bot.pedal_keys = set(DEFAULT_PEDAL_KEYS)
        self.list.clear()
        for k in sorted(self.bot.pedal_keys):
            self.list.addItem(k)
        self._save()

    def _save(self):
        try:
            json.dump(list(self.bot.pedal_keys),
                      open(PEDAL_FILE, "w", encoding="utf-8"))
        except Exception:
            pass

    def accept(self):
        self._save()
        super().accept()


# ═══════════════════════════════════════════════════════════════════
#                            BOT CORE
# ═══════════════════════════════════════════════════════════════════

class RobloxPianoBot(QtCore.QObject):
    state_changed = QtCore.pyqtSignal()

    def __init__(self, playlist_with_names):
        super().__init__()
        self.keyboard = Controller() if Controller else None
        self.lock = threading.Lock()
        self.playlist = []
        for name, song in playlist_with_names:
            sanitized = self.sanitize_song(song)
            if sanitized:
                self.playlist.append((name, sanitized))
        if not self.playlist:
            self.playlist = [("Empty", "")]

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
        self._timers_lock = threading.Lock()
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
        self.playback_limit = 0
        self._preview_active = False
        self.gui_update_callback = None
        self.overlay_window = None
        self.progress = 0
        self.check_updates_on_start = False
        self.midi_out_enabled = False
        self.midi_port = None
        self.midi_port_name = ""
        self._midi_lock = threading.Lock()
        self._midi_note_counts = {}
        self.audio_player = AudioNotePlayer() if HAS_AUDIO else None
        self.audio_enabled = False
        self.audio_volume = 0.7
        self.auto_play_no_pedal = True
        self.auto_hold_ms = 180
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
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
                self.mode = int(s.get("mode", 1))
                self.min_note_delay = int(s.get("min_delay", 0))
                self.max_note_delay = int(s.get("max_delay", 10))
                self.start_delay = float(s.get("start_delay", 0.03))
                self.check_updates_on_start = bool(s.get("check_updates_on_start", False))
                self.midi_out_enabled = bool(s.get("midi_out_enabled", False))
                self.midi_port_name = s.get("midi_port_name", "")
                self.audio_enabled = bool(s.get("audio_enabled", False)) and HAS_AUDIO
                self.audio_volume = float(s.get("audio_volume", 0.7))
                self.auto_play_no_pedal = bool(s.get("auto_play_no_pedal", True))
                self.auto_hold_ms = int(s.get("auto_hold_ms", 180))
                if self.audio_player:
                    self.audio_player.set_volume(self.audio_volume)
        except Exception as e:
            logger.error(f"Load app settings error: {e}")

    def save_app_settings(self):
        try:
            s = {}
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                        s = json.load(f)
                except Exception:
                    s = {}
            s.update({
                "mode": self.mode, "min_delay": self.min_note_delay,
                "max_delay": self.max_note_delay, "start_delay": self.start_delay,
                "lang": tr_obj.lang, "theme": _current_theme_key,
                "check_updates_on_start": self.check_updates_on_start,
                "midi_out_enabled": self.midi_out_enabled,
                "midi_port_name": self.midi_port_name,
                "audio_enabled": self.audio_enabled,
                "audio_volume": self.audio_volume,
                "auto_play_no_pedal": self.auto_play_no_pedal,
                "auto_hold_ms": self.auto_hold_ms,
            })
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save app settings error: {e}")

    def load_pedal_settings(self):
        try:
            if os.path.exists(PEDAL_FILE):
                with open(PEDAL_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    self.pedal_keys = set(data)
        except Exception as e:
            logger.error(f"Load pedal settings error: {e}")

    def load_recordings_index(self):
        try:
            if os.path.exists(RECORDINGS_INDEX):
                with open(RECORDINGS_INDEX, "r", encoding="utf-8") as f:
                    self.recordings_index = json.load(f)
        except Exception as e:
            logger.error(f"Load recordings index error: {e}")

    def save_recordings_index(self):
        try:
            with open(RECORDINGS_INDEX, "w", encoding="utf-8") as f:
                json.dump(self.recordings_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save recordings index error: {e}")

    def _unique_recording_name(self, desired_name):
        existing = {e.get('name', '') for e in self.recordings_index}
        desired_name = (desired_name or "Untitled").strip() or "Untitled"
        if desired_name not in existing:
            return desired_name
        c = 2
        while f"{desired_name} ({c})" in existing:
            c += 1
        return f"{desired_name} ({c})"

    def list_midi_ports(self):
        if not HAS_MIDI_OUT:
            return []
        try:
            return list(mido.get_output_names())
        except Exception as e:
            logger.error(f"list_midi_ports: {e}")
            return []

    def open_midi_port(self, port_name):
        if not HAS_MIDI_OUT:
            return False, "mido not installed"
        try:
            with self._midi_lock:
                self.close_midi_port_locked()
                self.midi_port = mido.open_output(port_name)
                self.midi_port_name = port_name
                return True, None
        except Exception as e:
            return False, str(e)

    def close_midi_port_locked(self):
        if self.midi_port:
            try:
                for note in list(self._midi_note_counts.keys()):
                    try:
                        self.midi_port.send(mido.Message('note_off', note=note, velocity=0))
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self.midi_port.close()
            except Exception:
                pass
            self.midi_port = None
            self.midi_port_name = ""
            self._midi_note_counts.clear()

    def close_midi_port(self):
        with self._midi_lock:
            self.close_midi_port_locked()

    def _midi_note_on(self, note):
        if note is None or not self.midi_port:
            return
        count = self._midi_note_counts.get(note, 0)
        if count == 0:
            self.midi_port.send(mido.Message("note_on", note=note, velocity=100))
        self._midi_note_counts[note] = count + 1

    def _midi_note_off(self, note):
        if note is None or not self.midi_port:
            return
        count = self._midi_note_counts.get(note, 0)
        if count <= 1:
            self.midi_port.send(mido.Message("note_off", note=note, velocity=0))
            self._midi_note_counts.pop(note, None)
        else:
            self._midi_note_counts[note] = count - 1

    def set_overlay_window(self, win):
        self.overlay_window = win

    def set_gui_update_callback(self, cb):
        self.gui_update_callback = cb

    def _gui_update(self):
        if self.gui_update_callback:
            self.gui_update_callback()

    def sanitize_song(self, song):
        allowed = set(ROBLOX_KEYS + " \t\r[]")
        return ''.join(ch for ch in song if ch in allowed)

    def get_random_delay(self):
        return random.uniform(self.min_note_delay, self.max_note_delay) / 1000.0

    def _schedule_timer(self, delay, func, args=()):
        holder = {}

        def _wrapper():
            try:
                func(*args)
            finally:
                t = holder.get("timer")
                if t is not None:
                    with self._timers_lock:
                        try:
                            self.pending_timers.remove(t)
                        except ValueError:
                            pass

        timer = threading.Timer(delay, _wrapper)
        timer.daemon = True
        holder["timer"] = timer
        with self._timers_lock:
            self.pending_timers.append(timer)
        timer.start()
        return timer

    def press_key(self, key):
        if not key or not isinstance(key, str) or len(key) != 1:
            return
        midi_note = key_to_midi(key)
        with self.lock:
            if self.active_keys.get(key, False):
                return
            if self.audio_enabled and self.audio_player and midi_note is not None:
                self.audio_player.note_on(midi_note)
            if (self.midi_out_enabled and HAS_MIDI_OUT and self.midi_port
                    and midi_note is not None):
                try:
                    with self._midi_lock:
                        self._midi_note_on(midi_note)
                    self.active_keys[key] = True
                except Exception as e:
                    logger.error(f"MIDI press error: {e}")
                return
            if not self.keyboard:
                self.active_keys[key] = True
                return
            base_key, needs_shift = get_keyboard_parts(key)
            if base_key is None:
                return
            try:
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
        if not key or not isinstance(key, str) or len(key) != 1:
            return
        midi_note = key_to_midi(key)
        with self.lock:
            if self.audio_enabled and self.audio_player and midi_note is not None:
                self.audio_player.note_off(midi_note)
            if (self.midi_out_enabled and HAS_MIDI_OUT and self.midi_port
                    and midi_note is not None):
                try:
                    with self._midi_lock:
                        self._midi_note_off(midi_note)
                    self.active_keys[key] = False
                except Exception as e:
                    logger.error(f"MIDI release error: {e}")
                return
            if not self.active_keys.get(key, False):
                return
            if not self.keyboard:
                self.active_keys[key] = False
                return
            base_key, _ = get_keyboard_parts(key)
            if base_key is None:
                return
            try:
                self.keyboard.release(base_key)
                self.active_keys[key] = False
            except Exception as e:
                logger.error(f"Release error: {e}")

    def release_all(self):
        with self._timers_lock:
            pending = list(self.pending_timers)
            self.pending_timers.clear()
        for t in pending:
            try:
                t.cancel()
            except Exception:
                pass
        if self.audio_enabled and self.audio_player:
            try:
                self.audio_player.all_notes_off()
            except Exception:
                pass
        if self.midi_out_enabled and HAS_MIDI_OUT and self.midi_port:
            try:
                with self._midi_lock:
                    for note in list(self._midi_note_counts.keys()):
                        try:
                            self.midi_port.send(mido.Message("note_off", note=note, velocity=0))
                        except Exception:
                            pass
                    self._midi_note_counts.clear()
            except Exception:
                pass
        with self.lock:
            for k in list(self.active_keys.keys()):
                if self.active_keys.get(k, False) and self.keyboard:
                    base_key, _ = get_keyboard_parts(k)
                    if base_key:
                        try:
                            self.keyboard.release(base_key)
                        except Exception:
                            pass
            self.active_keys.clear()

    def play_chord(self, chord):
        if self.mode == 1:
            for k in chord:
                self.press_key(k)
            time.sleep(0.001)
        else:
            delays = [self.get_random_delay() for _ in chord]
            for i, k in enumerate(chord):
                self._schedule_timer(delays[i], self.press_key, (k,))
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
            for i, k in enumerate(reversed(chord)):
                self._schedule_timer(delays[i], self.release_key, (k,))
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
                self._gui_update()
                return
        self.song_index = old

    def _play_latest_recording(self):
        if not self.recordings_index:
            return
        latest = max(self.recordings_index, key=lambda e: e.get('date', ''))
        json_path = os.path.join("recordings", latest.get('json_file', ''))
        if not os.path.exists(json_path):
            return
        if self.load_recording(json_path):
            self.start_playback()

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.recording_events = []
        self.recording_start_time = time.time()
        self.recording_song_name = self.song_name
        self._gui_update()

    def stop_recording(self, custom_name=None):
        if not self.is_recording:
            return
        self.is_recording = False
        if not self.recording_events:
            self._gui_update()
            return
        press_times = {}
        for ev in self.recording_events:
            if ev['action'] == 'press':
                press_times[ev['key']] = ev['time']
            elif ev['action'] == 'release':
                press_times.pop(ev['key'], None)
        for key, t in list(press_times.items()):
            self.recording_events.append({'time': round(t + 0.2, 3),
                                           'key': key, 'action': 'release'})
        self.recording_events.sort(key=lambda e: e['time'])
        events = self.recording_events[:]
        self._save_recording(custom_name or self.recording_song_name, events)
        self.recording_events = []
        self._gui_update()

    def _save_recording(self, name, events):
        if not events:
            return None
        events = sorted(events, key=lambda e: e['time'])
        final_name = self._unique_recording_name(name)
        os.makedirs("recordings", exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe = re.sub(r'[^\w\-_]', '_', final_name)
        json_fname = f"recordings/{safe}_{ts}.json"
        data = {
            'song_name': final_name, 'start_time': datetime.now().isoformat(),
            'mode': self.mode, 'min_delay': self.min_note_delay,
            'max_delay': self.max_note_delay, 'start_delay': self.start_delay,
            'events': events,
        }
        try:
            with open(json_fname, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Save recording error: {e}")
            return None
        midi_fname = None
        if HAS_MIDI:
            midi_fname = f"recordings/{safe}_{ts}.mid"
            self.export_recording_to_midi(events, midi_fname)
        last_time = max((ev['time'] for ev in events), default=0.0)
        self.recordings_index.append({
            "name": final_name, "json_file": os.path.basename(json_fname),
            "midi_file": os.path.basename(midi_fname) if midi_fname else None,
            "date": datetime.now().isoformat(), "favorite": False,
            "duration": round(last_time, 2),
        })
        self.save_recordings_index()
        return final_name

    def save_recording_events(self, name, events):
        return self._save_recording(name, events)

    def export_recording_to_midi(self, events, filename):
        if not HAS_MIDI or not events:
            return
        midi = MIDIFile(1)
        track, channel = 0, 0
        midi.addTempo(track, 0, 60)
        has_press = any(ev.get('action') == 'press' for ev in events)
        if has_press:
            min_time = min(ev['time'] for ev in events if ev['action'] == 'press')
        else:
            min_time = min(max(0.0, ev['time'] - ev.get('duration', 0.2))
                           for ev in events if ev['action'] == 'release')
        pending = {}
        if has_press:
            for ev in events:
                t = max(0.0, ev['time'] - min_time)
                chord_str = ev.get('key', '')
                notes = [key_to_midi(ch) for ch in chord_str if key_to_midi(ch) is not None]
                if not notes:
                    continue
                if ev['action'] == 'press':
                    pending[chord_str] = (t, notes)
                elif ev['action'] == 'release' and chord_str in pending:
                    start_time, pressed_notes = pending.pop(chord_str)
                    duration = max(0.05, t - start_time)
                    for n in pressed_notes:
                        midi.addNote(track, channel, n, start_time, duration, 100)
            for chord_str, (start_time, notes) in pending.items():
                for n in notes:
                    midi.addNote(track, channel, n, start_time, 0.25, 100)
        else:
            for ev in events:
                if ev['action'] != 'release':
                    continue
                chord_str = ev.get('key', '')
                duration = max(0.05, ev.get('duration', 0.2))
                start_time = max(0.0, ev['time'] - duration - min_time)
                for ch in chord_str:
                    n = key_to_midi(ch)
                    if n is not None:
                        midi.addNote(track, channel, n, start_time, duration, 100)
        try:
            with open(filename, "wb") as f:
                midi.writeFile(f)
        except Exception as e:
            logger.error(f"MIDI export error: {e}")

    def load_recording(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            events = data.get('events', [])
            if not events:
                return False
            events.sort(key=lambda e: e.get('time', 0.0))
            if not any(ev.get('action') == 'press' for ev in events):
                reconstructed = []
                for ev in events:
                    if ev.get('action') != 'release':
                        continue
                    dur = max(0.05, ev.get('duration', 0.2))
                    press_time = max(0.0, ev['time'] - dur)
                    reconstructed.append({'time': press_time, 'key': ev['key'],
                                          'action': 'press'})
                    reconstructed.append({'time': ev['time'], 'key': ev['key'],
                                          'action': 'release'})
                events = sorted(reconstructed, key=lambda e: e['time'])
            cleaned, pending, last_time = [], {}, 0.0
            for ev in events:
                t = float(ev.get('time', 0.0))
                last_time = max(last_time, t)
                key = ev.get('key', '')
                action = ev.get('action')
                if not key or action not in ('press', 'release'):
                    continue
                if action == 'press':
                    if key in pending:
                        cleaned.append({'time': round(max(0.0, t - 0.001), 3),
                                        'key': key, 'action': 'release'})
                        pending.pop(key, None)
                    pending[key] = True
                else:
                    pending.pop(key, None)
                cleaned.append({'time': round(t, 3), 'key': key, 'action': action})
            for key in list(pending.keys()):
                cleaned.append({'time': round(last_time + 0.2, 3),
                                'key': key, 'action': 'release'})
            cleaned.sort(key=lambda e: e['time'])
            self.playback_events = cleaned
            return True
        except Exception as e:
            logger.error(f"Load recording error: {e}")
            return False

    def preview_recording(self, filepath, seconds=5.0):
        if self.is_playback:
            return False
        if not self.load_recording(filepath):
            return False
        self._preview_active = True
        self.start_playback(limit_seconds=seconds)
        return True

    def start_playback(self, limit_seconds=0):
        if self.is_playback or not self.playback_events:
            return
        self.is_playback = True
        self.playback_stop = False
        self.playback_paused = False
        self.playback_elapsed = 0
        self.playback_limit = limit_seconds
        self.release_all()
        if not self._preview_active:
            activate_roblox_window()
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        self._gui_update()

    def stop_playback(self):
        if not self.is_playback:
            return
        self.playback_stop = True
        if self.playback_thread:
            self.playback_thread.join(0.5)
        self.is_playback = False
        self.release_all()
        self._preview_active = False
        self.playback_limit = 0
        self._gui_update()

    def toggle_playback_pause(self):
        if not self.is_playback:
            return
        self.playback_paused = not self.playback_paused
        if self.playback_paused:
            self.playback_pause_time = time.time()
        else:
            self.playback_elapsed += time.time() - self.playback_pause_time
        self._gui_update()

    def _playback_worker(self):
        start = time.time()
        self.playback_elapsed = 0
        for ev in self.playback_events:
            if self.playback_stop:
                break
            if self.playback_limit and ev['time'] > self.playback_limit:
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
            chord_str, action = ev['key'], ev['action']
            if action == 'press':
                for k in chord_str:
                    self.press_key(k)
            elif action == 'release':
                for k in chord_str:
                    self.release_key(k)
        self.release_all()
        self.is_playback = False
        self.playback_limit = 0
        self._preview_active = False
        self._gui_update()

    def _record_event(self, chord, action):
        if self.is_recording and chord:
            elapsed = time.time() - self.recording_start_time
            self.recording_events.append({
                'time': round(elapsed, 3), 'key': ''.join(chord), 'action': action,
            })

    def _next_note_pos(self, idx):
        if idx < 0:
            idx = 0
        if idx >= len(self.song):
            return idx
        if self.song[idx] == '[':
            end = self.song.find(']', idx)
            return end + 1 if end != -1 else idx + 1
        return idx + 1

    def _prev_note_pos(self, idx):
        i = idx - 1
        while i >= 0 and self.song[i].isspace():
            i -= 1
        if i < 0:
            return 0
        if self.song[i] == ']':
            start = self.song.rfind('[', 0, i)
            return start if start != -1 else i
        return i

    def play_song(self):
        time.sleep(0.5)
        current_chord = None
        while True:
            try:
                if self.is_playback:
                    if current_chord:
                        self._record_event(current_chord, "release")
                        self.release_chord(current_chord)
                        current_chord = None
                    time.sleep(0.05)
                    continue
                if self.overlay_window:
                    self.overlay_window.update_notes(self.song, self.note_index)
                if self.restart:
                    self.restart = False
                    self.note_index = 0
                    self.frozen_note_index = 0
                    self.progress = 0
                    if current_chord:
                        self._record_event(current_chord, "release")
                        self.release_chord(current_chord)
                        current_chord = None
                    self.release_all()
                    self._gui_update()
                    continue
                if not self.playing:
                    if current_chord:
                        self._record_event(current_chord, "release")
                        self.release_chord(current_chord)
                        current_chord = None
                    time.sleep(0.05)
                    continue
                if self.freeze_note:
                    time.sleep(0.02)
                    continue
                if self.note_index >= len(self.song):
                    self.playing = False
                    self.progress = 100
                    if current_chord:
                        self._record_event(current_chord, "release")
                        self.release_chord(current_chord)
                        current_chord = None
                    self._gui_update()
                    time.sleep(0.3)
                    continue
                char = self.song[self.note_index]
                if char.isspace():
                    self.note_index += 1
                    continue
                if self.skip_notes != 0:
                    delta = self.skip_notes
                    self.skip_notes = 0
                    pos = self.note_index
                    if delta > 0:
                        for _ in range(delta):
                            pos = self._next_note_pos(pos)
                            if pos >= len(self.song):
                                break
                    else:
                        for _ in range(-delta):
                            pos = self._prev_note_pos(pos)
                            if pos <= 0:
                                break
                    self.note_index = max(0, min(pos, len(self.song)))
                    self._gui_update()
                    continue
                if not (self.hold_star or self.auto_play_no_pedal):
                    time.sleep(0.005)
                    continue
                if char == '[':
                    end = self.song.find(']', self.note_index)
                    if end == -1:
                        chord, next_idx = [char], self.note_index + 1
                    else:
                        chord = list(''.join(self.song[self.note_index + 1:end].split()))
                        next_idx = end + 1
                else:
                    chord, next_idx = [char], self.note_index + 1
                if not chord:
                    self.note_index = next_idx
                    continue
                if self.start_delay > 0:
                    time.sleep(self.start_delay)
                self._record_event(chord, "press")
                self.play_chord(chord)
                current_chord = chord
                if self.hold_star:
                    while (self.hold_star and self.playing
                           and not self.restart and not self.freeze_note):
                        time.sleep(0.001)
                elif self.auto_play_no_pedal:
                    hold_seconds = max(0.02, self.auto_hold_ms / 1000.0)
                    hold_until = time.time() + hold_seconds
                    while (time.time() < hold_until and self.playing
                           and not self.restart and not self.freeze_note
                           and not self.hold_star):
                        time.sleep(0.001)
                    if self.hold_star:
                        while (self.hold_star and self.playing
                               and not self.restart and not self.freeze_note):
                            time.sleep(0.001)
                if current_chord:
                    self._record_event(current_chord, "release")
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
                    if self.playing and not self.is_playback:
                        activate_roblox_window()
                    self._gui_update()
                elif key == Key.f2:
                    self.restart = True
                elif key == Key.f3:
                    self.skip_notes += 25
                elif key == Key.f4:
                    self.skip_notes -= 25
                elif key == Key.f5:
                    self.toggle_playback_pause()
                elif key == Key.f6:
                    self.freeze_note = not self.freeze_note
                    if self.freeze_note:
                        self.frozen_note_index = self.note_index
                    self._gui_update()
                elif key == Key.f7:
                    self.mode = 2 if self.mode == 1 else 1
                    self.save_app_settings()
                    self._gui_update()
                elif key == Key.f8:
                    self.next_song()
                elif key == Key.f9:
                    self.stop_playback()
                elif key == Key.f10:
                    self._play_latest_recording()
                elif key == Key.f12:
                    if self.is_recording:
                        self.stop_recording()
                    else:
                        self.start_recording()
                    self._gui_update()
                elif key_char is not None and key_char in self.pedal_keys:
                    self.hold_star = True
                else:
                    if (self.is_recording and key_char and len(key_char) == 1
                            and is_valid_key(key_char)):
                        elapsed = time.time() - self.recording_start_time
                        self.recording_events.append({
                            'time': round(elapsed, 3), 'key': key_char, 'action': 'press',
                        })
            except Exception as e:
                logger.error(f"on_press error: {e}")

        def on_release(key):
            try:
                key_char = getattr(key, 'char', None)
                if key_char is not None and key_char in self.pedal_keys:
                    self.hold_star = False
                else:
                    if (self.is_recording and key_char and len(key_char) == 1
                            and is_valid_key(key_char)):
                        elapsed = time.time() - self.recording_start_time
                        self.recording_events.append({
                            'time': round(elapsed, 3), 'key': key_char, 'action': 'release',
                        })
            except Exception as e:
                logger.error(f"on_release error: {e}")

        try:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            logger.error(f"Listener failed: {e}")


# ═══════════════════════════════════════════════════════════════════
#                     RECORDINGS MANAGER
# ═══════════════════════════════════════════════════════════════════

class RecordingsManagerDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('recordings.title'))
        self.setMinimumSize(820, 560)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        top_row = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(tr('recordings.search'))
        self.search_input.textChanged.connect(self.refresh_list)
        top_row.addWidget(self.search_input, 1)
        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItems([
            tr('recordings.sort_new'), tr('recordings.sort_old'),
            tr('recordings.sort_az'), tr('recordings.sort_za'),
            tr('recordings.sort_dur'), tr('recordings.sort_fav'),
        ])
        self.sort_combo.currentIndexChanged.connect(self.refresh_list)
        top_row.addWidget(self.sort_combo)
        layout.addLayout(top_row)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.refresh_list()
        layout.addWidget(self.list_widget)

        row = QtWidgets.QHBoxLayout()
        for text, slot in [
            (tr('recordings.preview'), self.preview_selected),
            (tr('recordings.favorite'), self.toggle_favorite),
            (tr('recordings.rename'), self.rename_selected),
            (tr('recordings.editor'), self.open_editor),
            (tr('recordings.delete'), self.delete_selected),
        ]:
            b = HoverButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        layout.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        for text, slot in [
            (tr('recordings.export_zip'), self.export_recordings_zip),
            (tr('recordings.import_zip'), self.import_recordings_zip),
            (tr('recordings.open_folder'), self.open_recordings_folder),
            (tr('recordings.clean'), self.clean_non_favorite),
        ]:
            b = HoverButton(text)
            b.clicked.connect(slot)
            row2.addWidget(b)
        layout.addLayout(row2)

        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText(tr('ui.close'))
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def refresh_list(self):
        self.list_widget.clear()
        query = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ""
        sort_mode = self.sort_combo.currentIndex() if hasattr(self, 'sort_combo') else 0
        indexed = list(enumerate(self.bot.recordings_index))
        if query:
            indexed = [(i, e) for i, e in indexed if query in e.get('name', '').lower()]
        if sort_mode == 0:
            indexed.sort(key=lambda ie: ie[1].get('date', ''), reverse=True)
        elif sort_mode == 1:
            indexed.sort(key=lambda ie: ie[1].get('date', ''))
        elif sort_mode == 2:
            indexed.sort(key=lambda ie: ie[1].get('name', '').lower())
        elif sort_mode == 3:
            indexed.sort(key=lambda ie: ie[1].get('name', '').lower(), reverse=True)
        elif sort_mode == 4:
            indexed.sort(key=lambda ie: ie[1].get('duration', 0), reverse=True)
        elif sort_mode == 5:
            indexed.sort(key=lambda ie: (not ie[1].get('favorite', False),
                                          ie[1].get('date', '')))
        for idx, entry in indexed:
            name = entry.get('name', 'Untitled')
            date = entry.get('date', '')
            fav = '★' if entry.get('favorite', False) else '☆'
            dur = entry.get('duration', 0)
            midi = '♪' if entry.get('midi_file') else ' '
            date_str = date[:16].replace('T', ' ') if date else ''
            display = f"{fav} {midi}  {name}   ·   {dur:.1f}s   ·   {date_str}"
            self.list_widget.addItem(display)
            self.list_widget.item(self.list_widget.count() - 1).setData(
                QtCore.Qt.ItemDataRole.UserRole, idx)

    def get_selected_index(self):
        row = self.list_widget.currentRow()
        return None if row < 0 else self.list_widget.item(row).data(
            QtCore.Qt.ItemDataRole.UserRole)

    def _on_item_double_clicked(self, item):
        idx = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if idx is None:
            return
        entry = self.bot.recordings_index[idx]
        json_path = os.path.join("recordings", entry['json_file'])
        if not os.path.exists(json_path):
            return
        if self.bot.load_recording(json_path):
            self.bot.start_playback()
            self.accept()

    def preview_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        if self.bot.is_playback:
            self.bot.stop_playback()
            time.sleep(0.1)
        entry = self.bot.recordings_index[idx]
        json_path = os.path.join("recordings", entry['json_file'])
        if not os.path.exists(json_path):
            return
        self.bot.preview_recording(json_path, seconds=5.0)

    def open_editor(self):
        RecordingEditorDialog(self.bot, self).exec()
        self.refresh_list()

    def open_recordings_folder(self):
        path = os.path.abspath("recordings")
        os.makedirs(path, exist_ok=True)
        try:
            os.startfile(path)
        except Exception:
            pass

    def rename_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        entry = self.bot.recordings_index[idx]
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, tr('recordings.rename'), tr('songs.new_name'),
            text=entry.get('name', ''))
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        existing = {e.get('name', '') for i, e in enumerate(self.bot.recordings_index)
                    if i != idx}
        if new_name in existing:
            c = 2
            while f"{new_name} ({c})" in existing:
                c += 1
            new_name = f"{new_name} ({c})"
        entry['name'] = new_name
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
            self, tr('ui.confirm'),
            tr('recordings.confirm_delete', name=entry.get('name')),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
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
        to_delete = [i for i, entry in enumerate(self.bot.recordings_index)
                     if not entry.get('favorite', False)]
        if not to_delete:
            return
        reply = QtWidgets.QMessageBox.question(
            self, tr('ui.confirm'),
            tr('recordings.confirm_clean', n=len(to_delete)),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
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

    def export_recordings_zip(self):
        downloads = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads):
            downloads = os.getcwd()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr('recordings.export_zip'),
            os.path.join(downloads, "AstraKeys_recordings.zip"), tr('file.zip'))
        if not file_path:
            return
        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(RECORDINGS_INDEX):
                    zf.write(RECORDINGS_INDEX, RECORDINGS_INDEX)
                if os.path.isdir("recordings"):
                    for fn in sorted(os.listdir("recordings")):
                        full = os.path.join("recordings", fn)
                        if os.path.isfile(full):
                            zf.write(full, f"recordings/{fn}")
            QtWidgets.QMessageBox.information(self, tr('ui.done'), file_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr('ui.error'), str(e))

    def import_recordings_zip(self):
        downloads = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads):
            downloads = os.getcwd()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, tr('recordings.import_zip'), downloads, tr('file.zip'))
        if not file_path:
            return
        try:
            os.makedirs("recordings", exist_ok=True)
            base = os.path.abspath(".")
            incoming_index = None
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                if RECORDINGS_INDEX in names:
                    with zf.open(RECORDINGS_INDEX) as f:
                        incoming_index = json.loads(f.read().decode('utf-8'))
                for member in names:
                    if member.endswith('/'):
                        continue
                    full = os.path.abspath(os.path.join(base, member))
                    if not (full == base or full.startswith(base + os.sep)):
                        continue
                    if member == RECORDINGS_INDEX:
                        continue
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with zf.open(member) as src, open(full, 'wb') as dst:
                        dst.write(src.read())
            if incoming_index is None:
                return
            existing_names = {e.get('name', '') for e in self.bot.recordings_index}
            added = 0
            for entry in incoming_index:
                json_file = entry.get('json_file')
                if not json_file or not os.path.exists(
                        os.path.join("recordings", json_file)):
                    continue
                desired = entry.get('name', 'Untitled')
                new_name = desired
                c = 2
                while new_name in existing_names:
                    new_name = f"{desired} ({c})"
                    c += 1
                entry['name'] = new_name
                existing_names.add(new_name)
                self.bot.recordings_index.append(entry)
                added += 1
            self.bot.save_recordings_index()
            self.refresh_list()
            QtWidgets.QMessageBox.information(
                self, tr('ui.done'), tr('recordings.import_ok', n=added))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr('ui.error'), str(e))


# ═══════════════════════════════════════════════════════════════════
#                       RECORDING EDITOR
# ═══════════════════════════════════════════════════════════════════

class RecordingEditorDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('editor.title'))
        self.setMinimumSize(640, 520)
        self._entries = list(self.bot.recordings_index)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._trim_tab(), tr('editor.trim'))
        tabs.addTab(self._concat_tab(), tr('editor.concat'))
        layout.addWidget(tabs)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText(tr('ui.close'))
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _trim_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.addWidget(QtWidgets.QLabel(tr('editor.select')))
        self.trim_combo = QtWidgets.QComboBox()
        self._fill_combo(self.trim_combo)
        self.trim_combo.currentIndexChanged.connect(self._on_trim_changed)
        v.addWidget(self.trim_combo)
        self.trim_info = QtWidgets.QLabel("—")
        v.addWidget(self.trim_info)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(tr('editor.start')))
        self.trim_start = QtWidgets.QDoubleSpinBox()
        self.trim_start.setRange(0.0, 99999.0)
        self.trim_start.setDecimals(2)
        row.addWidget(self.trim_start, 1)
        row.addWidget(QtWidgets.QLabel(tr('editor.end')))
        self.trim_end = QtWidgets.QDoubleSpinBox()
        self.trim_end.setRange(0.0, 99999.0)
        self.trim_end.setDecimals(2)
        row.addWidget(self.trim_end, 1)
        v.addLayout(row)
        b1 = HoverButton(tr('editor.preview'))
        b1.clicked.connect(self._preview_trimmed)
        v.addWidget(b1)
        b2 = HoverButton(tr('editor.save_new'))
        b2.setProperty("role", "primary")
        b2.clicked.connect(self._save_trimmed)
        v.addWidget(b2)
        v.addStretch()
        self._on_trim_changed(0)
        return w

    def _concat_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.addWidget(QtWidgets.QLabel(tr('editor.first')))
        self.cat_combo_a = QtWidgets.QComboBox()
        self._fill_combo(self.cat_combo_a)
        v.addWidget(self.cat_combo_a)
        v.addWidget(QtWidgets.QLabel(tr('editor.second')))
        self.cat_combo_b = QtWidgets.QComboBox()
        self._fill_combo(self.cat_combo_b)
        v.addWidget(self.cat_combo_b)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(tr('editor.gap')))
        self.cat_gap = QtWidgets.QDoubleSpinBox()
        self.cat_gap.setRange(0.0, 30.0)
        self.cat_gap.setValue(0.3)
        row.addWidget(self.cat_gap, 1)
        v.addLayout(row)
        b = HoverButton(tr('editor.concat_btn'))
        b.setProperty("role", "primary")
        b.clicked.connect(self._save_concatenated)
        v.addWidget(b)
        v.addStretch()
        return w

    def _fill_combo(self, combo):
        combo.clear()
        for e in self._entries:
            combo.addItem(f"{e.get('name', '?')}  ·  {e.get('duration', 0):.1f}s",
                          e.get('json_file', ''))

    def _load_events(self, json_file):
        path = os.path.join("recordings", json_file)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            events = data.get('events', [])
            if events and not any(ev.get('action') == 'press' for ev in events):
                reconstructed = []
                for ev in events:
                    if ev.get('action') != 'release':
                        continue
                    dur = max(0.05, ev.get('duration', 0.2))
                    press_time = max(0.0, ev['time'] - dur)
                    reconstructed.append({'time': press_time, 'key': ev['key'],
                                          'action': 'press'})
                    reconstructed.append({'time': ev['time'], 'key': ev['key'],
                                          'action': 'release'})
                events = sorted(reconstructed, key=lambda e: e['time'])
            return events
        except Exception as e:
            logger.error(f"Editor load error: {e}")
            return None

    def _on_trim_changed(self, idx):
        if idx < 0 or idx >= len(self._entries):
            return
        dur = self._entries[idx].get('duration', 0)
        self.trim_info.setText(f"{tr('editor.duration')}: {dur:.2f}s")
        self.trim_start.setRange(0.0, max(0.0, dur))
        self.trim_end.setRange(0.0, max(0.0, dur))
        self.trim_start.setValue(0.0)
        self.trim_end.setValue(dur)

    def _slice_events(self, events, start, end):
        out = []
        pending_before = {}
        for ev in events:
            if ev['time'] < start:
                if ev['action'] == 'press':
                    pending_before[ev['key']] = True
                elif ev['action'] == 'release':
                    pending_before.pop(ev['key'], None)
            else:
                break
        for key in pending_before.keys():
            out.append({"time": 0.0, "key": key, "action": "press"})
        pending = dict(pending_before)
        for ev in events:
            t = ev['time']
            if t < start:
                continue
            if t > end:
                break
            new_ev = dict(ev)
            new_ev['time'] = round(t - start, 3)
            out.append(new_ev)
            if ev['action'] == 'press':
                pending[ev['key']] = True
            elif ev['action'] == 'release':
                pending.pop(ev['key'], None)
        for key in list(pending.keys()):
            out.append({"time": round(end - start, 3), "key": key,
                        "action": "release"})
        out.sort(key=lambda e: e['time'])
        return out

    def _preview_trimmed(self):
        idx = self.trim_combo.currentIndex()
        if idx < 0:
            return
        events = self._load_events(self._entries[idx]['json_file'])
        if not events:
            return
        start, end = self.trim_start.value(), self.trim_end.value()
        if end <= start:
            return
        sliced = self._slice_events(events, start, end)
        if not sliced:
            return
        if self.bot.is_playback:
            self.bot.stop_playback()
            time.sleep(0.1)
        self.bot.playback_events = sliced
        self.bot._preview_active = True
        self.bot.start_playback(limit_seconds=min(5.0, end - start))

    def _save_trimmed(self):
        idx = self.trim_combo.currentIndex()
        if idx < 0:
            return
        entry = self._entries[idx]
        events = self._load_events(entry['json_file'])
        if not events:
            return
        start, end = self.trim_start.value(), self.trim_end.value()
        if end <= start:
            return
        sliced = self._slice_events(events, start, end)
        if not sliced:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, tr('ui.save'), tr('songs.new_name'),
            text=f"{entry.get('name', 'Rec')}")
        if not ok or not name.strip():
            return
        saved = self.bot.save_recording_events(name.strip(), sliced)
        if saved:
            self._entries = list(self.bot.recordings_index)
            self._fill_combo(self.trim_combo)
            self._fill_combo(self.cat_combo_a)
            self._fill_combo(self.cat_combo_b)

    def _save_concatenated(self):
        ia, ib = self.cat_combo_a.currentIndex(), self.cat_combo_b.currentIndex()
        if ia < 0 or ib < 0:
            return
        ev_a = self._load_events(self._entries[ia]['json_file'])
        ev_b = self._load_events(self._entries[ib]['json_file'])
        if not ev_a or not ev_b:
            return

        def _close_pending(events):
            pending = {}
            for ev in events:
                if ev['action'] == 'press':
                    pending[ev['key']] = True
                elif ev['action'] == 'release':
                    pending.pop(ev['key'], None)
            if pending:
                last_t = max(ev['time'] for ev in events)
                extra = [{'time': round(last_t + 0.05, 3), 'key': k,
                          'action': 'release'} for k in pending.keys()]
                events = events + extra
            return sorted(events, key=lambda e: e['time'])

        ev_a = _close_pending(ev_a)
        ev_b = _close_pending(ev_b)
        offset = max(ev['time'] for ev in ev_a) + self.cat_gap.value()
        merged = list(ev_a)
        for ev in ev_b:
            new_ev = dict(ev)
            new_ev['time'] = round(ev['time'] + offset, 3)
            merged.append(new_ev)
        merged.sort(key=lambda e: e['time'])
        name, ok = QtWidgets.QInputDialog.getText(
            self, tr('ui.save'), tr('songs.new_name'),
            text=f"{self._entries[ia].get('name', 'A')} + "
                 f"{self._entries[ib].get('name', 'B')}")
        if not ok or not name.strip():
            return
        saved = self.bot.save_recording_events(name.strip(), merged)
        if saved:
            self._entries = list(self.bot.recordings_index)
            self._fill_combo(self.trim_combo)
            self._fill_combo(self.cat_combo_a)
            self._fill_combo(self.cat_combo_b)


# ═══════════════════════════════════════════════════════════════════
#                           LOG VIEWER
# ═══════════════════════════════════════════════════════════════════

class LogViewerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('log.title'))
        self.setMinimumSize(700, 500)
        layout = QtWidgets.QVBoxLayout(self)
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, encoding='utf-8') as f:
                    self.text_edit.setPlainText(''.join(f.readlines()[-1000:]))
        except Exception:
            pass
        layout.addWidget(self.text_edit)
        row = QtWidgets.QHBoxLayout()
        cp = HoverButton(tr('log.copy'))
        cp.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(
            self.text_edit.toPlainText()))
        row.addWidget(cp)
        cl = HoverButton(tr('log.close'))
        cl.clicked.connect(self.accept)
        row.addWidget(cl)
        layout.addLayout(row)


# ═══════════════════════════════════════════════════════════════════
#                            MAIN GUI
# ═══════════════════════════════════════════════════════════════════

class BotGUI(QtWidgets.QWidget):
    _update_requested = QtCore.pyqtSignal()

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._i18n_widgets = {}
        self._animations = []
        self._rec_pulse_anim = None
        self._rec_pulse_effect = None
        self._last_status = None
        self._last_recording = False
        self._last_playback = False
        self._theme_anim = None

        self._update_requested.connect(
            self.on_state_changed, QtCore.Qt.ConnectionType.QueuedConnection)
        self.bot.set_gui_update_callback(self._update_requested.emit)

        self.setWindowTitle(tr('app.title'))
        self.setWindowOpacity(0.0)
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() // 2 - 450, screen.height() // 2 - 390, 900, 780)
        self.load_window_state()

        self._build()

        self.overlay_window = NoteOverlayWindow(bot=self.bot, parent_gui=self)
        self.bot.set_overlay_window(self.overlay_window)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(150)

        self.load_playlist()
        self._refresh_midi_ports()
        if self.bot.midi_out_enabled and self.bot.midi_port_name:
            ok, err = self.bot.open_midi_port(self.bot.midi_port_name)
            if ok:
                self.midi_status_label.setText(
                    tr('midi.connected', name=self.bot.midi_port_name))
            else:
                self.bot.midi_out_enabled = False
                self.midi_enable_check.setChecked(False)
                self.midi_status_label.setText(tr('midi.error'))

        QtCore.QTimer.singleShot(80, self._fade_in)
        QtCore.QTimer.singleShot(2000, self._auto_check_updates_if_enabled)

    # ─── i18n helpers ───
    def _lbl(self, key, parent_layout=None, min_width=None, obj_name=None):
        lbl = QtWidgets.QLabel(tr(key))
        if min_width is not None:
            lbl.setMinimumWidth(min_width)
        if obj_name:
            lbl.setObjectName(obj_name)
        self._i18n_widgets.setdefault(key, []).append(('text', lbl))
        if parent_layout is not None:
            parent_layout.addWidget(lbl)
        return lbl

    def _tr_btn(self, key, parent_layout=None):
        b = HoverButton(tr(key))
        self._i18n_widgets.setdefault(key, []).append(('text', b))
        if parent_layout is not None:
            parent_layout.addWidget(b)
        return b

    def _tr_chk(self, key, parent_layout=None):
        c = QtWidgets.QCheckBox(tr(key))
        self._i18n_widgets.setdefault(key, []).append(('text', c))
        if parent_layout is not None:
            parent_layout.addWidget(c)
        return c

    def _icon_btn(self, text, key, size=32):
        b = HoverButton(text)
        b.setProperty("role", "icon")
        b.setFixedSize(size, size)
        b.setToolTip(tr(key))
        self._i18n_widgets.setdefault(key, []).append(('tooltip', b))
        return b

    # ─── animations ───
    def _keep_anim(self, anim, on_finished=None):
        self._animations.append(anim)

        def _cleanup():
            try:
                self._animations.remove(anim)
            except ValueError:
                pass
            if on_finished:
                try:
                    on_finished()
                except Exception:
                    pass

        anim.finished.connect(_cleanup)
        anim.start()

    def _fade_in(self):
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(420)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._keep_anim(anim)

    def _animate_theme(self, target_key, duration=260):
        """Smoothly interpolate every theme color, ~60 FPS."""
        global _current_theme_key
        if self._theme_anim is not None:
            try:
                self._theme_anim.stop()
            except Exception:
                pass

        from_theme = dict(get_theme())
        to_theme = dict(THEMES[target_key])
        _current_theme_key = target_key

        color_keys = [k for k, v in to_theme.items()
                      if isinstance(v, str) and (v.startswith('#') or v.startswith('rgb'))]
        from_parsed = {k: _parse_color(from_theme.get(k, to_theme[k])) for k in color_keys}
        to_parsed = {k: _parse_color(to_theme[k]) for k in color_keys}

        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        anim = QtCore.QVariantAnimation()
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(duration)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        def tick(t):
            merged = dict(to_theme)
            for k in color_keys:
                merged[k] = _rgba_to_str(_lerp_rgba(from_parsed[k], to_parsed[k], t))
            app.setStyleSheet(build_qss(merged))
            if self.overlay_window:
                ov = self.overlay_window
                ov.bg_color = merged.get('overlay_bg', ov.bg_color)
                ov.text_color = merged.get('overlay_text', ov.text_color)
                ov.accent_color = merged.get('overlay_accent', ov.accent_color)
                ov.highlight_bg = merged.get('overlay_highlight', ov.highlight_bg)
                ov.apply_settings()

        def done():
            apply_theme(app)
            if self.overlay_window:
                self.overlay_window._apply_theme_from_current()
                self.overlay_window.apply_settings()
            self.bot.save_app_settings()
            self._theme_anim = None

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._theme_anim = anim
        anim.start()

    # ─── build ───
    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # title bar
        tb = QtWidgets.QFrame()
        tb.setObjectName("titlebar")
        tb.setFixedHeight(46)
        tbl = QtWidgets.QHBoxLayout(tb)
        tbl.setContentsMargins(18, 0, 14, 0)
        tbl.setSpacing(8)

        title = QtWidgets.QLabel("AstraKeys")
        title.setObjectName("app_title")
        tbl.addWidget(title)
        tbl.addStretch()

        self.theme_btn = self._icon_btn("🎨", 'titlebar.theme_tooltip')
        self.theme_btn.clicked.connect(self._cycle_theme)
        tbl.addWidget(self.theme_btn)

        self.lang_combo = QtWidgets.QComboBox()
        for code in SUPPORTED_LANGS:
            self.lang_combo.addItem(LANG_LABELS[code], code)
        self.lang_combo.setCurrentIndex(SUPPORTED_LANGS.index(tr_obj.lang))
        self.lang_combo.setFixedWidth(120)
        self.lang_combo.currentIndexChanged.connect(self._change_lang)
        tbl.addWidget(self.lang_combo)

        self.log_btn = self._icon_btn("📋", 'titlebar.log_tooltip')
        self.log_btn.clicked.connect(lambda: LogViewerDialog(self).exec())
        tbl.addWidget(self.log_btn)

        self.about_btn = self._icon_btn("ⓘ", 'titlebar.about_tooltip')
        self.about_btn.clicked.connect(self.show_about)
        tbl.addWidget(self.about_btn)

        root.addWidget(tb)

        accent = QtWidgets.QFrame()
        accent.setObjectName("accent_line")
        accent.setFixedHeight(1)
        root.addWidget(accent)

        # body
        body = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(body)
        bl.setContentsMargins(16, 14, 16, 14)
        bl.setSpacing(16)

        # left — playlist
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(8)
        self._lbl('playlist.section', left, obj_name='section_label')

        self.song_list = QtWidgets.QListWidget()
        self.song_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.song_list.model().rowsMoved.connect(self.handle_rows_moved)
        left.addWidget(self.song_list, 1)

        pl_btns = QtWidgets.QHBoxLayout()
        pl_btns.setSpacing(4)
        for sym, key, cb in [
            ("＋", 'playlist.add_tooltip', self.add_song),
            ("🗑", 'playlist.remove_tooltip', self.remove_song),
            ("✏", 'playlist.rename_tooltip', self.rename_song),
            ("💾", 'playlist.save_tooltip', self.save_playlist),
            ("📂", 'playlist.load_tooltip', self.load_playlist_dialog),
        ]:
            b = self._icon_btn(sym, key)
            b.clicked.connect(cb)
            pl_btns.addWidget(b)
        pl_btns.addStretch()
        left.addLayout(pl_btns)

        self.manage_btn = self._tr_btn('playlist.manage_recordings', left)
        self.manage_btn.clicked.connect(self.open_recordings_manager)

        self.overlay_btn = self._tr_btn('playlist.overlay', left)
        self.overlay_btn.clicked.connect(self.toggle_overlay)

        bl.addLayout(left, 3)

        # right — player
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(8)
        self._lbl('player.section', right, obj_name='section_label')

        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText(tr('player.input_placeholder'))
        self.song_input.setFixedHeight(60)
        self._i18n_widgets.setdefault('player.input_placeholder', []).append(
            ('placeholder', self.song_input))
        right.addWidget(self.song_input)

        self.song_display = QtWidgets.QTextEdit()
        self.song_display.setObjectName("song_display")
        self.song_display.setReadOnly(True)
        self.song_display.setFixedHeight(76)
        right.addWidget(self.song_display)

        # transport (icon + text for main, icon-only for secondary)
        transport = QtWidgets.QHBoxLayout()
        transport.setSpacing(6)

        self.play_btn = HoverButton("▶")
        self.play_btn.setProperty("role", "primary")
        self.play_btn.setFixedHeight(36)
        self.play_btn.setMinimumWidth(100)
        self.play_btn.setToolTip(tr('player.start_tooltip'))
        self._i18n_widgets.setdefault('player.start_tooltip', []).append(
            ('tooltip', self.play_btn))
        self.play_btn.clicked.connect(self.toggle_play)
        transport.addWidget(self.play_btn)

        self.rec_btn = QtWidgets.QPushButton("●")  # plain; has its own pulse effect
        self.rec_btn.setProperty("role", "icon")
        self.rec_btn.setFixedHeight(36)
        self.rec_btn.setMinimumWidth(110)
        self.rec_btn.setToolTip(tr('player.record_tooltip'))
        self._i18n_widgets.setdefault('player.record_tooltip', []).append(
            ('tooltip', self.rec_btn))
        self.rec_btn.clicked.connect(self.toggle_recording)
        transport.addWidget(self.rec_btn)

        self.playback_btn = HoverButton("🎵")
        self.playback_btn.setProperty("role", "icon")
        self.playback_btn.setFixedSize(40, 36)
        self.playback_btn.setToolTip(tr('player.playback_tooltip'))
        self._i18n_widgets.setdefault('player.playback_tooltip', []).append(
            ('tooltip', self.playback_btn))
        self.playback_btn.clicked.connect(self.load_and_play)
        transport.addWidget(self.playback_btn)

        self.stop_btn = HoverButton("■")
        self.stop_btn.setProperty("role", "icon")
        self.stop_btn.setFixedSize(40, 36)
        self.stop_btn.setToolTip(tr('player.stop_playback_tooltip'))
        self._i18n_widgets.setdefault('player.stop_playback_tooltip', []).append(
            ('tooltip', self.stop_btn))
        self.stop_btn.clicked.connect(self.bot.stop_playback)
        self.stop_btn.hide()
        transport.addWidget(self.stop_btn)

        self.pause_btn = HoverButton("⏸")
        self.pause_btn.setProperty("role", "icon")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setMinimumWidth(110)
        self.pause_btn.setToolTip(tr('player.pause_tooltip'))
        self._i18n_widgets.setdefault('player.pause_tooltip', []).append(
            ('tooltip', self.pause_btn))
        self.pause_btn.clicked.connect(self.bot.toggle_playback_pause)
        self.pause_btn.hide()
        transport.addWidget(self.pause_btn)

        self.next_song_btn = self._icon_btn("⏭", 'player.next_song_tooltip', size=36)
        self.next_song_btn.clicked.connect(lambda: (self.bot.next_song(), self.refresh()))
        transport.addWidget(self.next_song_btn)

        self.next_mode_btn = self._icon_btn("🔀", 'player.next_mode_tooltip', size=36)
        self.next_mode_btn.clicked.connect(self.next_mode)
        transport.addWidget(self.next_mode_btn)

        transport.addStretch()
        right.addLayout(transport)

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._settings_tab(), tr('settings.tab_params'))
        self.tabs.addTab(self._midi_tab(), tr('settings.tab_midi'))
        right.addWidget(self.tabs, 1)

        bl.addLayout(right, 5)
        root.addWidget(body, 1)

        # status bar
        sb = QtWidgets.QFrame()
        sb.setFixedHeight(26)
        sbl = QtWidgets.QHBoxLayout(sb)
        sbl.setContentsMargins(18, 0, 18, 0)
        self.status_label = QtWidgets.QLabel(tr('status.idle'))
        self.status_label.setObjectName("status_accent")
        sbl.addWidget(self.status_label)
        self.mode_lbl = QtWidgets.QLabel("")
        self.mode_lbl.setObjectName("status_normal")
        sbl.addWidget(self.mode_lbl)
        sbl.addStretch()
        self.pos_lbl = QtWidgets.QLabel("0/0")
        self.pos_lbl.setObjectName("status_pos")
        sbl.addWidget(self.pos_lbl)
        root.addWidget(sb)

        self.hint = self._lbl('help.text', obj_name='status_normal')
        self.hint.setContentsMargins(18, 3, 18, 8)
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

    def _settings_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)

        row = QtWidgets.QHBoxLayout()
        self._lbl('settings.mode_label', row)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([tr('settings.mode1'), tr('settings.mode2')])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        row.addWidget(self.mode_combo, 1)
        v.addLayout(row)

        self.min_slider, self.min_lbl = self._slider_row(
            v, 'settings.min_delay', 0, 200, self.bot.min_note_delay,
            self.min_delay_changed)
        self.max_slider, self.max_lbl = self._slider_row(
            v, 'settings.max_delay', 0, 500, self.bot.max_note_delay,
            self.max_delay_changed)
        self.start_slider, self.start_lbl = self._slider_row(
            v, 'settings.start_delay', 0, 100,
            int(self.bot.start_delay * 1000), self.start_delay_changed)

        self.audio_enable_check = self._tr_chk('settings.speaker_enable', v)
        self.audio_enable_check.setChecked(self.bot.audio_enabled)
        self.audio_enable_check.stateChanged.connect(self._on_audio_toggle)

        auto_hold_row = QtWidgets.QHBoxLayout()
        self._lbl('audio.auto_hold', auto_hold_row)
        self.auto_hold_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.auto_hold_slider.setMinimum(20)
        self.auto_hold_slider.setMaximum(1000)
        self.auto_hold_slider.setValue(self.bot.auto_hold_ms)
        self.auto_hold_slider.valueChanged.connect(self._auto_hold_changed)
        auto_hold_row.addWidget(self.auto_hold_slider, 1)
        self.auto_hold_label = QtWidgets.QLabel(str(self.bot.auto_hold_ms))
        self.auto_hold_label.setMinimumWidth(40)
        auto_hold_row.addWidget(self.auto_hold_label)
        v.addLayout(auto_hold_row)

        self.auto_play_check = self._tr_chk('audio.auto_play', v)
        self.auto_play_check.setChecked(self.bot.auto_play_no_pedal)
        self.auto_play_check.stateChanged.connect(self._on_auto_play_toggled)

        self.auto_update_check = self._tr_chk('settings.auto_update', v)
        self.auto_update_check.setChecked(self.bot.check_updates_on_start)
        self.auto_update_check.stateChanged.connect(self._on_auto_update_toggled)

        row2 = QtWidgets.QHBoxLayout()
        u = self._tr_btn('settings.update_btn', row2)
        u.clicked.connect(self.gui_update_client)
        p = self._tr_btn('settings.pedal_btn', row2)
        p.clicked.connect(self.open_pedal_settings)
        row2.addStretch()
        v.addLayout(row2)

        self.update_progress = QtWidgets.QProgressBar()
        self.update_progress.setVisible(False)
        v.addWidget(self.update_progress)
        v.addStretch()
        return w

    def _midi_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)

        self.midi_enable_check = self._tr_chk('midi.enable', v)
        self.midi_enable_check.setChecked(self.bot.midi_out_enabled)
        self.midi_enable_check.stateChanged.connect(self._on_midi_toggle)

        row = QtWidgets.QHBoxLayout()
        self._lbl('midi.port', row)
        self.midi_port_combo = QtWidgets.QComboBox()
        row.addWidget(self.midi_port_combo, 1)
        ref = self._icon_btn("⟳", 'midi.refresh_tooltip')
        ref.clicked.connect(self._refresh_midi_ports)
        row.addWidget(ref)
        v.addLayout(row)

        test = self._tr_btn('midi.test', v)
        test.clicked.connect(self._midi_test)

        self.midi_status_label = QtWidgets.QLabel(tr('midi.no_ports'))
        self.midi_status_label.setObjectName("status_normal")
        v.addWidget(self.midi_status_label)

        hint = self._lbl('midi.hint', v, obj_name='status_normal')
        hint.setWordWrap(True)

        v.addStretch()
        return w

    def _slider_row(self, parent, key, lo, hi, val, cb):
        row = QtWidgets.QHBoxLayout()
        self._lbl(key, row, min_width=180)
        s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.valueChanged.connect(cb)
        row.addWidget(s, 1)
        vl = QtWidgets.QLabel(str(val))
        vl.setMinimumWidth(40)
        vl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        row.addWidget(vl)
        parent.addLayout(row)
        return s, vl

    # ─── retranslation ───
    def _retranslate_ui(self):
        for key, items in self._i18n_widgets.items():
            text = tr(key)
            for kind, widget in items:
                try:
                    if kind == 'text':
                        widget.setText(text)
                    elif kind == 'tooltip':
                        widget.setToolTip(text)
                    elif kind == 'placeholder':
                        widget.setPlaceholderText(text)
                except Exception:
                    pass
        self.setWindowTitle(tr('app.title'))

        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems([tr('settings.mode1'), tr('settings.mode2')])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.blockSignals(False)

        self.tabs.setTabText(0, tr('settings.tab_params'))
        self.tabs.setTabText(1, tr('settings.tab_midi'))

        # re-populate MIDI ports with translated placeholder
        self._refresh_midi_ports()
        if hasattr(self, 'midi_status_label'):
            if self.bot.midi_out_enabled and self.bot.midi_port_name:
                self.midi_status_label.setText(
                    tr('midi.connected', name=self.bot.midi_port_name))
            else:
                self.midi_status_label.setText(tr('midi.no_ports'))

        if hasattr(self, 'overlay_window') and self.overlay_window:
            self.overlay_window.refresh_tooltips()

        self.refresh()

    # ─── actions ───
    def _change_lang(self, idx):
        code = self.lang_combo.itemData(idx)
        if not code:
            return
        tr_obj.set_lang(code)
        self.bot.save_app_settings()
        self._retranslate_ui()

    def _cycle_theme(self):
        keys = list(THEMES.keys())
        i = keys.index(_current_theme_key)
        next_key = keys[(i + 1) % len(keys)]
        self._animate_theme(next_key, duration=260)

    def toggle_play(self):
        self.bot.playing = not self.bot.playing
        if self.bot.playing and not self.bot.is_playback:
            activate_roblox_window()

    def toggle_recording(self):
        if self.bot.is_recording:
            name, ok = QtWidgets.QInputDialog.getText(
                self, tr('recording.name_title'), tr('recording.name_label'),
                text=self.bot.recording_song_name)
            if ok:
                self.bot.stop_recording(custom_name=name.strip() if name.strip() else None)
            else:
                self.bot.stop_recording()
        else:
            self.bot.start_recording()

    def load_and_play(self):
        RecordingsManagerDialog(self.bot, self).exec()

    def toggle_overlay(self):
        if self.overlay_window.isVisible():
            self.overlay_window.hide_with_fade()
        else:
            self.overlay_window.show_with_fade()

    def next_mode(self):
        self.bot.mode = 2 if self.bot.mode == 1 else 1
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.bot.save_app_settings()
        self.refresh()

    def mode_changed(self, i):
        self.bot.mode = i + 1
        self.bot.save_app_settings()

    def min_delay_changed(self, v):
        self.bot.min_note_delay = v
        self.min_lbl.setText(str(v))
        if v > self.bot.max_note_delay:
            self.bot.max_note_delay = v
            self.max_slider.setValue(v)
            self.max_lbl.setText(str(v))

    def max_delay_changed(self, v):
        self.bot.max_note_delay = v
        self.max_lbl.setText(str(v))
        if v < self.bot.min_note_delay:
            self.bot.min_note_delay = v
            self.min_slider.setValue(v)
            self.min_lbl.setText(str(v))

    def start_delay_changed(self, v):
        self.bot.start_delay = v / 1000.0
        self.start_lbl.setText(str(v))

    def _on_audio_toggle(self, state):
        e = bool(state)
        if e and (not HAS_AUDIO or not self.bot.audio_player):
            QtWidgets.QMessageBox.warning(
                self, tr('audio.warn_title'), tr('audio.warn_text'))
            self.audio_enable_check.setChecked(False)
            return
        self.bot.audio_enabled = e
        self.bot.save_app_settings()

    def _on_auto_play_toggled(self, state):
        self.bot.auto_play_no_pedal = bool(state)
        self.bot.save_app_settings()

    def _auto_hold_changed(self, v):
        self.bot.auto_hold_ms = int(v)
        self.auto_hold_label.setText(str(v))
        self.bot.save_app_settings()

    def _on_auto_update_toggled(self, state):
        self.bot.check_updates_on_start = bool(state)
        self.bot.save_app_settings()

    def _auto_check_updates_if_enabled(self):
        if (self.bot.check_updates_on_start and not self.bot.playing
                and not self.bot.is_playback):
            self.gui_update_client()

    def open_recordings_manager(self):
        RecordingsManagerDialog(self.bot, self).exec()

    def open_pedal_settings(self):
        PedalSettingsDialog(self.bot, self).exec()

    # ─── playlist ───
    def add_song(self):
        text = self.song_input.toPlainText().strip()
        if not text:
            return
        default = tr('songs.default_name', n=len(self.bot.playlist) + 1)
        name, ok = QtWidgets.QInputDialog.getText(
            self, tr('songs.name_title'), tr('songs.name_label'), text=default)
        if not ok or not name.strip():
            name = default
        sanitized = self.bot.sanitize_song(text)
        if not sanitized.strip():
            QtWidgets.QMessageBox.warning(self, tr('ui.error'), tr('recording.empty'))
            return
        was_empty = len(self.bot.playlist) == 0
        self.bot.playlist.append((name.strip(), sanitized))
        item = QtWidgets.QListWidgetItem(name.strip())
        item.setData(QtCore.Qt.ItemDataRole.UserRole, sanitized)
        self.song_list.addItem(item)
        if was_empty:
            self.bot.song_index = 0
            self.bot.song_name, self.bot.song = self.bot.playlist[0]
            self.song_list.setCurrentRow(0)
        self.song_input.clear()

    def remove_song(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            reply = QtWidgets.QMessageBox.question(
                self, tr('songs.delete_title'),
                tr('songs.delete_text', name=self.bot.playlist[row][0]),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.bot.playlist.pop(row)
                self.song_list.takeItem(row)
                if not self.bot.playlist:
                    self.bot.song_index = 0
                    self.bot.song_name = ""
                    self.bot.song = ""
                    self.song_display.clear()
                else:
                    if self.bot.song_index >= len(self.bot.playlist):
                        self.bot.song_index = len(self.bot.playlist) - 1
                    self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
                    self.song_list.setCurrentRow(self.bot.song_index)

    def rename_song(self):
        row = self.song_list.currentRow()
        if 0 <= row < len(self.bot.playlist):
            name, content = self.bot.playlist[row]
            new_name, ok = QtWidgets.QInputDialog.getText(
                self, tr('recordings.rename'), tr('songs.new_name'), text=name)
            if ok and new_name.strip():
                self.bot.playlist[row] = (new_name.strip(), content)
                if row == self.bot.song_index:
                    self.bot.song_name = new_name.strip()
                item = self.song_list.item(row)
                if item:
                    item.setText(new_name.strip())
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, content)

    def save_playlist(self):
        try:
            data = [{"name": n, "content": c} for n, c in self.bot.playlist]
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, tr('ui.done'), PLAYLIST_FILE)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr('ui.error'), str(e))

    def load_playlist(self):
        try:
            if os.path.exists(PLAYLIST_FILE):
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.bot.playlist = [(d['name'], self.bot.sanitize_song(d['content']))
                                     for d in data]
                self.bot.song_index = 0
                if self.bot.playlist:
                    self.bot.song_name, self.bot.song = self.bot.playlist[0]
                else:
                    self.bot.song_name = ""
                    self.bot.song = ""
                self.refresh_list()
        except Exception as e:
            logger.error(f"Load playlist error: {e}")

    def load_playlist_dialog(self):
        self.load_playlist()
        self.refresh_list()

    def refresh_list(self):
        self.song_list.blockSignals(True)
        self.song_list.clear()
        for name, content in self.bot.playlist:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, content)
            self.song_list.addItem(item)
        if self.bot.playlist:
            self.song_list.setCurrentRow(self.bot.song_index)
        self.song_list.blockSignals(False)

    def handle_rows_moved(self, *args):
        QtCore.QTimer.singleShot(0, self._rebuild_playlist_from_list)

    def _rebuild_playlist_from_list(self):
        self.song_list.blockSignals(True)
        new_playlist = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            content = item.data(QtCore.Qt.ItemDataRole.UserRole) or ""
            new_playlist.append((item.text(), content))
        current_name = self.bot.song_name
        self.bot.playlist = new_playlist
        self.bot.song_index = 0
        for i, (name, _) in enumerate(self.bot.playlist):
            if name == current_name:
                self.bot.song_index = i
                break
        if self.bot.playlist:
            self.bot.song_name, self.bot.song = self.bot.playlist[self.bot.song_index]
        else:
            self.bot.song_name = ""
            self.bot.song = ""
        self.song_list.setCurrentRow(self.bot.song_index)
        self.song_list.blockSignals(False)

    # ─── refresh ───
    def refresh(self):
        if self.bot.is_recording:
            st = tr('status.recording')
        elif self.bot.is_playback and self.bot._preview_active:
            st = tr('status.preview')
        elif self.bot.is_playback:
            st = tr('status.playback')
        elif self.bot.playing:
            st = tr('status.playing')
        else:
            st = tr('status.idle')
        if self.bot.playback_paused:
            st += " ⏸"

        if st != self._last_status:
            self._last_status = st
            self._flash_status()
        self.status_label.setText(st)

        self.mode_lbl.setText(f"· {self.mode_combo.currentText()}")
        try:
            self.pos_lbl.setText(f"{self.bot.note_index}/{len(self.bot.song)}")
        except Exception:
            self.pos_lbl.setText("0/0")

        # transport text update (respects language + state)
        if self.bot.playing:
            self.play_btn.setText("⏸ " + tr('player.btn_pause'))
            self.play_btn.setToolTip(tr('player.pause_tooltip'))
        else:
            self.play_btn.setText("▶ " + tr('player.btn_play'))
            self.play_btn.setToolTip(tr('player.start_tooltip'))

        if self.bot.is_recording:
            self.rec_btn.setText("■ " + tr('player.btn_stop_rec'))
        else:
            self.rec_btn.setText("● " + tr('player.btn_record'))

        if self.bot.playback_paused:
            self.pause_btn.setText("▶ " + tr('player.btn_resume_playback'))
        else:
            self.pause_btn.setText("⏸ " + tr('player.btn_pause_playback'))

        # record pulse
        if self.bot.is_recording and not self._last_recording:
            self._start_record_pulse()
        elif not self.bot.is_recording and self._last_recording:
            self._stop_record_pulse()
        self._last_recording = self.bot.is_recording

        # playback controls
        self._last_playback = self.bot.is_playback
        if self.bot.is_playback:
            self.playback_btn.hide()
            self.stop_btn.show()
            self.pause_btn.show()
        else:
            self.playback_btn.show()
            self.stop_btn.hide()
            self.pause_btn.hide()

        self._update_song_display()
        if self.overlay_window and self.overlay_window.isVisible():
            self.overlay_window.update_metadata(
                self.bot.song_name, self.bot.progress,
                self.bot.playing, self.bot.is_playback)
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.setCurrentRow(self.bot.song_index)

    def _flash_status(self):
        try:
            eff = QtWidgets.QGraphicsOpacityEffect(self.status_label)
            self.status_label.setGraphicsEffect(eff)
            anim = QtCore.QPropertyAnimation(eff, b"opacity")
            anim.setDuration(420)
            anim.setKeyValueAt(0.0, 0.35)
            anim.setKeyValueAt(1.0, 1.0)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

            def _cleanup():
                try:
                    self.status_label.setGraphicsEffect(None)
                except Exception:
                    pass

            self._keep_anim(anim, on_finished=_cleanup)
        except Exception:
            pass

    def _start_record_pulse(self):
        if self._rec_pulse_anim is not None:
            return
        try:
            self._rec_pulse_effect = QtWidgets.QGraphicsOpacityEffect(self.rec_btn)
            self.rec_btn.setGraphicsEffect(self._rec_pulse_effect)
            anim = QtCore.QPropertyAnimation(self._rec_pulse_effect, b"opacity")
            anim.setDuration(900)
            anim.setKeyValueAt(0.0, 1.0)
            anim.setKeyValueAt(0.5, 0.4)
            anim.setKeyValueAt(1.0, 1.0)
            anim.setLoopCount(-1)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
            self._rec_pulse_anim = anim
            anim.start()
        except Exception:
            pass

    def _stop_record_pulse(self):
        try:
            if self._rec_pulse_anim is not None:
                self._rec_pulse_anim.stop()
                self._rec_pulse_anim = None
            self.rec_btn.setGraphicsEffect(None)
        except Exception:
            pass
        self._rec_pulse_effect = None

    def on_state_changed(self):
        self.refresh()

    def _update_song_display(self):
        if not self.bot.song:
            self.song_display.setPlainText("")
            return
        cpl, lines = 45, 3
        total = cpl * lines
        pos = self.bot.frozen_note_index if self.bot.freeze_note else self.bot.note_index
        t = get_theme()
        if pos >= len(self.bot.song):
            self.song_display.setPlainText(
                self.bot.song[max(0, len(self.bot.song) - total):])
            return
        start = max(0, pos - total // 3)
        disp = self.bot.song[start:start + total]
        ci = pos - start
        if 0 <= ci < len(disp):
            if ci < len(disp) - 1 and disp[ci] == '[':
                end = disp.find(']', ci + 1)
                if end != -1:
                    before = html.escape(disp[:ci])
                    chord = html.escape(disp[ci:end + 1])
                    after = html.escape(disp[end + 1:])
                    self.song_display.setHtml(
                        f'<span style="color:{t["text_muted"]};">{before}</span>'
                        f'<span style="background-color:{t["selection"]}; '
                        f'color:{t["accent_press"]}; font-weight:bold; '
                        f'padding:0 4px; border-radius:3px;">{chord}</span>'
                        f'<span style="color:{t["text_muted"]};">{after}</span>')
                    return
            before = html.escape(disp[:ci])
            cur = html.escape(disp[ci:ci + 1])
            after = html.escape(disp[ci + 1:])
            self.song_display.setHtml(
                f'<span style="color:{t["text_muted"]};">{before}</span>'
                f'<span style="background-color:{t["selection"]}; '
                f'color:{t["accent_press"]}; font-weight:bold; '
                f'padding:0 4px; border-radius:3px;">{cur}</span>'
                f'<span style="color:{t["text_muted"]};">{after}</span>')
        else:
            self.song_display.setPlainText(disp)

    def show_about(self):
        QtWidgets.QMessageBox.about(
            self, tr('app.about_title'),
            tr('app.about_text', version=CURRENT_VERSION))

    # ─── MIDI ───
    def _refresh_midi_ports(self):
        ports = self.bot.list_midi_ports()
        self.midi_port_combo.clear()
        if not ports:
            self.midi_port_combo.addItem(tr('midi.no_ports'))
            return
        for p in ports:
            self.midi_port_combo.addItem(p)
        saved = self.bot.midi_port_name
        if saved and saved in ports:
            self.midi_port_combo.setCurrentText(saved)

    def _on_midi_toggle(self, state):
        enabled = bool(state)
        if enabled:
            if not HAS_MIDI_OUT:
                QtWidgets.QMessageBox.warning(self, tr('midi.error'), tr('midi.no_lib'))
                self.midi_enable_check.setChecked(False)
                return
            port_name = self.midi_port_combo.currentText().strip()
            if not port_name or port_name.startswith("("):
                QtWidgets.QMessageBox.warning(self, tr('midi.error'),
                                              tr('midi.select_port'))
                self.midi_enable_check.setChecked(False)
                return
            ok, err = self.bot.open_midi_port(port_name)
            if not ok:
                QtWidgets.QMessageBox.critical(self, tr('midi.error'), str(err))
                self.midi_enable_check.setChecked(False)
                return
            self.bot.midi_out_enabled = True
            self.midi_status_label.setText(tr('midi.connected', name=port_name))
        else:
            self.bot.midi_out_enabled = False
            self.bot.close_midi_port()
            self.midi_status_label.setText(tr('midi.no_ports'))
        self.bot.save_app_settings()

    def _midi_test(self):
        if not (self.bot.midi_out_enabled and self.bot.midi_port):
            return

        def go():
            try:
                for n in [60, 62, 64, 65, 67, 69, 71, 72]:
                    with self.bot._midi_lock:
                        self.bot.midi_port.send(mido.Message('note_on', note=n, velocity=90))
                    time.sleep(0.15)
                    with self.bot._midi_lock:
                        self.bot.midi_port.send(mido.Message('note_off', note=n, velocity=0))
                    time.sleep(0.05)
            except Exception as e:
                logger.error(f"MIDI test error: {e}")

        threading.Thread(target=go, daemon=True).start()

    # ─── update ───
    def gui_update_client(self):
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            info, err = fetch_latest_release_info()
            if err or not info:
                self.show_message_box(tr('update.error'), str(err))
                return
            tag = (info.get("tag_name") or info.get("name") or "").strip()
            latest_version = tag.lstrip("v").strip()
            if not latest_version:
                m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", info.get("body", ""))
                if m:
                    latest_version = m.group(1)
            if not latest_version:
                self.show_message_box(tr('update.error'), tr('update.version_unknown'))
                return
            if version_tuple(latest_version) <= version_tuple(CURRENT_VERSION):
                self.show_message_box(tr('settings.update_btn'), tr('update.latest'))
                return
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self.show_message_box(tr('update.error'), tr('update.asset_missing'))
                return
            tmp_name = "AstraKeys_update_tmp.exe"

            def prog_cb(pct):
                QtCore.QTimer.singleShot(0, lambda: self.update_progress.setValue(pct))

            ok, derr = download_asset_to_file(asset_url, tmp_name, progress_callback=prog_cb)
            if not ok:
                self.show_message_box(tr('update.error'), str(derr))
                return
            is_frozen = getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe")
            perform_replacement_and_restart(tmp_name, ASSET_NAME, is_frozen)
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self.show_message_box(tr('update.error'), str(e))
        finally:
            QtCore.QTimer.singleShot(0, lambda: self.update_progress.setVisible(False))

    def show_message_box(self, title, text):
        QtCore.QTimer.singleShot(
            0, lambda: QtWidgets.QMessageBox.information(self, title, text))

    # ─── window state ───
    def save_window_state(self):
        try:
            state = {
                "geometry": {"x": self.x(), "y": self.y(),
                             "width": self.width(), "height": self.height()},
                "maximized": self.isMaximized(),
            }
            with open(WINDOW_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    def load_window_state(self):
        try:
            if os.path.exists(WINDOW_FILE):
                with open(WINDOW_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if not state.get("maximized", False):
                    g = state.get("geometry", {})
                    if all(k in g for k in ["x", "y", "width", "height"]):
                        self.setGeometry(g["x"], g["y"], g["width"], g["height"])
        except Exception:
            pass

    def closeEvent(self, event):
        self.bot.save_app_settings()
        self.bot.save_recordings_index()
        self.save_window_state()
        self.bot.stop_playback()
        self.bot.release_all()
        try:
            self.bot.close_midi_port()
        except Exception:
            pass
        try:
            if self.bot.audio_player:
                self.bot.audio_player.close()
        except Exception:
            pass
        try:
            self.overlay_window.save_settings()
            self.overlay_window.close()
        except Exception:
            pass
        event.accept()


# ═══════════════════════════════════════════════════════════════════
#                            MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    default_playlist = [
        ("Random start, good ending",
         r"[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe] 6 [QPS] C [Sc] [*Ti] Z [SO] [HO] i L [Wsl] Z [ESi] L [LP] [EZ] c P"),
        ("Demo: simple", r"l--l--l--l-lzlklzl"),
        ("Demo: chord", r"fffff[4qf]spsfspsg"),
        ("Demo: blues", r"d h f j [Ffd][xbgf][xd]"),
    ]

    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, encoding='utf-8') as f:
                _t = json.load(f).get('theme', 'gold')
            if _t in THEMES:
                _current_theme_key = _t
    except Exception:
        pass

    bot = RobloxPianoBot(default_playlist)
    threading.Thread(target=bot.play_song, daemon=True).start()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Segoe UI", 9))
    apply_theme(app)

    gui = BotGUI(bot)
    gui.show()
    logger.info("Application started")
    sys.exit(app.exec())
