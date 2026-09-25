# -*- coding: utf-8 -*-
"""
AstraKeys v1.3.0 — mega update
+ mixed timed-notes format:  C {1441ms release}   I   [Q I] {214842ms press}
+ optimized "play without pedal" (progressive sleep instead of busy-wait)
+ no virtual keyboard widget
+ no humanize / no start delay
+ clean modes: No delays / With delays
+ fixed auto_play_no_pedal toggle (toggled(bool) + _to_bool)
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
import shutil
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

CURRENT_VERSION = "1.3.0"
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
DRAFT_FILE = "draft.txt"
HOTKEYS_FILE = "hotkeys.json"
HISTORY_FILE = "play_history.json"
SONG_PROFILES_FILE = "song_profiles.json"
BACKUP_DIR = "backups"

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
#                       TRANSPOSE MARKERS
# ═══════════════════════════════════════════════════════════════════

TRANSPOSE_RE = re.compile(r'Transpose\s+by\s*:\s*([+-]?\d+)', re.IGNORECASE)
TRANSPOSE_START = '\x01'
TRANSPOSE_END = '\x02'


def preprocess_song_text(text):
    if not text:
        return text
    def _repl(m):
        try:
            return f'{TRANSPOSE_START}{int(m.group(1))}{TRANSPOSE_END}'
        except Exception:
            return ''
    return TRANSPOSE_RE.sub(_repl, text)


# ═══════════════════════════════════════════════════════════════════
#                    TIMED / MIXED NOTES FORMAT
# ═══════════════════════════════════════════════════════════════════

TIMED_MARKER = '\x03TIMED\x03'

TIMED_NOTE_RE = re.compile(
    r'(\[[^\]]+\]|[^\s{]+)'
    r'\s*\{\s*'
    r'(\d+(?:\.\d+)?)\s*ms\s+'
    r'(press|release)'
    r'\s*\}',
    re.IGNORECASE,
)

MIXED_TOKEN_RE = re.compile(
    r'(\[[^\]]+\]|[^\s{}]+)'
    r'(?:\s*\{\s*(\d+(?:\.\d+)?)\s*ms\s+(press|release)\s*\})?',
    re.IGNORECASE,
)


def is_timed_note_text(text):
    if not text:
        return False
    return len(TIMED_NOTE_RE.findall(text)) >= 3


def parse_timed_note_text(text, default_gap_ms=150, hold_ms=120):
    if not text:
        return None

    tokens = []
    for m in MIXED_TOKEN_RE.finditer(text):
        keys_raw = m.group(1).strip()
        time_ms = m.group(2)
        action = m.group(3)

        if keys_raw.startswith('[') and keys_raw.endswith(']'):
            keys = ''.join(keys_raw[1:-1].split())
        else:
            keys = keys_raw
        keys = ''.join(ch for ch in keys if ch in ROBLOX_KEYS)
        if not keys:
            continue

        tokens.append({
            'keys': keys,
            'time': float(time_ms) if time_ms is not None else None,
            'action': action.lower() if action else None,
        })

    if not tokens:
        return None

    n = len(tokens)
    times = [None] * n
    anchors = [i for i, t in enumerate(tokens) if t['time'] is not None]
    for i in anchors:
        times[i] = tokens[i]['time']

    if not anchors:
        for i in range(n):
            times[i] = i * default_gap_ms
    else:
        first = anchors[0]
        if first > 0:
            if times[first] <= 0:
                step = default_gap_ms
                for i in range(first):
                    times[i] = times[first] - (first - i) * step
            else:
                step = times[first] / first
                for i in range(first):
                    times[i] = step * i

        for k in range(len(anchors) - 1):
            i1, i2 = anchors[k], anchors[k + 1]
            t1, t2 = times[i1], times[i2]
            span = i2 - i1
            if span > 0:
                step = (t2 - t1) / span
                for j in range(1, span):
                    times[i1 + j] = t1 + step * j

        last = anchors[-1]
        if len(anchors) >= 2:
            i1, i2 = anchors[-2], anchors[-1]
            if i2 > i1:
                rate = (times[i2] - times[i1]) / (i2 - i1)
            else:
                rate = default_gap_ms
        else:
            rate = default_gap_ms
        if rate <= 0:
            rate = default_gap_ms
        for i in range(last + 1, n):
            times[i] = times[last] + rate * (i - last)

    def _release_matches(press_keys, release_keys):
        return all(c in press_keys for c in release_keys)

    events = []
    for i, tok in enumerate(tokens):
        t = times[i]
        if t is None:
            continue
        keys = tok['keys']
        action = tok['action']
        t_sec = round(t / 1000.0, 4)

        if action == 'release':
            events.append({'time': t_sec, 'key': keys, 'action': 'release'})
            continue

        events.append({'time': t_sec, 'key': keys, 'action': 'press'})

        release_ms = None
        for j in range(i + 1, n):
            tok2 = tokens[j]
            if _release_matches(keys, tok2['keys']) and tok2['action'] == 'release':
                if times[j] is not None:
                    release_ms = times[j]
                break
            if _release_matches(keys, tok2['keys']) and tok2['action'] in (None, 'press'):
                break

        if release_ms is None:
            release_ms = t + hold_ms

        events.append({
            'time': round(release_ms / 1000.0, 4),
            'key': keys,
            'action': 'release',
        })

    events.sort(key=lambda e: e['time'])
    return events


# ═══════════════════════════════════════════════════════════════════
#                            DEFAULT HOTKEYS
# ═══════════════════════════════════════════════════════════════════

DEFAULT_HOTKEYS = {
    "toggle_play":   "f1",
    "restart":       "f2",
    "skip_fwd":      "f3",
    "skip_back":     "f4",
    "pause_playback":"f5",
    "freeze":        "f6",
    "next_mode":     "f7",
    "next_song":     "f8",
    "stop":          "f9",
    "last_rec":      "f10",
    "record":        "f12",
    "speed_up":      "ctrl+up",
    "speed_down":    "ctrl+down",
}


def load_hotkeys():
    hk = dict(DEFAULT_HOTKEYS)
    try:
        if os.path.exists(HOTKEYS_FILE):
            with open(HOTKEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in hk:
                    hk[k] = v
    except Exception as e:
        logger.error(f"load_hotkeys: {e}")
    return hk


def save_hotkeys(hk):
    try:
        with open(HOTKEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(hk, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_hotkeys: {e}")


# ═══════════════════════════════════════════════════════════════════
#                            THEMES
# ═══════════════════════════════════════════════════════════════════

def _to_rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _mk_theme(key, name_key, is_dark, bg, bg_alt, panel, panel_alt, inp,
              text, text_muted, text_dim, accent, accent_hover, accent_press,
              accent_text, border, danger="#e05a4d", danger_hover="#ff6a5d",
              success="#5cb85c"):
    return {
        "key": key, "name_key": name_key, "is_dark": is_dark,
        "bg": bg, "bg_alt": bg_alt,
        "panel": panel, "panel_alt": panel_alt, "input": inp,
        "text": text, "text_muted": text_muted, "text_dim": text_dim,
        "accent": accent, "accent_hover": accent_hover, "accent_press": accent_press,
        "accent_text": accent_text,
        "accent_soft": _to_rgba(accent, 0.10),
        "border": border, "border_accent": _to_rgba(accent, 0.30),
        "danger": danger, "danger_hover": danger_hover, "success": success,
        "selection": _to_rgba(accent, 0.22),
        "scrollbar": panel_alt, "scrollbar_hover": border,
        "overlay_bg": bg, "overlay_text": accent_hover,
        "overlay_accent": accent, "overlay_highlight": _to_rgba(accent, 0.35),
    }


THEMES = {
    "gold": _mk_theme("gold", "theme.gold", True,
        "#0a0a0a", "#0f0f0f", "#151515", "#1c1c1c", "#181818",
        "#f5f3f1", "#8a8a8a", "#5a5a5a",
        "#d4af37", "#ffd86a", "#b8942a", "#0a0a0a", "#262626"),
    "sand": _mk_theme("sand", "theme.sand", False,
        "#f5efe1", "#ece4d0", "#ffffff", "#faf6ec", "#ffffff",
        "#2b2418", "#7c7160", "#ab9f88",
        "#a67c00", "#c99612", "#8a6508", "#ffffff", "#e6dcc3"),
    "blue": _mk_theme("blue", "theme.blue", True,
        "#08121e", "#0b1824", "#0f1e2e", "#142838", "#101f2d",
        "#e8f2ff", "#7a90a8", "#4a5d72",
        "#4ea3ff", "#82c0ff", "#2d7ed4", "#001018", "#1a2e44"),
    "purple": _mk_theme("purple", "theme.purple", True,
        "#100a1e", "#160f28", "#1d1433", "#241a40", "#1a1230",
        "#f0e8ff", "#9488b0", "#5e5578",
        "#a060ff", "#c896ff", "#7d3fd8", "#0a0618", "#2a1f4a"),
    "green": _mk_theme("green", "theme.green", True,
        "#081410", "#0c1c16", "#10281e", "#163428", "#122c22",
        "#e8fff0", "#80a890", "#4a6a58",
        "#4dcc80", "#80e8a0", "#2da060", "#041810", "#1c3e30"),
    "pink": _mk_theme("pink", "theme.pink", True,
        "#1a0812", "#240c1a", "#2e1022", "#3a162c", "#2a0e20",
        "#ffe8f2", "#b088a0", "#755868",
        "#ff5ca8", "#ff8cc4", "#d43a82", "#180610", "#3e1a2e"),
    "red": _mk_theme("red", "theme.red", True,
        "#1a0808", "#240c0c", "#2e1010", "#3a1616", "#2a0e0e",
        "#ffe8e8", "#b08888", "#755858",
        "#ff5050", "#ff8080", "#d43030", "#180404", "#3e1a1a"),
    "cyan": _mk_theme("cyan", "theme.cyan", True,
        "#081618", "#0c1c20", "#10282e", "#163438", "#122c30",
        "#e8feff", "#80a8b0", "#4a6870",
        "#3cd0e0", "#70e8f0", "#20a0b0", "#041418", "#1c3a3e"),
    "orange": _mk_theme("orange", "theme.orange", True,
        "#1a1008", "#24160c", "#2e1c10", "#3a2416", "#2a1a0e",
        "#ffeee0", "#b09880", "#756858",
        "#ff8c30", "#ffb060", "#d46a10", "#180c04", "#3e2818"),
    "mono": _mk_theme("mono", "theme.mono", True,
        "#0a0a0a", "#101010", "#161616", "#1e1e1e", "#181818",
        "#f0f0f0", "#909090", "#606060",
        "#d0d0d0", "#ffffff", "#a8a8a8", "#0a0a0a", "#282828"),
}

_current_theme_key = "gold"


def get_theme():
    return THEMES.get(_current_theme_key, THEMES["gold"])


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
        background: {t['accent_hover']};
        border-color: {t['accent_hover']};
    }}
    QPushButton[role="primary"]:pressed {{ background: {t['accent_press']}; }}
    QPushButton[role="danger"] {{
        background: {t['panel_alt']};
        color: {t['danger']};
        border: 1px solid {t['danger']};
    }}
    QPushButton[role="danger"]:hover {{ background: {t['danger']}; color: #ffffff; }}
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
    QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {t['accent']}; }}
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
    QListWidget::item {{ padding: 6px 10px; border-radius: 5px; min-height: 18px; }}
    QListWidget::item:hover {{ background: {t['panel_alt']}; }}
    QListWidget::item:selected {{ background: {t['selection']}; color: {t['text']}; }}
    QSlider::groove:horizontal {{ height: 5px; background: {t['border']}; border-radius: 3px; }}
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
    QTabBar::tab:selected {{ color: {t['accent']}; border-bottom: 2px solid {t['accent']}; }}
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
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {t['scrollbar']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {t['scrollbar_hover']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: {t['scrollbar']}; border-radius: 5px; min-width: 30px; }}
    QScrollBar::handle:horizontal:hover {{ background: {t['scrollbar_hover']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    QFrame#titlebar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {t['bg_alt']}, stop:1 {t['bg']});
        border: none;
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#accent_line {{ background: {t['accent']}; max-height: 1px; min-height: 1px; border: none; }}
    QLabel#app_title {{ font-size: 13pt; font-weight: 700; color: {t['accent']}; background: transparent; }}
    QLabel#section_label {{
        color: {t['text_muted']};
        font-size: 8pt; font-weight: 700;
        letter-spacing: 2px;
        background: transparent;
    }}
    QLabel#status_normal {{ color: {t['text_muted']}; font-size: 8pt; background: transparent; }}
    QLabel#status_accent {{ color: {t['accent']}; font-size: 9pt; font-weight: 600; background: transparent; }}
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
    QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
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
        'app.about_text': ('AstraKeys v{version}\nАвтор: SMisha2\n\nПианино для Roblox.'),
        'ui.ok': 'OK', 'ui.cancel': 'Отмена', 'ui.close': 'Закрыть',
        'ui.yes': 'Да', 'ui.no': 'Нет', 'ui.add': 'Добавить',
        'ui.remove': 'Удалить', 'ui.save': 'Сохранить', 'ui.load': 'Загрузить',
        'ui.import': 'Импорт', 'ui.export': 'Экспорт', 'ui.reset': 'Сбросить',
        'ui.refresh': 'Обновить', 'ui.error': 'Ошибка',
        'ui.warning': 'Предупреждение', 'ui.info': 'Информация',
        'ui.done': 'Готово', 'ui.confirm': 'Подтверждение',
        'theme.gold': 'Золото', 'theme.sand': 'Песок',
        'theme.blue': 'Синий', 'theme.purple': 'Фиолетовый',
        'theme.green': 'Зелёный', 'theme.pink': 'Розовый',
        'theme.red': 'Красный', 'theme.cyan': 'Голубой',
        'theme.orange': 'Оранжевый', 'theme.mono': 'Моно',
        'titlebar.about_tooltip': 'О программе',
        'titlebar.theme_tooltip': 'Сменить тему',
        'titlebar.log_tooltip': 'Лог',
        'titlebar.lang_tooltip': 'Язык',
        'titlebar.custom_theme': 'Свой цвет',
        'playlist.section': 'ПЛЕЙЛИСТ',
        'playlist.add_tooltip': 'Добавить', 'playlist.remove_tooltip': 'Удалить',
        'playlist.rename_tooltip': 'Переименовать', 'playlist.save_tooltip': 'Сохранить',
        'playlist.load_tooltip': 'Загрузить', 'playlist.manage_recordings': 'Записи',
        'playlist.overlay': 'Ноты', 'playlist.history': 'История',
        'playlist.hotkeys': 'Хоткеи', 'playlist.profile': 'Профиль песни',
        'player.section': 'ПРОИГРЫВАТЕЛЬ',
        'player.input_placeholder': 'Вставьте текст песни...',
        'player.start_tooltip': 'Играть (F1)', 'player.pause_tooltip': 'Пауза (F1)',
        'player.record_tooltip': 'Запись (F12)', 'player.playback_tooltip': 'Записи',
        'player.stop_playback_tooltip': 'Стоп (F9)', 'player.next_song_tooltip': 'Следующая (F8)',
        'player.next_mode_tooltip': 'Режим (F7)', 'player.btn_play': 'Играть',
        'player.btn_pause': 'Пауза', 'player.btn_record': 'Запись',
        'player.btn_stop_rec': 'Стоп', 'player.btn_playback': 'Записи',
        'player.btn_stop_playback': 'Стоп', 'player.btn_pause_playback': 'Пауза',
        'player.btn_resume_playback': 'Продолжить',
        'settings.tab_params': 'Параметры', 'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Режим', 'settings.mode1': 'Без задержек',
        'settings.mode2': 'С задержками',
        'settings.min_delay': 'Мин. задержка, мс', 'settings.max_delay': 'Макс. задержка, мс',
        'settings.transpose_initial': 'Начальный транспоз',
        'settings.transpose_hint': 'Текущее в игре',
        'settings.bpm': 'Темп, BPM', 'settings.bpm_hint': '0 = Авто-удержание',
        'settings.speed': 'Скорость', 'settings.speed_hint': '0.5×–2.0×',
        'settings.speaker_enable': 'Звук в динамиках',
        'settings.auto_update': 'Проверять обновления',
        'settings.update_btn': 'Обновления', 'settings.pedal_btn': 'Педали',
        'settings.auto_transpose': 'Авто-транспоз',
        'settings.auto_transpose_hint': 'Подобрать транспоз под диапазон',
        'audio.auto_play': 'Играть без педали', 'audio.auto_hold': 'Авто-удержание, мс',
        'audio.warn_title': 'Звук недоступен',
        'audio.warn_text': 'Установите:\npip install sounddevice numpy',
        'midi.enable': 'MIDI-выход', 'midi.port': 'Порт', 'midi.test': 'Тест',
        'midi.no_ports': '(нет портов)', 'midi.hint': 'Установите loopMIDI',
        'midi.no_lib': 'mido не установлен', 'midi.connected': 'OK: {name}',
        'midi.error': 'Ошибка MIDI', 'midi.select_port': 'Выберите порт',
        'midi.refresh_tooltip': 'Обновить',
        'status.idle': 'Готов', 'status.playing': 'Играет', 'status.paused': 'Пауза',
        'status.recording': 'Запись', 'status.playback': 'Воспроизведение',
        'status.preview': 'Превью',
        'help.text': 'F1 пуск · F2 рестарт · F3/F4 ±25 · F6 заморозка · F7 режим · F8 песня · F9 стоп · F12 запись',
        'overlay.pin_tooltip': 'Поверх окон', 'overlay.opacity_tooltip': 'Прозрачность',
        'overlay.close_tooltip': 'Скрыть', 'overlay.font_size': 'Размер шрифта',
        'overlay.lines': 'Строк', 'overlay.reset': 'Сбросить', 'overlay.opacity_1pct': '1%',
        'pedal.title': 'Педали', 'pedal.placeholder': 'Символ',
        'pedal.add': 'Добавить', 'pedal.remove': 'Удалить', 'pedal.reset': 'Сброс',
        'recordings.title': 'Записи', 'recordings.search': 'Поиск...',
        'recordings.sort_new': 'Новые', 'recordings.sort_old': 'Старые',
        'recordings.sort_az': 'А-Я', 'recordings.sort_za': 'Я-А',
        'recordings.sort_dur': 'Длительность', 'recordings.sort_fav': 'Избранные',
        'recordings.preview': 'Прослушать', 'recordings.favorite': 'Избранное',
        'recordings.rename': 'Переименовать', 'recordings.editor': 'Редактор',
        'recordings.delete': 'Удалить', 'recordings.export_zip': 'Экспорт ZIP',
        'recordings.import_zip': 'Импорт ZIP', 'recordings.open_folder': 'Папка',
        'recordings.clean': 'Очистить', 'recordings.confirm_delete': 'Удалить "{name}"?',
        'recordings.confirm_clean': 'Удалить {n} записей?',
        'recordings.import_ok': 'Добавлено: {n}',
        'editor.title': 'Редактор', 'editor.trim': 'Обрезка', 'editor.concat': 'Склейка',
        'editor.select': 'Выберите:', 'editor.duration': 'Длительность',
        'editor.start': 'Начало, с', 'editor.end': 'Конец, с',
        'editor.preview': 'Прослушать', 'editor.save_new': 'Сохранить как новую',
        'editor.first': 'Первая:', 'editor.second': 'Вторая:',
        'editor.gap': 'Пауза, с', 'editor.concat_btn': 'Склеить',
        'editor.notes': 'Ноты', 'editor.offset': 'Сдвиг, с',
        'editor.quantize': 'Квантовать', 'editor.quantize_btn': 'Применить',
        'editor.undo': 'Отменить', 'editor.redo': 'Вернуть',
        'editor.delete_note': 'Удалить ноту', 'editor.save_changes': 'Сохранить',
        'log.title': 'Лог', 'log.copy': 'Копировать', 'log.close': 'Закрыть',
        'update.error': 'Ошибка', 'update.latest': 'Последняя версия',
        'update.asset_missing': 'Файл не найден', 'update.version_unknown': 'Неизвестная версия',
        'songs.name_title': 'Название', 'songs.name_label': 'Введите:',
        'songs.new_name': 'Новое имя:', 'songs.delete_title': 'Удаление',
        'songs.delete_text': 'Удалить "{name}"?', 'songs.default_name': 'Песня {n}',
        'recording.name_title': 'Имя записи', 'recording.name_label': 'Введите имя:',
        'recording.empty': 'Нет нот',
        'file.json': 'JSON (*.json)', 'file.zip': 'ZIP (*.zip)',
        'hotkeys.title': 'Горячие клавиши', 'hotkeys.action': 'Действие',
        'hotkeys.key': 'Клавиша', 'hotkeys.change': 'Изменить',
        'hotkeys.press': 'Нажмите клавишу...', 'hotkeys.reset': 'Сброс',
        'history.title': 'История воспроизведений', 'history.clear': 'Очистить',
        'history.empty': 'Пусто', 'history.played': 'Играл',
        'history.stopped_after': 'остановлено через',
        'theme_custom.title': 'Свой цвет темы', 'theme_custom.accent': 'Акцент',
        'theme_custom.bg': 'Фон', 'theme_custom.text': 'Текст',
        'theme_custom.apply': 'Применить',
        'draft.title': 'Черновик', 'draft.text': 'Найден несохранённый черновик.\nВосстановить?',
        'profile.title': 'Профиль песни', 'profile.use': 'Использовать профиль для этой песни',
        'profile.save': 'Сохранить профиль', 'profile.delete': 'Удалить профиль',
        'autotranspose.title': 'Авто-транспоз',
        'autotranspose.text': 'Диапазон песни: {lo}..{hi}\nРекомендуемый транспоз: {tr}\nПрименить?',
        'autotranspose.none': 'Нет нот для анализа',
    },
    'en': {
        'app.title': 'AstraKeys', 'app.about_title': 'About',
        'app.about_text': ('AstraKeys v{version}\nAuthor: SMisha2\n\nPiano for Roblox.'),
        'ui.ok': 'OK', 'ui.cancel': 'Cancel', 'ui.close': 'Close',
        'ui.yes': 'Yes', 'ui.no': 'No', 'ui.add': 'Add', 'ui.remove': 'Remove',
        'ui.save': 'Save', 'ui.load': 'Load', 'ui.import': 'Import',
        'ui.export': 'Export', 'ui.reset': 'Reset', 'ui.refresh': 'Refresh',
        'ui.error': 'Error', 'ui.warning': 'Warning', 'ui.info': 'Info',
        'ui.done': 'Done', 'ui.confirm': 'Confirm',
        'theme.gold': 'Gold', 'theme.sand': 'Sand', 'theme.blue': 'Blue',
        'theme.purple': 'Purple', 'theme.green': 'Green', 'theme.pink': 'Pink',
        'theme.red': 'Red', 'theme.cyan': 'Cyan', 'theme.orange': 'Orange',
        'theme.mono': 'Mono',
        'titlebar.about_tooltip': 'About', 'titlebar.theme_tooltip': 'Theme',
        'titlebar.log_tooltip': 'Log', 'titlebar.lang_tooltip': 'Language',
        'titlebar.custom_theme': 'Custom color',
        'playlist.section': 'PLAYLIST', 'playlist.add_tooltip': 'Add',
        'playlist.remove_tooltip': 'Remove', 'playlist.rename_tooltip': 'Rename',
        'playlist.save_tooltip': 'Save', 'playlist.load_tooltip': 'Load',
        'playlist.manage_recordings': 'Recordings', 'playlist.overlay': 'Notes',
        'playlist.history': 'History', 'playlist.hotkeys': 'Hotkeys',
        'playlist.profile': 'Profile',
        'player.section': 'PLAYER', 'player.input_placeholder': 'Paste song text...',
        'player.start_tooltip': 'Play (F1)', 'player.pause_tooltip': 'Pause (F1)',
        'player.record_tooltip': 'Record (F12)', 'player.playback_tooltip': 'Recordings',
        'player.stop_playback_tooltip': 'Stop (F9)', 'player.next_song_tooltip': 'Next (F8)',
        'player.next_mode_tooltip': 'Mode (F7)', 'player.btn_play': 'Play',
        'player.btn_pause': 'Pause', 'player.btn_record': 'Record',
        'player.btn_stop_rec': 'Stop', 'player.btn_playback': 'Records',
        'player.btn_stop_playback': 'Stop', 'player.btn_pause_playback': 'Pause',
        'player.btn_resume_playback': 'Resume',
        'settings.tab_params': 'Settings', 'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Mode', 'settings.mode1': 'No delays',
        'settings.mode2': 'With delays',
        'settings.min_delay': 'Min delay, ms', 'settings.max_delay': 'Max delay, ms',
        'settings.transpose_initial': 'Initial transpose',
        'settings.transpose_hint': 'Current in-game',
        'settings.bpm': 'Tempo, BPM', 'settings.bpm_hint': '0 = auto-hold',
        'settings.speed': 'Speed', 'settings.speed_hint': '0.5x-2.0x',
        'settings.speaker_enable': 'Speaker audio',
        'settings.auto_update': 'Check updates',
        'settings.update_btn': 'Updates', 'settings.pedal_btn': 'Pedals',
        'settings.auto_transpose': 'Auto-transpose',
        'settings.auto_transpose_hint': 'Fit to range',
        'audio.auto_play': 'Play without pedal', 'audio.auto_hold': 'Auto-hold, ms',
        'audio.warn_title': 'Audio unavailable',
        'audio.warn_text': 'Install:\npip install sounddevice numpy',
        'midi.enable': 'MIDI output', 'midi.port': 'Port', 'midi.test': 'Test',
        'midi.no_ports': '(no ports)', 'midi.hint': 'Install loopMIDI',
        'midi.no_lib': 'mido not installed', 'midi.connected': 'OK: {name}',
        'midi.error': 'MIDI error', 'midi.select_port': 'Select port',
        'midi.refresh_tooltip': 'Refresh',
        'status.idle': 'Ready', 'status.playing': 'Playing', 'status.paused': 'Paused',
        'status.recording': 'Recording', 'status.playback': 'Playback',
        'status.preview': 'Preview',
        'help.text': 'F1 play · F2 restart · F3/F4 ±25 · F6 freeze · F7 mode · F8 song · F9 stop · F12 record',
        'overlay.pin_tooltip': 'Pin', 'overlay.opacity_tooltip': 'Opacity',
        'overlay.close_tooltip': 'Hide', 'overlay.font_size': 'Font size',
        'overlay.lines': 'Lines', 'overlay.reset': 'Reset', 'overlay.opacity_1pct': '1%',
        'pedal.title': 'Pedals', 'pedal.placeholder': 'Char',
        'pedal.add': 'Add', 'pedal.remove': 'Remove', 'pedal.reset': 'Reset',
        'recordings.title': 'Recordings', 'recordings.search': 'Search...',
        'recordings.sort_new': 'Newest', 'recordings.sort_old': 'Oldest',
        'recordings.sort_az': 'A-Z', 'recordings.sort_za': 'Z-A',
        'recordings.sort_dur': 'Duration', 'recordings.sort_fav': 'Favorites',
        'recordings.preview': 'Preview', 'recordings.favorite': 'Favorite',
        'recordings.rename': 'Rename', 'recordings.editor': 'Editor',
        'recordings.delete': 'Delete', 'recordings.export_zip': 'Export ZIP',
        'recordings.import_zip': 'Import ZIP', 'recordings.open_folder': 'Folder',
        'recordings.clean': 'Clean', 'recordings.confirm_delete': 'Delete "{name}"?',
        'recordings.confirm_clean': 'Delete {n} recordings?',
        'recordings.import_ok': 'Added: {n}',
        'editor.title': 'Editor', 'editor.trim': 'Trim', 'editor.concat': 'Concat',
        'editor.select': 'Select:', 'editor.duration': 'Duration',
        'editor.start': 'Start, s', 'editor.end': 'End, s',
        'editor.preview': 'Preview', 'editor.save_new': 'Save as new',
        'editor.first': 'First:', 'editor.second': 'Second:',
        'editor.gap': 'Gap, s', 'editor.concat_btn': 'Concat',
        'editor.notes': 'Notes', 'editor.offset': 'Offset, s',
        'editor.quantize': 'Quantize', 'editor.quantize_btn': 'Apply',
        'editor.undo': 'Undo', 'editor.redo': 'Redo',
        'editor.delete_note': 'Delete note', 'editor.save_changes': 'Save',
        'log.title': 'Log', 'log.copy': 'Copy', 'log.close': 'Close',
        'update.error': 'Error', 'update.latest': 'Latest version',
        'update.asset_missing': 'Asset missing', 'update.version_unknown': 'Unknown version',
        'songs.name_title': 'Name', 'songs.name_label': 'Enter:',
        'songs.new_name': 'New name:', 'songs.delete_title': 'Delete',
        'songs.delete_text': 'Delete "{name}"?', 'songs.default_name': 'Song {n}',
        'recording.name_title': 'Recording name', 'recording.name_label': 'Enter name:',
        'recording.empty': 'No notes',
        'file.json': 'JSON (*.json)', 'file.zip': 'ZIP (*.zip)',
        'hotkeys.title': 'Hotkeys', 'hotkeys.action': 'Action',
        'hotkeys.key': 'Key', 'hotkeys.change': 'Change',
        'hotkeys.press': 'Press a key...', 'hotkeys.reset': 'Reset',
        'history.title': 'Play history', 'history.clear': 'Clear',
        'history.empty': 'Empty', 'history.played': 'Played',
        'history.stopped_after': 'stopped after',
        'theme_custom.title': 'Custom theme color', 'theme_custom.accent': 'Accent',
        'theme_custom.bg': 'Background', 'theme_custom.text': 'Text',
        'theme_custom.apply': 'Apply',
        'draft.title': 'Draft', 'draft.text': 'Unsent draft found.\nRestore?',
        'profile.title': 'Song profile', 'profile.use': 'Use profile for this song',
        'profile.save': 'Save profile', 'profile.delete': 'Delete profile',
        'autotranspose.title': 'Auto-transpose',
        'autotranspose.text': 'Song range: {lo}..{hi}\nSuggested transpose: {tr}\nApply?',
        'autotranspose.none': 'No notes to analyze',
    },
    'uk': {
        'app.title': 'AstraKeys', 'app.about_title': 'Про програму',
        'app.about_text': ('AstraKeys v{version}\nАвтор: SMisha2\n\nПіаніно для Roblox.'),
        'ui.ok': 'OK', 'ui.cancel': 'Скасувати', 'ui.close': 'Закрити',
        'ui.yes': 'Так', 'ui.no': 'Ні', 'ui.add': 'Додати', 'ui.remove': 'Видалити',
        'ui.save': 'Зберегти', 'ui.load': 'Завантажити', 'ui.import': 'Імпорт',
        'ui.export': 'Експорт', 'ui.reset': 'Скинути', 'ui.refresh': 'Оновити',
        'ui.error': 'Помилка', 'ui.warning': 'Попередження', 'ui.info': 'Інформація',
        'ui.done': 'Готово', 'ui.confirm': 'Підтвердження',
        'theme.gold': 'Золото', 'theme.sand': 'Пісок', 'theme.blue': 'Синій',
        'theme.purple': 'Фіолетовий', 'theme.green': 'Зелений', 'theme.pink': 'Рожевий',
        'theme.red': 'Червоний', 'theme.cyan': 'Блакитний', 'theme.orange': 'Оранжевий',
        'theme.mono': 'Моно',
        'titlebar.about_tooltip': 'Про програму', 'titlebar.theme_tooltip': 'Тема',
        'titlebar.log_tooltip': 'Лог', 'titlebar.lang_tooltip': 'Мова',
        'titlebar.custom_theme': 'Свій колір',
        'playlist.section': 'ПЛЕЙЛИСТ', 'playlist.add_tooltip': 'Додати',
        'playlist.remove_tooltip': 'Видалити', 'playlist.rename_tooltip': 'Перейменувати',
        'playlist.save_tooltip': 'Зберегти', 'playlist.load_tooltip': 'Завантажити',
        'playlist.manage_recordings': 'Записи', 'playlist.overlay': 'Ноти',
        'playlist.history': 'Історія', 'playlist.hotkeys': 'Хоткеї',
        'playlist.profile': 'Профіль',
        'player.section': 'ПРОГРАВАЧ', 'player.input_placeholder': 'Вставте текст...',
        'player.start_tooltip': 'Грати (F1)', 'player.pause_tooltip': 'Пауза (F1)',
        'player.record_tooltip': 'Запис (F12)', 'player.playback_tooltip': 'Записи',
        'player.stop_playback_tooltip': 'Стоп (F9)', 'player.next_song_tooltip': 'Наступна (F8)',
        'player.next_mode_tooltip': 'Режим (F7)', 'player.btn_play': 'Грати',
        'player.btn_pause': 'Пауза', 'player.btn_record': 'Запис',
        'player.btn_stop_rec': 'Стоп', 'player.btn_playback': 'Записи',
        'player.btn_stop_playback': 'Стоп', 'player.btn_pause_playback': 'Пауза',
        'player.btn_resume_playback': 'Продовжити',
        'settings.tab_params': 'Параметри', 'settings.tab_midi': 'MIDI',
        'settings.mode_label': 'Режим', 'settings.mode1': 'Без затримок',
        'settings.mode2': 'Із затримками',
        'settings.min_delay': 'Мін. затримка, мс', 'settings.max_delay': 'Макс. затримка, мс',
        'settings.transpose_initial': 'Початковий транспоз',
        'settings.transpose_hint': 'Поточне у грі',
        'settings.bpm': 'Темп, BPM', 'settings.bpm_hint': '0 = Авто-утримання',
        'settings.speed': 'Швидкість', 'settings.speed_hint': '0.5x-2.0x',
        'settings.speaker_enable': 'Звук у динаміках',
        'settings.auto_update': 'Перевіряти оновлення',
        'settings.update_btn': 'Оновлення', 'settings.pedal_btn': 'Педалі',
        'settings.auto_transpose': 'Авто-транспоз',
        'settings.auto_transpose_hint': 'Підібрати під діапазон',
        'audio.auto_play': 'Грати без педалі', 'audio.auto_hold': 'Авто-утримання, мс',
        'audio.warn_title': 'Звук недоступний',
        'audio.warn_text': 'Встановіть:\npip install sounddevice numpy',
        'midi.enable': 'MIDI-вихід', 'midi.port': 'Порт', 'midi.test': 'Тест',
        'midi.no_ports': '(немає портів)', 'midi.hint': 'Встановіть loopMIDI',
        'midi.no_lib': 'mido не встановлено', 'midi.connected': 'OK: {name}',
        'midi.error': 'Помилка MIDI', 'midi.select_port': 'Виберіть порт',
        'midi.refresh_tooltip': 'Оновити',
        'status.idle': 'Готовий', 'status.playing': 'Грає', 'status.paused': 'Пауза',
        'status.recording': 'Запис', 'status.playback': 'Відтворення',
        'status.preview': 'Прев\'ю',
        'help.text': 'F1 пуск · F2 рестарт · F3/F4 ±25 · F6 заморозка · F7 режим · F8 пісня · F9 стоп · F12 запис',
        'overlay.pin_tooltip': 'Поверх вікон', 'overlay.opacity_tooltip': 'Прозорість',
        'overlay.close_tooltip': 'Сховати', 'overlay.font_size': 'Розмір шрифту',
        'overlay.lines': 'Рядків', 'overlay.reset': 'Скинути', 'overlay.opacity_1pct': '1%',
        'pedal.title': 'Педалі', 'pedal.placeholder': 'Символ',
        'pedal.add': 'Додати', 'pedal.remove': 'Видалити', 'pedal.reset': 'Скинути',
        'recordings.title': 'Записи', 'recordings.search': 'Пошук...',
        'recordings.sort_new': 'Нові', 'recordings.sort_old': 'Старі',
        'recordings.sort_az': 'А-Я', 'recordings.sort_za': 'Я-А',
        'recordings.sort_dur': 'Тривалість', 'recordings.sort_fav': 'Обрані',
        'recordings.preview': 'Прослухати', 'recordings.favorite': 'Обране',
        'recordings.rename': 'Перейменувати', 'recordings.editor': 'Редактор',
        'recordings.delete': 'Видалити', 'recordings.export_zip': 'Експорт ZIP',
        'recordings.import_zip': 'Імпорт ZIP', 'recordings.open_folder': 'Папка',
        'recordings.clean': 'Очистити', 'recordings.confirm_delete': 'Видалити "{name}"?',
        'recordings.confirm_clean': 'Видалити {n} записів?',
        'recordings.import_ok': 'Додано: {n}',
        'editor.title': 'Редактор', 'editor.trim': 'Обрізка', 'editor.concat': 'Склейка',
        'editor.select': 'Виберіть:', 'editor.duration': 'Тривалість',
        'editor.start': 'Початок, с', 'editor.end': 'Кінець, с',
        'editor.preview': 'Прослухати', 'editor.save_new': 'Зберегти як нову',
        'editor.first': 'Перша:', 'editor.second': 'Друга:',
        'editor.gap': 'Пауза, с', 'editor.concat_btn': 'Склеїти',
        'editor.notes': 'Ноти', 'editor.offset': 'Зсув, с',
        'editor.quantize': 'Квантувати', 'editor.quantize_btn': 'Застосувати',
        'editor.undo': 'Скасувати', 'editor.redo': 'Повернути',
        'editor.delete_note': 'Видалити ноту', 'editor.save_changes': 'Зберегти',
        'log.title': 'Лог', 'log.copy': 'Копіювати', 'log.close': 'Закрити',
        'update.error': 'Помилка', 'update.latest': 'Остання версія',
        'update.asset_missing': 'Файл не знайдено', 'update.version_unknown': 'Невідома версія',
        'songs.name_title': 'Назва', 'songs.name_label': 'Введіть:',
        'songs.new_name': 'Нова назва:', 'songs.delete_title': 'Видалення',
        'songs.delete_text': 'Видалити "{name}"?', 'songs.default_name': 'Пісня {n}',
        'recording.name_title': 'Назва запису', 'recording.name_label': 'Введіть назву:',
        'recording.empty': 'Немає нот',
        'file.json': 'JSON (*.json)', 'file.zip': 'ZIP (*.zip)',
        'hotkeys.title': 'Гарячі клавіші', 'hotkeys.action': 'Дія',
        'hotkeys.key': 'Клавіша', 'hotkeys.change': 'Змінити',
        'hotkeys.press': 'Натисніть клавішу...', 'hotkeys.reset': 'Скинути',
        'history.title': 'Історія', 'history.clear': 'Очистити',
        'history.empty': 'Порожньо', 'history.played': 'Грав',
        'history.stopped_after': 'зупинено через',
        'theme_custom.title': 'Свій колір', 'theme_custom.accent': 'Акцент',
        'theme_custom.bg': 'Фон', 'theme_custom.text': 'Текст',
        'theme_custom.apply': 'Застосувати',
        'draft.title': 'Чернетка', 'draft.text': 'Знайдено незбережену чернетку.\nВідновити?',
        'profile.title': 'Профіль пісні', 'profile.use': 'Використати профіль',
        'profile.save': 'Зберегти профіль', 'profile.delete': 'Видалити профіль',
        'autotranspose.title': 'Авто-транспоз',
        'autotranspose.text': 'Діапазон пісні: {lo}..{hi}\nРекомендований транспоз: {tr}\nЗастосувати?',
        'autotranspose.none': 'Немає нот для аналізу',
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
ROBLOX_KEYS = ("1234567890qwertyuiopasdfghjklzxcvbnm"
               "QWERTYUIOPASDFGHJKLZXCVBNM!@#$%^*()_-+{}:;\"'<>,.?/|\\~")
KEY_TO_MIDI = {
    '1': 36, '2': 38, '3': 40, '4': 41, '5': 43, '6': 45, '7': 47,
    '8': 48, '9': 50, '0': 52, 'q': 53, 'w': 55, 'e': 57, 'r': 59,
    't': 60, 'y': 62, 'u': 64, 'i': 65, 'o': 67, 'p': 69, 'a': 71,
    's': 72, 'd': 74, 'f': 76, 'g': 77, 'h': 79, 'j': 81, 'k': 83,
    'l': 84, 'z': 86, 'x': 88, 'c': 89, 'v': 91, 'b': 93, 'n': 95, 'm': 96,
}
SHARP_ALIASES = {'!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                 '^': '6', '&': '7', '*': '8', '(': '9', ')': '0'}
SHIFT_SYMBOL_MAP = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6',
    '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', ':': ';', '"': "'",
    '<': ',', '>': '.', '?': '/', '|': '\\', '~': '`',
}


def _to_bool(v, default=False):
    """Надёжное приведение к bool — терпит строки 'true'/'false'/'0'/'1'."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ('1', 'true', 'yes', 'on', 'y', 'да')
    if isinstance(v, (int, float)):
        return bool(v)
    return default


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


# ─── AUTO TRANSPOSE ───
def analyze_song_range(song):
    if not song:
        return None
    notes = []
    i = 0
    while i < len(song):
        c = song[i]
        if c == TRANSPOSE_START:
            end = song.find(TRANSPOSE_END, i)
            i = end + 1 if end != -1 else i + 1
            continue
        if c == '[':
            end = song.find(']', i)
            if end == -1:
                i += 1
                continue
            for ch in song[i + 1:end]:
                n = key_to_midi(ch)
                if n is not None:
                    notes.append(n)
            i = end + 1
            continue
        n = key_to_midi(c)
        if n is not None:
            notes.append(n)
        i += 1
    if not notes:
        return None
    return (min(notes), max(notes))


def suggest_transpose(song, target_lo=48, target_hi=84):
    rng = analyze_song_range(song)
    if not rng:
        return None, None
    lo, hi = rng
    span = hi - lo
    target_center = (target_lo + target_hi) // 2
    song_center = (lo + hi) // 2
    tr = target_center - song_center
    if span > (target_hi - target_lo):
        return tr, (lo + tr, hi + tr)
    while lo + tr < target_lo:
        tr += 1
    while hi + tr > target_hi:
        tr -= 1
    return tr, (lo + tr, hi + tr)


# ─── DRAFT ───
def load_draft():
    try:
        if os.path.exists(DRAFT_FILE):
            with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""


def save_draft(text):
    try:
        if text and text.strip():
            with open(DRAFT_FILE, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            if os.path.exists(DRAFT_FILE):
                os.remove(DRAFT_FILE)
    except Exception as e:
        logger.error(f"save_draft: {e}")


# ─── PLAYLIST BACKUPS ───
def backup_playlist():
    try:
        if not os.path.exists(PLAYLIST_FILE):
            return
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(BACKUP_DIR, f"playlist_{ts}.json")
        shutil.copy2(PLAYLIST_FILE, dst)
        files = sorted(os.listdir(BACKUP_DIR))
        files = [f for f in files if f.startswith("playlist_")]
        for f in files[:-20]:
            try:
                os.remove(os.path.join(BACKUP_DIR, f))
            except Exception:
                pass
    except Exception as e:
        logger.error(f"backup_playlist: {e}")


# ─── HISTORY ───
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []


def save_history(hist):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist[-500:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_history: {e}")


# ─── SONG PROFILES ───
def load_profiles():
    try:
        if os.path.exists(SONG_PROFILES_FILE):
            with open(SONG_PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_profiles(p):
    try:
        with open(SONG_PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_profiles: {e}")


# ═══════════════════════════════════════════════════════════════════
#                         ANIMATED BUTTONS
# ═══════════════════════════════════════════════════════════════════

class HoverButton(QtWidgets.QPushButton):
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
                    blocksize=self.BLOCK_SIZE, callback=self._callback)
                self._stream.start()
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
                oldest = min(self._voices.items(),
                             key=lambda kv: kv[1]["start_frame"])[0]
                self._voices.pop(oldest, None)
            self._voices[note] = {"freq": freq, "start_frame": self._frame,
                                   "release_frame": None, "velocity": vel}

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
        except Exception:
            pass

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
                am = age < attack
                if np.any(am):
                    env[am] = age[am] / attack
                dm = (age >= attack) & (age < attack + decay)
                if np.any(dm):
                    env[dm] = 1.0 - (1.0 - sustain) * ((age[dm] - attack) / decay)
                if voice["release_frame"] is not None:
                    rel = (current_frame + n_arr - voice["release_frame"]) / self.sample_rate
                    rm = rel >= 0.0
                    if np.any(rm):
                        env = env * np.where(rm, np.exp(-8.0 * rel), 1.0)
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
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint |
                            QtCore.Qt.WindowType.FramelessWindowHint |
                            QtCore.Qt.WindowType.Tool)
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
        self.progress_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
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
        b.setStyleSheet(f"""QPushButton {{background: transparent; border: 1px solid {self.accent_color}55;
            border-radius: 6px; color: {self.text_color}; font-size: 13px;}}
            QPushButton:hover {{background: {self.highlight_bg}; border-color: {self.accent_color};}}""")
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
        self.pending_update = (song, current_pos, lines or self.lines, cpl or self.chars_per_line)

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
            text = re.sub(r'\x01(-?\d+)\x02', r' ⟨\1⟩ ', text)
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
                            chunks.append(cur); cur = ""
                        continue
                i += 1
                if len(cur) >= cpl:
                    chunks.append(cur); cur = ""
            if cur:
                chunks.append(cur)
            chunks = chunks[:lines]
            parts = []
            if chunks:
                first = chunks[0]
                if first:
                    parts.append(
                        f'<span style="background-color:{self.highlight_bg}; '
                        f'color:{self.text_color}; font-weight:bold; padding:0 3px; '
                        f'border-radius:3px; border:1px solid {self.accent_color};">'
                        f'{html.escape(first[0])}</span>'
                        f'<span style="color:{self.text_color};">{html.escape(first[1:])}</span>')
                for line in chunks[1:]:
                    parts.append(f'<span style="color:{self.text_color};">{html.escape(line)}</span>')
            self.note_label.setText("<br>".join(parts))
            self.pos_label.setText(f"{pos}/{len(song)}")
        except Exception as e:
            logger.error(f"overlay update: {e}")

    def apply_settings(self):
        self.note_label.setStyleSheet(f"""QLabel {{background: {self.bg_color}; color: {self.text_color};
            font-family: 'Consolas','Courier New',monospace; font-size: {self.font_size}px;
            border: 1px solid {self.accent_color}; border-radius: 8px; padding: 8px;}}""")
        self.song_title.setStyleSheet(f"color:{self.text_color};font-weight:bold;font-size:13px;background:transparent;")
        self.progress_label.setStyleSheet(f"color:{self.accent_color};font-size:12px;background:transparent;")
        self.status_label.setStyleSheet(f"color:{self.accent_color};font-size:11px;background:transparent;")
        self.pos_label.setStyleSheet(f"color:{self.text_color};font-size:11px;background:transparent;")
        self.progress_bar.setStyleSheet(f"""QProgressBar {{background: {self.bg_color};
            border: 1px solid {self.accent_color}66; border-radius: 4px; height: 8px;
            text-align: center; color: transparent;}}
            QProgressBar::chunk {{background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {self.accent_color}, stop:1 {self.text_color}); border-radius: 3px;}}""")

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
        self.font_size = s; self.apply_settings(); self.save_settings()

    def _set_lines(self, l):
        self.lines = l; self.save_settings()

    def reset_settings(self):
        self._apply_theme_from_current()
        self.opacity = 0.92; self.font_size = 18; self.lines = 4; self.chars_per_line = 50
        self.apply_settings(); self.save_settings()

    def show_with_fade(self):
        self.setWindowOpacity(0.0)
        super().show()
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(280); anim.setStartValue(0.0); anim.setEndValue(self.opacity)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        anim.start()

    def hide_with_fade(self):
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(220); anim.setStartValue(self.windowOpacity()); anim.setEndValue(0.0)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        anim.finished.connect(super().hide)
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
        a = m.addAction(tr('overlay.opacity_1pct')); a.setData(0.01)
        for v in range(5, 101, 5):
            a = m.addAction(f"{v}%"); a.setData(v / 100.0)
        act = m.exec(self.opacity_btn.mapToGlobal(QtCore.QPoint(0, self.opacity_btn.height())))
        if act:
            self.opacity = act.data()
            self.setWindowOpacity(self.opacity)
            self.save_settings()

    def closeEvent(self, e):
        self.save_settings(); self.hide(); e.ignore()


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
        rem = HoverButton(tr('pedal.remove')); rem.clicked.connect(self._rem)
        row2.addWidget(rem)
        rst = HoverButton(tr('pedal.reset')); rst.clicked.connect(self._reset)
        row2.addWidget(rst)
        v.addLayout(row2)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                         QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(tr('ui.ok'))
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText(tr('ui.cancel'))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _add(self):
        c = self.inp.text().strip()
        if c and len(c) == 1 and c not in self.bot.pedal_keys:
            self.bot.pedal_keys.add(c); self.list.addItem(c)
            self.inp.clear(); self._save()

    def _rem(self):
        r = self.list.currentRow()
        if r >= 0:
            k = self.list.takeItem(r).text()
            self.bot.pedal_keys.discard(k); self._save()

    def _reset(self):
        self.bot.pedal_keys = set(DEFAULT_PEDAL_KEYS)
        self.list.clear()
        for k in sorted(self.bot.pedal_keys):
            self.list.addItem(k)
        self._save()

    def _save(self):
        try:
            json.dump(list(self.bot.pedal_keys), open(PEDAL_FILE, "w", encoding="utf-8"))
        except Exception:
            pass

    def accept(self):
        self._save(); super().accept()


# ═══════════════════════════════════════════════════════════════════
#                     HOTKEY SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════════════

class HotkeySettingsDialog(QtWidgets.QDialog):
    ACTIONS = [
        ('toggle_play', 'F1 play/pause'),
        ('restart', 'F2 restart'),
        ('skip_fwd', 'F3 +25'),
        ('skip_back', 'F4 -25'),
        ('pause_playback', 'F5 pause'),
        ('freeze', 'F6 freeze'),
        ('next_mode', 'F7 mode'),
        ('next_song', 'F8 song'),
        ('stop', 'F9 stop'),
        ('last_rec', 'F10 last rec'),
        ('record', 'F12 record'),
        ('speed_up', 'Ctrl+Up speed +'),
        ('speed_down', 'Ctrl+Down speed -'),
    ]

    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('hotkeys.title'))
        self.setMinimumSize(460, 520)
        self._capturing = None
        v = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr('hotkeys.action'), tr('hotkeys.key'), ''])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(self.ACTIONS))
        for i, (action, label) in enumerate(self.ACTIONS):
            l = QtWidgets.QTableWidgetItem(label)
            l.setFlags(l.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, l)
            k = QtWidgets.QTableWidgetItem(self.bot.hotkeys.get(action, ""))
            k.setFlags(k.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, k)
            b = HoverButton(tr('hotkeys.change'))
            b.clicked.connect(lambda _, a=action, row=i: self._start_capture(a, row))
            self.table.setCellWidget(i, 2, b)
        v.addWidget(self.table)
        row = QtWidgets.QHBoxLayout()
        rst = HoverButton(tr('hotkeys.reset'))
        rst.clicked.connect(self._reset)
        row.addWidget(rst)
        row.addStretch()
        v.addLayout(row)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                         QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(tr('ui.ok'))
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText(tr('ui.cancel'))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def _start_capture(self, action, row):
        self._capturing = (action, row)
        self.grabKeyboard()

    def keyPressEvent(self, e):
        if self._capturing is None:
            super().keyPressEvent(e)
            return
        key = e.key()
        mods = e.modifiers()
        parts = []
        if mods & QtCore.Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if mods & QtCore.Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if mods & QtCore.Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        name = None
        if QtCore.Qt.Key.Key_F1 <= key <= QtCore.Qt.Key.Key_F35:
            name = f"f{key - QtCore.Qt.Key.Key_F1 + 1}"
        elif key == QtCore.Qt.Key.Key_Up: name = "up"
        elif key == QtCore.Qt.Key.Key_Down: name = "down"
        elif key == QtCore.Qt.Key.Key_Left: name = "left"
        elif key == QtCore.Qt.Key.Key_Right: name = "right"
        elif key == QtCore.Qt.Key.Key_Space: name = "space"
        elif key == QtCore.Qt.Key.Key_Escape:
            self.releaseKeyboard(); self._capturing = None; return
        elif QtCore.Qt.Key.Key_A <= key <= QtCore.Qt.Key.Key_Z:
            name = chr(key).lower()
        elif QtCore.Qt.Key.Key_0 <= key <= QtCore.Qt.Key.Key_9:
            name = chr(key)
        if name:
            combo = "+".join(parts + [name]) if parts else name
            action, row = self._capturing
            self.bot.hotkeys[action] = combo
            self.table.item(row, 1).setText(combo)
            self._capturing = None
            self.releaseKeyboard()

    def _reset(self):
        self.bot.hotkeys = dict(DEFAULT_HOTKEYS)
        for i, (action, _) in enumerate(self.ACTIONS):
            self.table.item(i, 1).setText(self.bot.hotkeys.get(action, ""))

    def accept(self):
        save_hotkeys(self.bot.hotkeys)
        super().accept()


# ═══════════════════════════════════════════════════════════════════
#                     PLAY HISTORY DIALOG
# ═══════════════════════════════════════════════════════════════════

class PlayHistoryDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('history.title'))
        self.setMinimumSize(560, 480)
        v = QtWidgets.QVBoxLayout(self)
        self.list = QtWidgets.QListWidget()
        v.addWidget(self.list)
        row = QtWidgets.QHBoxLayout()
        clr = HoverButton(tr('history.clear'))
        clr.setProperty("role", "danger")
        clr.clicked.connect(self._clear)
        row.addWidget(clr)
        row.addStretch()
        v.addLayout(row)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText(tr('ui.close'))
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._refresh()

    def _refresh(self):
        self.list.clear()
        for entry in reversed(self.bot.play_history[-300:]):
            name = entry.get("name", "?")
            start = entry.get("start", "")
            dur = entry.get("duration", 0)
            try:
                dt = datetime.fromisoformat(start)
                ts = dt.strftime("%d.%m %H:%M")
            except Exception:
                ts = start
            if dur > 0:
                text = f"{ts} — {name}  ·  {tr('history.stopped_after')} {int(dur)}с"
            else:
                text = f"{ts} — {name}"
            self.list.addItem(text)
        if self.list.count() == 0:
            self.list.addItem(tr('history.empty'))

    def _clear(self):
        self.bot.play_history = []
        save_history(self.bot.play_history)
        self._refresh()


# ═══════════════════════════════════════════════════════════════════
#                     CUSTOM THEME DIALOG
# ═══════════════════════════════════════════════════════════════════

class CustomThemeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('theme_custom.title'))
        self.setMinimumSize(360, 240)
        v = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.acc_btn = self._color_button("#d4af37")
        self.bg_btn = self._color_button("#0a0a0a")
        self.text_btn = self._color_button("#f5f3f1")
        form.addRow(tr('theme_custom.accent'), self.acc_btn)
        form.addRow(tr('theme_custom.bg'), self.bg_btn)
        form.addRow(tr('theme_custom.text'), self.text_btn)
        v.addLayout(form)
        v.addStretch()
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                         QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(tr('theme_custom.apply'))
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText(tr('ui.cancel'))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _color_button(self, initial):
        b = HoverButton(initial)
        b._color = initial
        b.clicked.connect(lambda: self._pick(b))
        b.setStyleSheet(f"background: {initial}; color: {initial}; min-height: 28px;")
        return b

    def _pick(self, btn):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(btn._color), self)
        if c.isValid():
            hx = c.name()
            btn._color = hx
            btn.setText(hx)
            btn.setStyleSheet(f"background: {hx}; color: {hx}; min-height: 28px;")

    def get_colors(self):
        return self.acc_btn._color, self.bg_btn._color, self.text_btn._color


# ═══════════════════════════════════════════════════════════════════
#                     SONG PROFILE DIALOG
# ═══════════════════════════════════════════════════════════════════

class SongProfileDialog(QtWidgets.QDialog):
    def __init__(self, bot, song_name, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.song_name = song_name
        self.setWindowTitle(tr('profile.title'))
        self.setMinimumSize(360, 300)
        v = QtWidgets.QVBoxLayout(self)
        self.use_chk = QtWidgets.QCheckBox(tr('profile.use'))
        v.addWidget(self.use_chk)
        form = QtWidgets.QFormLayout()
        self.mode_cb = QtWidgets.QComboBox()
        self.mode_cb.addItems([tr('settings.mode1'), tr('settings.mode2')])
        form.addRow(tr('settings.mode_label'), self.mode_cb)
        self.bpm = QtWidgets.QSpinBox(); self.bpm.setRange(0, 1000)
        form.addRow(tr('settings.bpm'), self.bpm)
        self.transpose = QtWidgets.QSpinBox(); self.transpose.setRange(-24, 24)
        form.addRow(tr('settings.transpose_initial'), self.transpose)
        self.speed = QtWidgets.QDoubleSpinBox()
        self.speed.setRange(0.5, 2.0); self.speed.setSingleStep(0.05); self.speed.setDecimals(2)
        form.addRow(tr('settings.speed'), self.speed)
        v.addLayout(form)
        v.addStretch()
        row = QtWidgets.QHBoxLayout()
        save_btn = HoverButton(tr('profile.save'))
        save_btn.setProperty("role", "primary")
        save_btn.clicked.connect(self._save)
        row.addWidget(save_btn)
        del_btn = HoverButton(tr('profile.delete'))
        del_btn.setProperty("role", "danger")
        del_btn.clicked.connect(self._delete)
        row.addWidget(del_btn)
        row.addStretch()
        v.addLayout(row)
        self._load()

    def _load(self):
        p = self.bot.song_profiles.get(self.song_name)
        if p:
            self.use_chk.setChecked(True)
            self.mode_cb.setCurrentIndex(max(0, min(1, p.get("mode", 1) - 1)))
            self.bpm.setValue(p.get("bpm", self.bot.bpm))
            self.transpose.setValue(p.get("transpose", self.bot.initial_transpose))
            self.speed.setValue(p.get("speed", self.bot.speed))
        else:
            self.bpm.setValue(self.bot.bpm)
            self.transpose.setValue(self.bot.initial_transpose)
            self.speed.setValue(self.bot.speed)

    def _save(self):
        if self.use_chk.isChecked():
            self.bot.song_profiles[self.song_name] = {
                "mode": self.mode_cb.currentIndex() + 1,
                "bpm": self.bpm.value(),
                "transpose": self.transpose.value(),
                "speed": self.speed.value(),
            }
        else:
            self.bot.song_profiles.pop(self.song_name, None)
        save_profiles(self.bot.song_profiles)
        self.accept()

    def _delete(self):
        self.bot.song_profiles.pop(self.song_name, None)
        save_profiles(self.bot.song_profiles)
        self.accept()


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

        self.initial_transpose = 0
        self.current_transpose = 0
        self.bpm = 120
        self.speed = 1.0
        self.hotkeys = load_hotkeys()
        self.song_profiles = load_profiles()
        self.play_history = load_history()
        self._play_start_time = None
        self._micro_desync_ms = 12

        self.load_pedal_settings()
        self.recordings_index = []
        self.load_recordings_index()
        self.load_app_settings()
        self.current_transpose = self.initial_transpose

        logger.info(f"Bot initialized. auto_play_no_pedal={self.auto_play_no_pedal}")
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
                self.check_updates_on_start = _to_bool(s.get("check_updates_on_start"), False)
                self.midi_out_enabled = _to_bool(s.get("midi_out_enabled"), False)
                self.midi_port_name = s.get("midi_port_name", "")
                self.audio_enabled = _to_bool(s.get("audio_enabled"), False) and HAS_AUDIO
                self.audio_volume = float(s.get("audio_volume", 0.7))
                self.auto_play_no_pedal = _to_bool(s.get("auto_play_no_pedal"), default=True)
                self.auto_hold_ms = int(s.get("auto_hold_ms", 180))
                self.initial_transpose = int(s.get("initial_transpose", 0))
                self.bpm = int(s.get("bpm", 120))
                self.speed = float(s.get("speed", 1.0))
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
                "max_delay": self.max_note_delay,
                "lang": tr_obj.lang, "theme": _current_theme_key,
                "check_updates_on_start": bool(self.check_updates_on_start),
                "midi_out_enabled": bool(self.midi_out_enabled),
                "midi_port_name": self.midi_port_name,
                "audio_enabled": bool(self.audio_enabled),
                "audio_volume": self.audio_volume,
                "auto_play_no_pedal": bool(self.auto_play_no_pedal),
                "auto_hold_ms": self.auto_hold_ms,
                "initial_transpose": self.initial_transpose,
                "bpm": self.bpm,
                "speed": self.speed,
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
        except Exception:
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
        if not song:
            return song
        if song.startswith(TIMED_MARKER):
            return song
        song = preprocess_song_text(song)
        if is_timed_note_text(song):
            return TIMED_MARKER + song
        allowed = set(ROBLOX_KEYS + " \t\r[]" + TRANSPOSE_START + TRANSPOSE_END)
        song = ''.join(ch for ch in song if ch in allowed)
        song = song.replace("'", "")
        return song

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

    def _wait_until(self, deadline, cancel_fn=None):
        """
        Эффективное ожидание до момента deadline (time.perf_counter()).
        cancel_fn() -> bool; True — выходим досрочно.
        Прогрессивный sleep: 5 мс / 2 мс / 0.5 мс вместо busy-wait 1 мс.
        """
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return
            if cancel_fn and cancel_fn():
                return
            if remaining > 0.05:
                time.sleep(0.005)
            elif remaining > 0.01:
                time.sleep(0.002)
            else:
                time.sleep(0.0005)

    def _handle_transpose(self, target):
        if target is None:
            return
        try:
            target = int(target)
        except Exception:
            return
        diff = target - int(self.current_transpose)
        if diff == 0:
            return
        logger.info(f"Transpose {self.current_transpose} -> {target} ({diff:+d})")
        if not self.keyboard:
            self.current_transpose = target
            self._gui_update()
            return
        arrow = Key.up if diff > 0 else Key.down
        steps = abs(diff)
        press_hold = 0.002
        gap = 0.004
        try:
            for _ in range(steps):
                self.keyboard.press(arrow)
                time.sleep(press_hold)
                self.keyboard.release(arrow)
                time.sleep(gap)
        except Exception as e:
            logger.error(f"Transpose press error: {e}")
        self.current_transpose = target
        self._gui_update()

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
        """
        Нажатие ноты/аккорда. Аккорд ВСЕГДА играется целиком —
        все ноты нажимаются одновременно, независимо от режима.
        """
        if not chord:
            return
        for k in chord:
            self.press_key(k)

    def release_chord(self, chord):
        """Отпускание — все ноты одновременно (в обратном порядке)."""
        if not chord:
            return
        for k in reversed(chord):
            self.release_key(k)

    def _log_play_start(self):
        self._play_start_time = time.time()

    def _log_play_end(self):
        if self._play_start_time is None:
            return
        dur = time.time() - self._play_start_time
        self._play_start_time = None
        if dur < 1.0:
            return
        entry = {
            "name": self.song_name or "?",
            "start": datetime.now().isoformat(),
            "duration": round(dur, 1),
        }
        self.play_history.append(entry)
        save_history(self.play_history)

    def next_song(self):
        n = len(self.playlist)
        if n == 0:
            return
        self._log_play_end()
        old = self.song_index
        for _ in range(n):
            self.song_index = (self.song_index + 1) % n
            if self.playlist[self.song_index][1]:
                self.song_name, self.song = self.playlist[self.song_index]
                self.note_index = 0
                self.frozen_note_index = 0
                self.progress = 0
                self._apply_song_profile()
                if self.current_transpose != self.initial_transpose:
                    self._handle_transpose(self.initial_transpose)
                else:
                    self.current_transpose = self.initial_transpose
                self._gui_update()
                return
        self.song_index = old

    def _apply_song_profile(self):
        p = self.song_profiles.get(self.song_name)
        if not p:
            return
        self.mode = int(p.get("mode", self.mode))
        self.bpm = int(p.get("bpm", self.bpm))
        self.initial_transpose = int(p.get("transpose", self.initial_transpose))
        self.current_transpose = self.initial_transpose
        self.speed = float(p.get("speed", self.speed))

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
            'max_delay': self.max_note_delay,
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
        speed = max(0.1, self.speed)
        for ev in self.playback_events:
            if self.playback_stop:
                break
            ev_time = ev['time'] / speed
            if self.playback_limit and ev_time > self.playback_limit:
                break
            target = start + ev_time + self.playback_elapsed
            while time.time() < target - 0.001:
                if self.playback_stop:
                    break
                if self.playback_paused:
                    self.playback_elapsed += time.time() - self.playback_pause_time
                    self.playback_pause_time = time.time()
                    target = start + ev_time + self.playback_elapsed
                    time.sleep(0.05)
                    continue
                remaining = target - time.time()
                if remaining > 0.05:
                    time.sleep(0.005)
                elif remaining > 0.01:
                    time.sleep(0.002)
                else:
                    time.sleep(0.0005)
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
        if self.song[idx] == TRANSPOSE_START:
            end = self.song.find(TRANSPOSE_END, idx)
            return end + 1 if end != -1 else idx + 1
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
        if self.song[i] == TRANSPOSE_END:
            start = self.song.rfind(TRANSPOSE_START, 0, i)
            return start if start != -1 else i
        if self.song[i] == ']':
            start = self.song.rfind('[', 0, i)
            return start if start != -1 else i
        return i

    def _hold_time_seconds(self):
        """Длительность удержания ноты: 60/BPM сек (или auto_hold_ms, если BPM=0)."""
        if self.bpm > 0:
            base = 60.0 / float(self.bpm)
        else:
            base = self.auto_hold_ms / 1000.0
        base /= max(0.1, self.speed)
        return max(0.02, base)

    def play_song(self):
        time.sleep(0.5)
        current_chord = None
        while True:
            try:
                if self.song.startswith(TIMED_MARKER):
                    time.sleep(0.1)
                    continue

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
                    if self.current_transpose != self.initial_transpose:
                        self._handle_transpose(self.initial_transpose)
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
                    if self.current_transpose != self.initial_transpose:
                        self._handle_transpose(self.initial_transpose)
                    self._log_play_end()
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
                if char == TRANSPOSE_START:
                    end = self.song.find(TRANSPOSE_END, self.note_index)
                    if end == -1:
                        self.note_index += 1
                        continue
                    try:
                        target = int(self.song[self.note_index + 1:end])
                    except ValueError:
                        target = None
                    self.note_index = end + 1
                    if self.playing and not self.freeze_note:
                        self._handle_transpose(target)
                    if self.song:
                        self.progress = int(self.note_index * 100 / len(self.song))
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
                self._record_event(chord, "press")
                self.play_chord(chord)
                current_chord = chord

                if self.hold_star:
                    while (self.hold_star and self.playing
                           and not self.restart and not self.freeze_note):
                        time.sleep(0.002)
                elif self.auto_play_no_pedal:
                    hold_seconds = self._hold_time_seconds()
                    deadline = time.perf_counter() + hold_seconds
                    self._wait_until(
                        deadline,
                        lambda: (not self.playing) or self.restart
                                or self.freeze_note or self.hold_star,
                    )
                    if self.hold_star:
                        while (self.hold_star and self.playing
                               and not self.restart and not self.freeze_note):
                            time.sleep(0.002)

                if current_chord:
                    self._record_event(current_chord, "release")
                    self.release_chord(current_chord)
                    current_chord = None
                self.note_index = next_idx
                if self.song:
                    self.progress = int(self.note_index * 100 / len(self.song))
                self._gui_update()

                if (self.mode == 2 and self.playing
                        and not self.restart and not self.freeze_note):
                    gap = self.get_random_delay()
                    if gap > 0:
                        deadline = time.perf_counter() + gap
                        self._wait_until(
                            deadline,
                            lambda: (not self.playing) or self.restart
                                    or self.freeze_note,
                        )
                time.sleep(0.0005)
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(0.05)

    # ─── Timed toggle ───
    def toggle_play_smart(self):
        """
        Универсальный Play/Pause.
        • timed-формат → timing-движок (playback) с абсолютными временами;
        • обычный текст → BPM-режим (или ожидание педали).
        """
        if self.song.startswith(TIMED_MARKER):
            if self.is_playback:
                self.stop_playback()
                return
            content = self.song[len(TIMED_MARKER):]
            events = parse_timed_note_text(content)
            if events:
                self.playback_events = events
                self._preview_active = False
                self.start_playback()
                return
            logger.warning("Timed song but no events parsed — fallback to text engine")
        if not self.playing:
            self._log_play_start()
            self.current_transpose = self.initial_transpose
        self.playing = not self.playing
        if self.playing and not self.is_playback:
            activate_roblox_window()

    def listen_keys(self):
        def on_press(key):
            try:
                key_char = getattr(key, 'char', None)
                if hasattr(key, 'name') and key.name:
                    base = key.name
                elif key_char:
                    base = key_char.lower()
                else:
                    base = None
                if base is None:
                    return
                matched_action = None
                for action, combo in self.hotkeys.items():
                    if not combo:
                        continue
                    combo_parts = combo.lower().split("+")
                    req_ctrl = "ctrl" in combo_parts
                    req_alt = "alt" in combo_parts
                    main = combo_parts[-1]
                    if main != base:
                        continue
                    if req_ctrl or req_alt:
                        continue
                    matched_action = action
                    break

                if matched_action == "toggle_play":
                    self.toggle_play_smart()
                    self._gui_update()
                elif matched_action == "restart":
                    self.restart = True
                elif matched_action == "skip_fwd":
                    self.skip_notes += 25
                elif matched_action == "skip_back":
                    self.skip_notes -= 25
                elif matched_action == "pause_playback":
                    self.toggle_playback_pause()
                elif matched_action == "freeze":
                    self.freeze_note = not self.freeze_note
                    if self.freeze_note:
                        self.frozen_note_index = self.note_index
                    self._gui_update()
                elif matched_action == "next_mode":
                    self.mode = 2 if self.mode == 1 else 1
                    self.save_app_settings()
                    self._gui_update()
                elif matched_action == "next_song":
                    self.next_song()
                elif matched_action == "stop":
                    self.stop_playback()
                elif matched_action == "last_rec":
                    self._play_latest_recording()
                elif matched_action == "record":
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
        self.sort_combo.addItems([tr('recordings.sort_new'), tr('recordings.sort_old'),
                                   tr('recordings.sort_az'), tr('recordings.sort_za'),
                                   tr('recordings.sort_dur'), tr('recordings.sort_fav')])
        self.sort_combo.currentIndexChanged.connect(self.refresh_list)
        top_row.addWidget(self.sort_combo)
        layout.addLayout(top_row)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.refresh_list()
        layout.addWidget(self.list_widget)
        row = QtWidgets.QHBoxLayout()
        for text, slot in [(tr('recordings.preview'), self.preview_selected),
                            (tr('recordings.favorite'), self.toggle_favorite),
                            (tr('recordings.rename'), self.rename_selected),
                            (tr('recordings.editor'), self.open_editor),
                            (tr('recordings.delete'), self.delete_selected)]:
            b = HoverButton(text); b.clicked.connect(slot); row.addWidget(b)
        layout.addLayout(row)
        row2 = QtWidgets.QHBoxLayout()
        for text, slot in [(tr('recordings.export_zip'), self.export_recordings_zip),
                            (tr('recordings.import_zip'), self.import_recordings_zip),
                            (tr('recordings.open_folder'), self.open_recordings_folder),
                            (tr('recordings.clean'), self.clean_non_favorite)]:
            b = HoverButton(text); b.clicked.connect(slot); row2.addWidget(b)
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
        if sort_mode == 0: indexed.sort(key=lambda ie: ie[1].get('date', ''), reverse=True)
        elif sort_mode == 1: indexed.sort(key=lambda ie: ie[1].get('date', ''))
        elif sort_mode == 2: indexed.sort(key=lambda ie: ie[1].get('name', '').lower())
        elif sort_mode == 3: indexed.sort(key=lambda ie: ie[1].get('name', '').lower(), reverse=True)
        elif sort_mode == 4: indexed.sort(key=lambda ie: ie[1].get('duration', 0), reverse=True)
        elif sort_mode == 5: indexed.sort(key=lambda ie: (not ie[1].get('favorite', False),
                                                           ie[1].get('date', '')))
        for idx, entry in indexed:
            name = entry.get('name', 'Untitled'); date = entry.get('date', '')
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
            self, tr('recordings.rename'), tr('songs.new_name'), text=entry.get('name', ''))
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        existing = {e.get('name', '') for i, e in enumerate(self.bot.recordings_index) if i != idx}
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
            self, tr('ui.confirm'), tr('recordings.confirm_delete', name=entry.get('name')),
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
            self, tr('ui.confirm'), tr('recordings.confirm_clean', n=len(to_delete)),
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
                if not json_file or not os.path.exists(os.path.join("recordings", json_file)):
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
#                       RECORDING EDITOR V2
# ═══════════════════════════════════════════════════════════════════

class RecordingEditorDialog(QtWidgets.QDialog):
    def __init__(self, bot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.setWindowTitle(tr('editor.title'))
        self.setMinimumSize(760, 620)
        self._entries = list(self.bot.recordings_index)
        self._working_events = None
        self._undo_stack = []
        self._redo_stack = []
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._edit_tab(), tr('editor.title'))
        tabs.addTab(self._concat_tab(), tr('editor.concat'))
        layout.addWidget(tabs)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        bb.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText(tr('ui.close'))
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _edit_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)

        v.addWidget(QtWidgets.QLabel(tr('editor.select')))
        self.edit_combo = QtWidgets.QComboBox()
        self._fill_combo(self.edit_combo)
        self.edit_combo.currentIndexChanged.connect(self._on_edit_changed)
        v.addWidget(self.edit_combo)

        self.edit_info = QtWidgets.QLabel("—")
        v.addWidget(self.edit_info)

        tools = QtWidgets.QHBoxLayout()
        self.undo_btn = HoverButton(tr('editor.undo'))
        self.undo_btn.clicked.connect(self._undo)
        tools.addWidget(self.undo_btn)
        self.redo_btn = HoverButton(tr('editor.redo'))
        self.redo_btn.clicked.connect(self._redo)
        tools.addWidget(self.redo_btn)
        tools.addStretch()
        self.save_changes_btn = HoverButton(tr('editor.save_changes'))
        self.save_changes_btn.setProperty("role", "primary")
        self.save_changes_btn.clicked.connect(self._save_changes)
        tools.addWidget(self.save_changes_btn)
        v.addLayout(tools)

        off_row = QtWidgets.QHBoxLayout()
        off_row.addWidget(QtWidgets.QLabel(tr('editor.offset')))
        self.offset_spin = QtWidgets.QDoubleSpinBox()
        self.offset_spin.setRange(-60.0, 60.0)
        self.offset_spin.setDecimals(2)
        self.offset_spin.setSingleStep(0.05)
        off_row.addWidget(self.offset_spin)
        apply_off = HoverButton("±")
        apply_off.clicked.connect(self._apply_offset)
        off_row.addWidget(apply_off)
        v.addLayout(off_row)

        q_row = QtWidgets.QHBoxLayout()
        q_row.addWidget(QtWidgets.QLabel(tr('editor.quantize')))
        self.quantize_combo = QtWidgets.QComboBox()
        self.quantize_combo.addItems(["1/4", "1/8", "1/16", "1/32"])
        q_row.addWidget(self.quantize_combo)
        q_apply = HoverButton(tr('editor.quantize_btn'))
        q_apply.clicked.connect(self._apply_quantize)
        q_row.addWidget(q_apply)
        v.addLayout(q_row)

        v.addWidget(QtWidgets.QLabel(tr('editor.notes')))
        self.notes_list = QtWidgets.QListWidget()
        v.addWidget(self.notes_list, 1)

        del_row = QtWidgets.QHBoxLayout()
        del_note = HoverButton(tr('editor.delete_note'))
        del_note.setProperty("role", "danger")
        del_note.clicked.connect(self._delete_note)
        del_row.addWidget(del_note)
        del_row.addStretch()
        v.addLayout(del_row)

        self._on_edit_changed(0)
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
                    reconstructed.append({'time': press_time, 'key': ev['key'], 'action': 'press'})
                    reconstructed.append({'time': ev['time'], 'key': ev['key'], 'action': 'release'})
                events = sorted(reconstructed, key=lambda e: e['time'])
            return events
        except Exception as e:
            logger.error(f"Editor load error: {e}")
            return None

    def _on_edit_changed(self, idx):
        if idx < 0 or idx >= len(self._entries):
            self._working_events = None
            return
        self._working_events = self._load_events(self._entries[idx]['json_file'])
        self._undo_stack = []
        self._redo_stack = []
        self._refresh_note_list()

    def _refresh_note_list(self):
        self.notes_list.clear()
        if not self._working_events:
            self.edit_info.setText("—")
            return
        last_t = max((e['time'] for e in self._working_events), default=0.0)
        self.edit_info.setText(f"{tr('editor.duration')}: {last_t:.2f}s  ·  нот: {len(self._working_events)}")
        for i, ev in enumerate(self._working_events):
            t = ev.get('time', 0)
            k = ev.get('key', '')
            a = ev.get('action', '')
            mark = "▶" if a == "press" else "■"
            self.notes_list.addItem(f"{i:4d}  {t:7.3f}s  {mark}  {k}")

    def _push_undo(self):
        if self._working_events is not None:
            self._undo_stack.append([dict(e) for e in self._working_events])
            self._redo_stack = []
            if len(self._undo_stack) > 50:
                self._undo_stack.pop(0)

    def _undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append([dict(e) for e in self._working_events])
        self._working_events = self._undo_stack.pop()
        self._refresh_note_list()

    def _redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append([dict(e) for e in self._working_events])
        self._working_events = self._redo_stack.pop()
        self._refresh_note_list()

    def _apply_offset(self):
        if not self._working_events:
            return
        self._push_undo()
        off = self.offset_spin.value()
        for e in self._working_events:
            e['time'] = round(max(0.0, e['time'] + off), 3)
        self._working_events.sort(key=lambda e: e['time'])
        self._refresh_note_list()

    def _apply_quantize(self):
        if not self._working_events:
            return
        self._push_undo()
        grid_map = {"1/4": 0.25, "1/8": 0.125, "1/16": 0.0625, "1/32": 0.03125}
        grid = grid_map.get(self.quantize_combo.currentText(), 0.125)
        for e in self._working_events:
            e['time'] = round(round(e['time'] / grid) * grid, 3)
        self._working_events.sort(key=lambda e: e['time'])
        self._refresh_note_list()

    def _delete_note(self):
        row = self.notes_list.currentRow()
        if row < 0 or not self._working_events:
            return
        self._push_undo()
        self._working_events.pop(row)
        self._refresh_note_list()

    def _save_changes(self):
        if not self._working_events:
            return
        idx = self.edit_combo.currentIndex()
        if idx < 0:
            return
        entry = self._entries[idx]
        name, ok = QtWidgets.QInputDialog.getText(
            self, tr('ui.save'), tr('songs.new_name'),
            text=f"{entry.get('name', 'Rec')}")
        if not ok or not name.strip():
            return
        saved = self.bot.save_recording_events(name.strip(), self._working_events)
        if saved:
            self._entries = list(self.bot.recordings_index)
            self._fill_combo(self.edit_combo)
            self._fill_combo(self.cat_combo_a)
            self._fill_combo(self.cat_combo_b)

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
                extra = [{'time': round(last_t + 0.05, 3), 'key': k, 'action': 'release'}
                         for k in pending.keys()]
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
            text=f"{self._entries[ia].get('name', 'A')} + {self._entries[ib].get('name', 'B')}")
        if not ok or not name.strip():
            return
        saved = self.bot.save_recording_events(name.strip(), merged)
        if saved:
            self._entries = list(self.bot.recordings_index)
            self._fill_combo(self.edit_combo)
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
        cp.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.text_edit.toPlainText()))
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
        self._status_flash_effect = None

        self._update_requested.connect(self.on_state_changed, QtCore.Qt.ConnectionType.QueuedConnection)
        self.bot.set_gui_update_callback(self._update_requested.emit)

        self.setWindowTitle(tr('app.title'))
        self.setWindowOpacity(0.0)
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() // 2 - 480, screen.height() // 2 - 420, 960, 800)
        self.load_window_state()

        self._build()
        self._update_mode_ui()

        self.overlay_window = NoteOverlayWindow(bot=self.bot, parent_gui=self)
        self.bot.set_overlay_window(self.overlay_window)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(150)

        self.draft_timer = QtCore.QTimer()
        self.draft_timer.timeout.connect(self._autosave_draft)
        self.draft_timer.start(2000)

        self.load_playlist()
        self._refresh_midi_ports()
        if self.bot.midi_out_enabled and self.bot.midi_port_name:
            ok, err = self.bot.open_midi_port(self.bot.midi_port_name)
            if ok:
                self.midi_status_label.setText(tr('midi.connected', name=self.bot.midi_port_name))
            else:
                self.bot.midi_out_enabled = False
                self.midi_enable_check.setChecked(False)
                self.midi_status_label.setText(tr('midi.error'))

        QtCore.QTimer.singleShot(80, self._fade_in)
        QtCore.QTimer.singleShot(600, self._restore_draft_if_any)
        QtCore.QTimer.singleShot(2000, self._auto_check_updates_if_enabled)

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
        anim.setDuration(420); anim.setStartValue(0.0); anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._keep_anim(anim)

    def _animate_theme(self, target_key, duration=260):
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
        anim.setStartValue(0.0); anim.setEndValue(1.0)
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

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tb = QtWidgets.QFrame()
        tb.setObjectName("titlebar"); tb.setFixedHeight(46)
        tbl = QtWidgets.QHBoxLayout(tb)
        tbl.setContentsMargins(18, 0, 14, 0); tbl.setSpacing(8)
        title = QtWidgets.QLabel("AstraKeys"); title.setObjectName("app_title")
        tbl.addWidget(title); tbl.addStretch()

        self.theme_btn = self._icon_btn("🎨", 'titlebar.theme_tooltip')
        self.theme_btn.clicked.connect(self._cycle_theme)
        tbl.addWidget(self.theme_btn)

        self.custom_theme_btn = self._icon_btn("🖌", 'titlebar.custom_theme')
        self.custom_theme_btn.clicked.connect(self._open_custom_theme)
        tbl.addWidget(self.custom_theme_btn)

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

        accent = QtWidgets.QFrame(); accent.setObjectName("accent_line"); accent.setFixedHeight(1)
        root.addWidget(accent)

        body = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(body)
        bl.setContentsMargins(16, 14, 16, 14); bl.setSpacing(16)

        left = QtWidgets.QVBoxLayout(); left.setSpacing(8)
        self._lbl('playlist.section', left, obj_name='section_label')
        self.song_list = QtWidgets.QListWidget()
        self.song_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.song_list.model().rowsMoved.connect(self.handle_rows_moved)
        self.song_list.currentRowChanged.connect(self._on_song_selected)
        left.addWidget(self.song_list, 1)
        pl_btns = QtWidgets.QHBoxLayout(); pl_btns.setSpacing(4)
        for sym, key, cb in [("＋", 'playlist.add_tooltip', self.add_song),
                             ("🗑", 'playlist.remove_tooltip', self.remove_song),
                             ("✏", 'playlist.rename_tooltip', self.rename_song),
                             ("💾", 'playlist.save_tooltip', self.save_playlist),
                             ("📂", 'playlist.load_tooltip', self.load_playlist_dialog)]:
            b = self._icon_btn(sym, key); b.clicked.connect(cb); pl_btns.addWidget(b)
        pl_btns.addStretch()
        left.addLayout(pl_btns)

        left_row_a = QtWidgets.QHBoxLayout()
        self.manage_btn = self._tr_btn('playlist.manage_recordings')
        self.manage_btn.clicked.connect(self.open_recordings_manager)
        left_row_a.addWidget(self.manage_btn)
        self.overlay_btn = self._tr_btn('playlist.overlay')
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        left_row_a.addWidget(self.overlay_btn)
        left.addLayout(left_row_a)

        left_row_b = QtWidgets.QHBoxLayout()
        self.history_btn = self._tr_btn('playlist.history')
        self.history_btn.clicked.connect(self.open_history)
        left_row_b.addWidget(self.history_btn)
        self.hotkeys_btn = self._tr_btn('playlist.hotkeys')
        self.hotkeys_btn.clicked.connect(self.open_hotkeys)
        left_row_b.addWidget(self.hotkeys_btn)
        left.addLayout(left_row_b)

        self.profile_btn = self._tr_btn('playlist.profile', left)
        self.profile_btn.clicked.connect(self.open_song_profile)

        bl.addLayout(left, 3)

        right = QtWidgets.QVBoxLayout(); right.setSpacing(8)
        self._lbl('player.section', right, obj_name='section_label')
        self.song_input = QtWidgets.QTextEdit()
        self.song_input.setPlaceholderText(tr('player.input_placeholder'))
        self.song_input.setFixedHeight(60)
        self._i18n_widgets.setdefault('player.input_placeholder', []).append(('placeholder', self.song_input))
        right.addWidget(self.song_input)
        self.song_display = QtWidgets.QTextEdit()
        self.song_display.setObjectName("song_display")
        self.song_display.setReadOnly(True)
        self.song_display.setFixedHeight(76)
        right.addWidget(self.song_display)

        transport = QtWidgets.QHBoxLayout(); transport.setSpacing(6)
        self.play_btn = HoverButton("▶")
        self.play_btn.setProperty("role", "primary")
        self.play_btn.setFixedHeight(36); self.play_btn.setMinimumWidth(100)
        self.play_btn.setToolTip(tr('player.start_tooltip'))
        self._i18n_widgets.setdefault('player.start_tooltip', []).append(('tooltip', self.play_btn))
        self.play_btn.clicked.connect(self.toggle_play)
        transport.addWidget(self.play_btn)

        self.rec_btn = QtWidgets.QPushButton("●")
        self.rec_btn.setProperty("role", "icon")
        self.rec_btn.setFixedHeight(36); self.rec_btn.setMinimumWidth(110)
        self.rec_btn.setToolTip(tr('player.record_tooltip'))
        self._i18n_widgets.setdefault('player.record_tooltip', []).append(('tooltip', self.rec_btn))
        self.rec_btn.clicked.connect(self.toggle_recording)
        transport.addWidget(self.rec_btn)

        self.playback_btn = HoverButton("🎵")
        self.playback_btn.setProperty("role", "icon")
        self.playback_btn.setFixedSize(40, 36)
        self.playback_btn.setToolTip(tr('player.playback_tooltip'))
        self._i18n_widgets.setdefault('player.playback_tooltip', []).append(('tooltip', self.playback_btn))
        self.playback_btn.clicked.connect(self.load_and_play)
        transport.addWidget(self.playback_btn)

        self.stop_btn = HoverButton("■")
        self.stop_btn.setProperty("role", "icon")
        self.stop_btn.setFixedSize(40, 36)
        self.stop_btn.setToolTip(tr('player.stop_playback_tooltip'))
        self._i18n_widgets.setdefault('player.stop_playback_tooltip', []).append(('tooltip', self.stop_btn))
        self.stop_btn.clicked.connect(self.bot.stop_playback)
        self.stop_btn.hide()
        transport.addWidget(self.stop_btn)

        self.pause_btn = HoverButton("⏸")
        self.pause_btn.setProperty("role", "icon")
        self.pause_btn.setFixedHeight(36); self.pause_btn.setMinimumWidth(110)
        self.pause_btn.setToolTip(tr('player.pause_tooltip'))
        self._i18n_widgets.setdefault('player.pause_tooltip', []).append(('tooltip', self.pause_btn))
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

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._settings_tab(), tr('settings.tab_params'))
        self.tabs.addTab(self._midi_tab(), tr('settings.tab_midi'))
        right.addWidget(self.tabs, 1)
        bl.addLayout(right, 5)
        root.addWidget(body, 1)

        sb = QtWidgets.QFrame(); sb.setFixedHeight(26)
        sbl = QtWidgets.QHBoxLayout(sb); sbl.setContentsMargins(18, 0, 18, 0)
        self.status_label = QtWidgets.QLabel(tr('status.idle'))
        self.status_label.setObjectName("status_accent")
        sbl.addWidget(self.status_label)
        self.mode_lbl = QtWidgets.QLabel(""); self.mode_lbl.setObjectName("status_normal")
        sbl.addWidget(self.mode_lbl)
        self.tr_lbl = QtWidgets.QLabel(""); self.tr_lbl.setObjectName("status_normal")
        sbl.addWidget(self.tr_lbl)
        self.spd_lbl = QtWidgets.QLabel(""); self.spd_lbl.setObjectName("status_normal")
        sbl.addWidget(self.spd_lbl)
        self.auto_lbl = QtWidgets.QLabel(""); self.auto_lbl.setObjectName("status_normal")
        sbl.addWidget(self.auto_lbl)
        sbl.addStretch()
        self.pos_lbl = QtWidgets.QLabel("0/0"); self.pos_lbl.setObjectName("status_pos")
        sbl.addWidget(self.pos_lbl)
        root.addWidget(sb)

        self.hint = self._lbl('help.text', obj_name='status_normal')
        self.hint.setContentsMargins(18, 3, 18, 8)
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

    def _settings_tab(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14); v.setSpacing(8)

        row = QtWidgets.QHBoxLayout()
        self._lbl('settings.mode_label', row)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([tr('settings.mode1'), tr('settings.mode2')])
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        row.addWidget(self.mode_combo, 1)
        v.addLayout(row)

        self.min_slider, self.min_lbl = self._slider_row(v, 'settings.min_delay', 0, 200,
                                                          self.bot.min_note_delay, self.min_delay_changed)
        self.max_slider, self.max_lbl = self._slider_row(v, 'settings.max_delay', 0, 500,
                                                          self.bot.max_note_delay, self.max_delay_changed)
        self.min_slider.setToolTip(tr('settings.mode2'))
        self.max_slider.setToolTip(tr('settings.mode2'))

        spd_row = QtWidgets.QHBoxLayout()
        self._lbl('settings.speed', spd_row, min_width=180)
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(int(self.bot.speed * 100))
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        spd_row.addWidget(self.speed_slider, 1)
        self.speed_lbl = QtWidgets.QLabel(f"{self.bot.speed:.2f}×")
        self.speed_lbl.setMinimumWidth(60)
        spd_row.addWidget(self.speed_lbl)
        v.addLayout(spd_row)

        row_tr = QtWidgets.QHBoxLayout()
        self._lbl('settings.transpose_initial', row_tr, min_width=180)
        self.transpose_spin = QtWidgets.QSpinBox()
        self.transpose_spin.setRange(-24, 24)
        self.transpose_spin.setValue(self.bot.initial_transpose)
        self.transpose_spin.setToolTip(tr('settings.transpose_hint'))
        self.transpose_spin.valueChanged.connect(self._on_initial_transpose_changed)
        row_tr.addWidget(self.transpose_spin, 1)
        auto_btn = HoverButton("🎯")
        auto_btn.setToolTip(tr('settings.auto_transpose_hint'))
        auto_btn.clicked.connect(self.auto_transpose)
        row_tr.addWidget(auto_btn)
        v.addLayout(row_tr)

        row_bpm = QtWidgets.QHBoxLayout()
        self._lbl('settings.bpm', row_bpm, min_width=180)
        self.bpm_spin = QtWidgets.QSpinBox()
        self.bpm_spin.setRange(0, 1000)
        self.bpm_spin.setValue(self.bot.bpm)
        self.bpm_spin.setToolTip(tr('settings.bpm_hint'))
        self.bpm_spin.valueChanged.connect(self._on_bpm_changed)
        row_bpm.addWidget(self.bpm_spin, 1)
        self.bpm_lbl = QtWidgets.QLabel(""); self.bpm_lbl.setMinimumWidth(120)
        row_bpm.addWidget(self.bpm_lbl)
        v.addLayout(row_bpm)
        self._refresh_bpm_label(self.bot.bpm)

        self.audio_enable_check = self._tr_chk('settings.speaker_enable', v)
        self.audio_enable_check.setChecked(self.bot.audio_enabled)
        self.audio_enable_check.toggled.connect(self._on_audio_toggle)

        auto_hold_row = QtWidgets.QHBoxLayout()
        self._lbl('audio.auto_hold', auto_hold_row)
        self.auto_hold_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.auto_hold_slider.setMinimum(20); self.auto_hold_slider.setMaximum(1000)
        self.auto_hold_slider.setValue(self.bot.auto_hold_ms)
        self.auto_hold_slider.valueChanged.connect(self._auto_hold_changed)
        auto_hold_row.addWidget(self.auto_hold_slider, 1)
        self.auto_hold_label = QtWidgets.QLabel(str(self.bot.auto_hold_ms))
        self.auto_hold_label.setMinimumWidth(40)
        auto_hold_row.addWidget(self.auto_hold_label)
        v.addLayout(auto_hold_row)

        self.auto_play_check = self._tr_chk('audio.auto_play', v)
        self.auto_play_check.setChecked(bool(self.bot.auto_play_no_pedal))
        self.auto_play_check.toggled.connect(self._on_auto_play_toggled)

        self.auto_update_check = self._tr_chk('settings.auto_update', v)
        self.auto_update_check.setChecked(self.bot.check_updates_on_start)
        self.auto_update_check.toggled.connect(self._on_auto_update_toggled)

        row2 = QtWidgets.QHBoxLayout()
        u = self._tr_btn('settings.update_btn', row2); u.clicked.connect(self.gui_update_client)
        p = self._tr_btn('settings.pedal_btn', row2); p.clicked.connect(self.open_pedal_settings)
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
        v.setContentsMargins(16, 14, 16, 14); v.setSpacing(10)
        self.midi_enable_check = self._tr_chk('midi.enable', v)
        self.midi_enable_check.setChecked(self.bot.midi_out_enabled)
        self.midi_enable_check.toggled.connect(self._on_midi_toggle)
        row = QtWidgets.QHBoxLayout()
        self._lbl('midi.port', row)
        self.midi_port_combo = QtWidgets.QComboBox()
        row.addWidget(self.midi_port_combo, 1)
        ref = self._icon_btn("⟳", 'midi.refresh_tooltip'); ref.clicked.connect(self._refresh_midi_ports)
        row.addWidget(ref)
        v.addLayout(row)
        test = self._tr_btn('midi.test', v); test.clicked.connect(self._midi_test)
        self.midi_status_label = QtWidgets.QLabel(tr('midi.no_ports'))
        self.midi_status_label.setObjectName("status_normal")
        v.addWidget(self.midi_status_label)
        hint = self._lbl('midi.hint', v, obj_name='status_normal'); hint.setWordWrap(True)
        v.addStretch()
        return w

    def _slider_row(self, parent, key, lo, hi, val, cb):
        row = QtWidgets.QHBoxLayout()
        self._lbl(key, row, min_width=180)
        s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s.setRange(lo, hi); s.setValue(val)
        s.valueChanged.connect(cb)
        row.addWidget(s, 1)
        vl = QtWidgets.QLabel(str(val)); vl.setMinimumWidth(40)
        vl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        row.addWidget(vl)
        parent.addLayout(row)
        return s, vl

    def _update_mode_ui(self):
        """Слайдеры min/max активны только в режиме «С задержками»."""
        is_delay_mode = (self.bot.mode == 2)
        for w in (self.min_slider, self.max_slider, self.min_lbl, self.max_lbl):
            w.setEnabled(is_delay_mode)

    def _retranslate_ui(self):
        for key, items in self._i18n_widgets.items():
            text = tr(key)
            for kind, widget in items:
                try:
                    if kind == 'text': widget.setText(text)
                    elif kind == 'tooltip': widget.setToolTip(text)
                    elif kind == 'placeholder': widget.setPlaceholderText(text)
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
        self._refresh_midi_ports()
        if hasattr(self, 'midi_status_label'):
            if self.bot.midi_out_enabled and self.bot.midi_port_name:
                self.midi_status_label.setText(tr('midi.connected', name=self.bot.midi_port_name))
            else:
                self.midi_status_label.setText(tr('midi.no_ports'))
        if hasattr(self, 'overlay_window') and self.overlay_window:
            self.overlay_window.refresh_tooltips()
        self.refresh()

    def _autosave_draft(self):
        try:
            txt = self.song_input.toPlainText()
            save_draft(txt)
        except Exception:
            pass

    def _restore_draft_if_any(self):
        draft = load_draft()
        if not draft.strip():
            return
        reply = QtWidgets.QMessageBox.question(
            self, tr('draft.title'), tr('draft.text'),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.song_input.setPlainText(draft)
        else:
            save_draft("")

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

    def _open_custom_theme(self):
        dlg = CustomThemeDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            accent, bg, text = dlg.get_colors()
            is_dark = QtGui.QColor(bg).lightness() < 128
            panel = QtGui.QColor(bg).lighter(115).name() if is_dark else QtGui.QColor(bg).darker(105).name()
            panel_alt = QtGui.QColor(bg).lighter(125).name() if is_dark else QtGui.QColor(bg).darker(110).name()
            inp = QtGui.QColor(bg).lighter(110).name() if is_dark else QtGui.QColor(bg).darker(103).name()
            border = QtGui.QColor(bg).lighter(150).name() if is_dark else QtGui.QColor(bg).darker(130).name()
            text_muted = QtGui.QColor(text).darker(140).name() if is_dark else QtGui.QColor(text).lighter(140).name()
            text_dim = QtGui.QColor(text).darker(180).name() if is_dark else QtGui.QColor(text).lighter(180).name()
            THEMES["custom"] = _mk_theme(
                "custom", "theme_custom.title", is_dark,
                bg, panel_alt, panel, panel_alt, inp, text, text_muted, text_dim,
                accent, accent, accent, text if is_dark else bg, border)
            self._animate_theme("custom", duration=200)

    def toggle_play(self):
        self.bot.toggle_play_smart()
        self.refresh()

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

    def open_history(self):
        PlayHistoryDialog(self.bot, self).exec()

    def open_hotkeys(self):
        HotkeySettingsDialog(self.bot, self).exec()

    def open_song_profile(self):
        idx = self.song_list.currentRow()
        if 0 <= idx < len(self.bot.playlist):
            name = self.bot.playlist[idx][0]
            SongProfileDialog(self.bot, name, self).exec()
            self._apply_profile_to_ui()

    def _apply_profile_to_ui(self):
        try:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(self.bot.mode - 1)
            self.mode_combo.blockSignals(False)
            self.bpm_spin.blockSignals(True)
            self.bpm_spin.setValue(self.bot.bpm)
            self.bpm_spin.blockSignals(False)
            self._refresh_bpm_label(self.bot.bpm)
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(int(self.bot.speed * 100))
            self.speed_slider.blockSignals(False)
            self.speed_lbl.setText(f"{self.bot.speed:.2f}×")
            self.transpose_spin.blockSignals(True)
            self.transpose_spin.setValue(self.bot.initial_transpose)
            self.transpose_spin.blockSignals(False)
            self._update_mode_ui()
        except Exception:
            pass

    def auto_transpose(self):
        if not self.bot.song:
            QtWidgets.QMessageBox.information(self, tr('autotranspose.title'), tr('autotranspose.none'))
            return
        if self.bot.song.startswith(TIMED_MARKER):
            QtWidgets.QMessageBox.information(self, tr('autotranspose.title'), tr('autotranspose.none'))
            return
        tr_val, rng = suggest_transpose(self.bot.song)
        if tr_val is None:
            QtWidgets.QMessageBox.information(self, tr('autotranspose.title'), tr('autotranspose.none'))
            return
        lo, hi = rng
        txt = tr('autotranspose.text', lo=lo, hi=hi, tr=tr_val)
        reply = QtWidgets.QMessageBox.question(
            self, tr('autotranspose.title'), txt,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.bot.initial_transpose = int(tr_val)
            self.bot.current_transpose = int(tr_val)
            self.transpose_spin.blockSignals(True)
            self.transpose_spin.setValue(int(tr_val))
            self.transpose_spin.blockSignals(False)
            self.bot.save_app_settings()

    def next_mode(self):
        self.bot.mode = 2 if self.bot.mode == 1 else 1
        self.mode_combo.setCurrentIndex(self.bot.mode - 1)
        self.bot.save_app_settings()
        self._update_mode_ui()
        self.refresh()

    def mode_changed(self, i):
        self.bot.mode = i + 1
        self.bot.save_app_settings()
        self._update_mode_ui()

    def min_delay_changed(self, v):
        self.bot.min_note_delay = v; self.min_lbl.setText(str(v))
        if v > self.bot.max_note_delay:
            self.bot.max_note_delay = v
            self.max_slider.setValue(v); self.max_lbl.setText(str(v))

    def max_delay_changed(self, v):
        self.bot.max_note_delay = v; self.max_lbl.setText(str(v))
        if v < self.bot.min_note_delay:
            self.bot.min_note_delay = v
            self.min_slider.setValue(v); self.min_lbl.setText(str(v))

    def _on_speed_changed(self, v):
        self.bot.speed = v / 100.0
        self.speed_lbl.setText(f"{self.bot.speed:.2f}×")
        self.bot.save_app_settings()

    def _on_initial_transpose_changed(self, v):
        self.bot.initial_transpose = int(v)
        self.bot.current_transpose = int(v)
        self.bot.save_app_settings()

    def _refresh_bpm_label(self, v):
        if v > 0:
            self.bpm_lbl.setText(f"≈ {60.0 / v:.3f}s / нота")
        else:
            self.bpm_lbl.setText("")

    def _on_bpm_changed(self, v):
        self.bot.bpm = int(v); self._refresh_bpm_label(int(v)); self.bot.save_app_settings()

    def _on_audio_toggle(self, checked):
        e = bool(checked)
        if e and (not HAS_AUDIO or not self.bot.audio_player):
            QtWidgets.QMessageBox.warning(self, tr('audio.warn_title'), tr('audio.warn_text'))
            self.audio_enable_check.setChecked(False)
            return
        self.bot.audio_enabled = e; self.bot.save_app_settings()

    def _on_auto_play_toggled(self, checked):
        """PyQt6: toggled(bool) — всегда честный bool, без enum-ловушек."""
        self.bot.auto_play_no_pedal = bool(checked)
        logger.info(f"auto_play_no_pedal set to {self.bot.auto_play_no_pedal}")
        self.bot.save_app_settings()
        self.refresh()

    def _auto_hold_changed(self, v):
        self.bot.auto_hold_ms = int(v); self.auto_hold_label.setText(str(v)); self.bot.save_app_settings()

    def _on_auto_update_toggled(self, checked):
        self.bot.check_updates_on_start = bool(checked); self.bot.save_app_settings()

    def _auto_check_updates_if_enabled(self):
        if self.bot.check_updates_on_start and not self.bot.playing and not self.bot.is_playback:
            self.gui_update_client()

    def open_recordings_manager(self):
        RecordingsManagerDialog(self.bot, self).exec()

    def open_pedal_settings(self):
        PedalSettingsDialog(self.bot, self).exec()

    # ─── Playlist ───
    def add_song(self):
        text = self.song_input.toPlainText().strip()
        if not text:
            return
        default = tr('songs.default_name', n=len(self.bot.playlist) + 1)
        name, ok = QtWidgets.QInputDialog.getText(self, tr('songs.name_title'), tr('songs.name_label'), text=default)
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
        save_draft("")

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
                    self.bot.song_name = ""; self.bot.song = ""
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
            new_name, ok = QtWidgets.QInputDialog.getText(self, tr('recordings.rename'), tr('songs.new_name'), text=name)
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
            backup_playlist()
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
                self.bot.playlist = [(d['name'], self.bot.sanitize_song(d['content'])) for d in data]
                self.bot.song_index = 0
                if self.bot.playlist:
                    self.bot.song_name, self.bot.song = self.bot.playlist[0]
                else:
                    self.bot.song_name = ""; self.bot.song = ""
                self.refresh_list()
        except Exception as e:
            logger.error(f"Load playlist error: {e}")

    def load_playlist_dialog(self):
        self.load_playlist(); self.refresh_list()

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

    def _on_song_selected(self, row):
        if row < 0 or row >= len(self.bot.playlist):
            return
        if row == self.bot.song_index:
            return
        if self.bot.is_playback:
            self.bot.stop_playback()
        self.bot.playing = False
        self.bot.song_index = row
        self.bot.song_name, self.bot.song = self.bot.playlist[row]
        self.bot.note_index = 0
        self.bot.frozen_note_index = 0
        self.bot.progress = 0
        self._apply_profile_to_ui()

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
            self.bot.song_name = ""; self.bot.song = ""
        self.song_list.setCurrentRow(self.bot.song_index)
        self.song_list.blockSignals(False)

    # ─── Refresh ───
    def refresh(self):
        song_is_timed = bool(self.bot.song) and self.bot.song.startswith(TIMED_MARKER)

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
        self.tr_lbl.setText(f"· tr {self.bot.current_transpose:+d}")
        self.spd_lbl.setText(f"· {self.bot.speed:.2f}×")
        self.auto_lbl.setText("· AUTO" if self.bot.auto_play_no_pedal else "· PEDAL")

        try:
            if song_is_timed:
                content = self.bot.song[len(TIMED_MARKER):]
                total = len(MIXED_TOKEN_RE.findall(content))
                self.pos_lbl.setText(f"timed · {total} ev")
            else:
                self.pos_lbl.setText(f"{self.bot.note_index}/{len(self.bot.song)}")
        except Exception:
            self.pos_lbl.setText("0/0")

        if song_is_timed:
            if self.bot.is_playback:
                self.play_btn.setText("⏸ " + tr('player.btn_pause'))
                self.play_btn.setToolTip(tr('player.pause_tooltip'))
            else:
                self.play_btn.setText("▶ " + tr('player.btn_play'))
                self.play_btn.setToolTip(tr('player.start_tooltip'))
        else:
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

        if self.bot.is_recording and not self._last_recording:
            self._start_record_pulse()
        elif not self.bot.is_recording and self._last_recording:
            self._stop_record_pulse()
        self._last_recording = self.bot.is_recording

        self._last_playback = self.bot.is_playback
        if self.bot.is_playback:
            self.playback_btn.hide(); self.stop_btn.show(); self.pause_btn.show()
        else:
            self.playback_btn.show(); self.stop_btn.hide(); self.pause_btn.hide()

        self._update_song_display()
        if self.overlay_window and self.overlay_window.isVisible():
            self.overlay_window.update_metadata(self.bot.song_name, self.bot.progress,
                                                 self.bot.playing, self.bot.is_playback)
        if self.song_list.currentRow() != self.bot.song_index:
            self.song_list.blockSignals(True)
            self.song_list.setCurrentRow(self.bot.song_index)
            self.song_list.blockSignals(False)

    def _flash_status(self):
        try:
            if self._status_flash_effect is not None:
                try:
                    self.status_label.setGraphicsEffect(None)
                except Exception:
                    pass
                self._status_flash_effect = None
            eff = QtWidgets.QGraphicsOpacityEffect(self.status_label)
            self._status_flash_effect = eff
            self.status_label.setGraphicsEffect(eff)
            anim = QtCore.QPropertyAnimation(eff, b"opacity")
            anim.setDuration(420)
            anim.setKeyValueAt(0.0, 0.35); anim.setKeyValueAt(1.0, 1.0)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            def _cleanup():
                try:
                    self.status_label.setGraphicsEffect(None)
                except Exception:
                    pass
                self._status_flash_effect = None
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
            anim.setKeyValueAt(0.0, 1.0); anim.setKeyValueAt(0.5, 0.4); anim.setKeyValueAt(1.0, 1.0)
            anim.setLoopCount(-1); anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
            self._rec_pulse_anim = anim
            anim.start()
        except Exception:
            pass

    def _stop_record_pulse(self):
        try:
            if self._rec_pulse_anim is not None:
                self._rec_pulse_anim.stop(); self._rec_pulse_anim = None
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

        if self.bot.song.startswith(TIMED_MARKER):
            content = self.bot.song[len(TIMED_MARKER):]
            total = len(MIXED_TOKEN_RE.findall(content))
            preview = content[:400]
            self.song_display.setPlainText(f"[Timed notes · {total} events]\n{preview}")
            return

        cpl, lines = 45, 3
        total = cpl * lines
        pos = self.bot.frozen_note_index if self.bot.freeze_note else self.bot.note_index
        t = get_theme()
        song = self.bot.song
        visible = []
        vis_to_orig = []
        i = 0
        while i < len(song):
            c = song[i]
            if c == TRANSPOSE_START:
                end = song.find(TRANSPOSE_END, i)
                if end != -1:
                    try:
                        val = int(song[i + 1:end])
                        marker_text = f'⟨{val:+d}⟩'
                    except Exception:
                        marker_text = '⟨?⟩'
                    for ch in marker_text:
                        visible.append(ch); vis_to_orig.append(i)
                    i = end + 1
                    continue
            visible.append(c); vis_to_orig.append(i); i += 1
        vis_str = ''.join(visible)
        vis_pos = len(visible)
        for vi, oi in enumerate(vis_to_orig):
            if oi >= pos:
                vis_pos = vi
                break
        start = max(0, vis_pos - total // 3)
        disp = vis_str[start:start + total]
        ci = vis_pos - start
        if 0 <= ci < len(disp):
            before = html.escape(disp[:ci]); cur = html.escape(disp[ci:ci+1]); after = html.escape(disp[ci+1:])
            self.song_display.setHtml(
                f'<span style="color:{t["text_muted"]};">{before}</span>'
                f'<span style="background-color:{t["selection"]}; color:{t["accent_press"]}; '
                f'font-weight:bold; padding:0 4px; border-radius:3px;">{cur}</span>'
                f'<span style="color:{t["text_muted"]};">{after}</span>')
        else:
            self.song_display.setPlainText(disp)

    def show_about(self):
        QtWidgets.QMessageBox.about(self, tr('app.about_title'),
                                     tr('app.about_text', version=CURRENT_VERSION))

    def _refresh_midi_ports(self):
        ports = self.bot.list_midi_ports()
        self.midi_port_combo.clear()
        if not ports:
            self.midi_port_combo.addItem(tr('midi.no_ports')); return
        for p in ports:
            self.midi_port_combo.addItem(p)
        saved = self.bot.midi_port_name
        if saved and saved in ports:
            self.midi_port_combo.setCurrentText(saved)

    def _on_midi_toggle(self, checked):
        enabled = bool(checked)
        if enabled:
            if not HAS_MIDI_OUT:
                QtWidgets.QMessageBox.warning(self, tr('midi.error'), tr('midi.no_lib'))
                self.midi_enable_check.setChecked(False); return
            port_name = self.midi_port_combo.currentText().strip()
            if not port_name or port_name.startswith("("):
                QtWidgets.QMessageBox.warning(self, tr('midi.error'), tr('midi.select_port'))
                self.midi_enable_check.setChecked(False); return
            ok, err = self.bot.open_midi_port(port_name)
            if not ok:
                QtWidgets.QMessageBox.critical(self, tr('midi.error'), str(err))
                self.midi_enable_check.setChecked(False); return
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

    def gui_update_client(self):
        self.update_progress.setVisible(True); self.update_progress.setValue(0)
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            info, err = fetch_latest_release_info()
            if err or not info:
                self.show_message_box(tr('update.error'), str(err)); return
            tag = (info.get("tag_name") or info.get("name") or "").strip()
            latest_version = tag.lstrip("v").strip()
            if not latest_version:
                m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", info.get("body", ""))
                if m:
                    latest_version = m.group(1)
            if not latest_version:
                self.show_message_box(tr('update.error'), tr('update.version_unknown')); return
            if version_tuple(latest_version) <= version_tuple(CURRENT_VERSION):
                self.show_message_box(tr('settings.update_btn'), tr('update.latest')); return
            asset_url = None
            for a in info.get("assets", []):
                if a.get("name") == ASSET_NAME:
                    asset_url = a.get("browser_download_url")
                    break
            if not asset_url:
                self.show_message_box(tr('update.error'), tr('update.asset_missing')); return
            tmp_name = "AstraKeys_update_tmp.exe"
            def prog_cb(pct):
                QtCore.QTimer.singleShot(0, lambda: self.update_progress.setValue(pct))
            ok, derr = download_asset_to_file(asset_url, tmp_name, progress_callback=prog_cb)
            if not ok:
                self.show_message_box(tr('update.error'), str(derr)); return
            is_frozen = getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe")
            perform_replacement_and_restart(tmp_name, ASSET_NAME, is_frozen)
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self.show_message_box(tr('update.error'), str(e))
        finally:
            QtCore.QTimer.singleShot(0, lambda: self.update_progress.setVisible(False))

    def show_message_box(self, title, text):
        QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.information(self, title, text))

    def save_window_state(self):
        try:
            state = {"geometry": {"x": self.x(), "y": self.y(),
                                   "width": self.width(), "height": self.height()},
                     "maximized": self.isMaximized()}
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
        self._autosave_draft()
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
