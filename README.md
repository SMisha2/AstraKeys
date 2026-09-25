<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0a,40:1a1a1a,70:2b2418,100:d4af37&height=220&section=header&text=AstraKeys&fontSize=96&fontColor=d4af37&fontAlignY=38&fontFamily=Georgia&desc=Автоматический%20пианист%20для%20Roblox&descAlignY=62&descSize=17&descColor=a8a8a8&animation=fadeIn" width="100%"/>

<br>

### ✨ Играйте · Записывайте · Редактируйте · Экспортируйте ✨

<br>

<a href="https://github.com/SMisha2/AstraKeys/releases/latest">
  <img src="https://img.shields.io/badge/⬇_Скачать_AstraKeys.exe-d4af37?style=for-the-badge&labelColor=0a0a0a&logo=windows&logoColor=d4af37" alt="Download">
</a>
<a href="#-документация">
  <img src="https://img.shields.io/badge/📖_Документация-8a8a8a?style=for-the-badge&labelColor=0a0a0a" alt="Docs">
</a>
<a href="https://github.com/SMisha2/AstraKeys/issues">
  <img src="https://img.shields.io/badge/🐛_Report_Bug-e05a4d?style=for-the-badge&labelColor=0a0a0a" alt="Issues">
</a>
<a href="https://github.com/SMisha2/AstraKeys/stargazers">
  <img src="https://img.shields.io/badge/⭐_Star-d4af37?style=for-the-badge&labelColor=0a0a0a" alt="Star">
</a>

<br><br>

<sub>
<img src="https://img.shields.io/badge/v1.3.0-d4af37?style=flat-square&label=version&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/Windows_10/11-0078D6?style=flat-square&logo=windows11&logoColor=white&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/Python_3.10+-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/MIT-5cb85c?style=flat-square&label=license&labelColor=0a0a0a">
<img src="https://img.shields.io/github/downloads/SMisha2/AstraKeys/total-d4af37?style=flat-square&label=downloads&labelColor=0a0a0a">
<img src="https://img.shields.io/github/stars/SMisha2/AstraKeys?style=flat-square&label=stars&color=d4af37&labelColor=0a0a0a">
</sub>

</div>

<br>

---

<br>

<div align="center">

## 📸 Скриншоты

</div>

<div align="center">

<table>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot_main.png" alt="Главное окно" width="100%"/>
<br><br>
<b>🎹 Главное окно</b>
<br>
<sub>Плейлист, плеер и настройки</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot_overlay.png" alt="Оверлей нот" width="100%"/>
<br><br>
<b>🎼 Оверлей нот</b>
<br>
<sub>Ноты поверх игры в реальном времени</sub>
</td>
</tr>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot_editor.png" alt="Редактор записей" width="100%"/>
<br><br>
<b>✂️ Редактор записей</b>
<br>
<sub>Обрезка, склейка, квантизация</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot_recordings.png" alt="Менеджер записей" width="100%"/>
<br><br>
<b>📚 Менеджер записей</b>
<br>
<sub>Поиск, избранное, экспорт</sub>
</td>
</tr>
</table>

<sub><i>Скриншоты можно найти в папке <code>docs/</code></i></sub>

</div>

<br>

---

<br>

<div align="center">

## 🎯 Что это

</div>

**AstraKeys** — приложение для Windows, которое играет музыку в Roblox за вас. Вставляете текст песни в формате Roblox-пианино — программа эмулирует нажатия клавиш с точными таймингами.

Помимо воспроизведения — **полноценная студия**: записывает вашу игру, редактирует записи, экспортирует в MIDI и умеет отправлять ноты на внешние синтезаторы через loopMIDI.

<br>

<details>
<summary><b>📑 Содержание</b> <i>(нажмите, чтобы развернуть)</i></summary>

<br>

- [Возможности](#-возможности)
- [Установка](#-установка)
- [Горячие клавиши](#-горячие-клавиши)
- [Формат песен](#-формат-песен)
- [MIDI (FreePiano)](#-midi-freepiano)
- [Файлы настроек](#-файлы-настроек)
- [FAQ](#-faq)
- [Стек](#-стек)
- [Вклад](#-вклад)
- [Лицензия](#-лицензия)

</details>

<br>

---

<br>

<div align="center">

## 🌟 Возможности

</div>

<table>
<tr>
<td width="50%" valign="top">

### 🎵 Воспроизведение

- 📜 Плейлист с drag & drop
- 🎹 Аккорды в формате Roblox
- ⏱️ Точная эмуляция нажатий
- 🎯 Два режима: **без задержек** / **с человеческими задержками**
- 🎚️ Скорость **0.5× – 2.0×**
- 🎼 Поддержка **BPM** для авто-удержания

### 📝 Запись и редактор

- 🔴 Запись в реальном времени `F12`
- ✂️ Обрезка записей
- 🔗 Склейка двух записей
- ↩️ Undo / Redo
- 🎯 Квантизация `1/4` `1/8` `1/16` `1/32`
- ⭐ Избранное, поиск, сортировка
- 📦 Импорт / экспорт ZIP

</td>
<td width="50%" valign="top">

### 🎼 MIDI & Audio

- 🎹 MIDI-выход для FreePiano / loopMIDI
- 💾 Экспорт в `.mid`
- 🔊 Локальный звук через динамики *(ADSR-синтез)*
- 🎚️ Регулировка громкости
- 🎹 Воспроизведение **без педали** *(auto-hold)*

### 🎨 Интерфейс

- 🌗 **10 тем** + кастомная
- ✨ Плавные анимации
- 🌍 Локализация **RU / EN / UK**
- 🪟 Оверлей поверх игры
- 📊 История воспроизведений
- 🔄 Авто-обновления с GitHub

</td>
</tr>
</table>

<br>

---

<br>

<div align="center">

## 🚀 Установка

</div>

### ⚡ Готовый `.exe` *(рекомендуется)*

```mermaid
graph LR
    A[📥 Releases]:::step --> B[⬇ Скачать .exe]:::step
    B --> C[▶ Запуск от админа]:::step
    C --> D[🎹 Играть]:::final

    classDef step fill:#1a1a1a,stroke:#d4af37,color:#d4af37,stroke-width:2px
    classDef final fill:#1a1a1a,stroke:#5cb85c,color:#5cb85c,stroke-width:2px
```

1. Откройте [**Releases**](https://github.com/SMisha2/AstraKeys/releases/latest)
2. Скачайте `AstraKeys.exe`
3. Запустите **от имени администратора**

<br>

> [!WARNING]
> **Антивирус может ругаться** — это ложное срабатывание PyInstaller.
> Добавьте файл в исключения: *Windows Defender → Защита от вирусов → Исключения*.

<br>

### 🐍 Из исходников

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/SMisha2/AstraKeys.git
cd AstraKeys

# 2. Установите зависимости
pip install PyQt6 requests
pip install mido python-rtmidi midiutil pynput
pip install sounddevice numpy pywin32

# 3. Запустите
python AstraKeys.py
```

<br>

<details>
<summary><b>🛠️ Сборка .exe через PyInstaller</b></summary>

<br>

```bash
pip install pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed ^
    --name "AstraKeys" ^
    --icon "assets/icon.ico" ^
    --hidden-import pynput.keyboard._win32 ^
    --hidden-import pynput.mouse._win32 ^
    --hidden-import sounddevice ^
    --hidden-import mido.backends.rtmidi ^
    --hidden-import win32gui ^
    --hidden-import win32con ^
    --collect-binaries sounddevice ^
    --collect-binaries rtmidi ^
    --collect-submodules pynput ^
    --collect-data midiutil ^
    AstraKeys.py
```

Готовый файл появится в `dist/AstraKeys.exe`.

</details>

<br>

---

<br>

<div align="center">

## 🎮 Горячие клавиши

</div>

<div align="center">

| | | | |
|:---:|:---|:---:|:---|
| <kbd>F1</kbd> | ▶ Пуск / Пауза | <kbd>F7</kbd> | 🔀 Сменить режим |
| <kbd>F2</kbd> | 🔄 Рестарт песни | <kbd>F8</kbd> | ⏭ Следующая песня |
| <kbd>F3</kbd> | ⏩ +25 нот | <kbd>F9</kbd> | ⏹ Стоп воспроизведения |
| <kbd>F4</kbd> | ⏪ −25 нот | <kbd>F10</kbd> | 🎵 Последняя запись |
| <kbd>F5</kbd> | ⏸ Пауза записи | <kbd>F12</kbd> | 🔴 Начать / стоп запись |
| <kbd>F6</kbd> | ❄ Заморозка позиции | <kbd>Ctrl</kbd>+<kbd>↑↓</kbd> | ⚡ Скорость ± |

</div>

> 💡 **Символы педалей:** `-` `=` `[` `]` — удерживают ноту, пока зажаты

<br>

---

<br>

<div align="center">

## 🎼 Формат песен

</div>

Стандартная нотная запись Roblox:

```text
[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe] 6 [QPS] C [Sc]
```

### 📖 Синтаксис

| Символ | Значение |
|:---:|:---|
| `q` | Нота — строчная (белая клавиша) |
| `Q` | Нота — заглавная (чёрная клавиша) |
| `[qwe]` | Аккорд — ноты играются одновременно |
| `-` `=` `[` `]` | Педаль — удержание ноты |
| _пробел_ | Игнорируется |

### 🎹 Карта клавиш

```text
1 2 3 4 5 6 7 8 9 0   →   C D E F G A B C D E
q w e r t y u i o p   →   F G A B C D E F G A
a s d f g h j k l     →   B C D E F G A B C
z x c v b n m         →   D E F G A B C
```

> 🔥 Заглавные буквы и символы `!@#$%^&*()` — **диезы** (чёрные клавиши)

<br>

### ⏱ Timed-формат *(с версии 1.3.0)*

Формат с абсолютными таймингами для точного воспроизведения:

```text
C {1441ms release}   I   [Q I] {214842ms press}
```

| Часть | Значение |
|:---|:---|
| `{NNNms press}` | Нота **нажимается** через N мс от начала |
| `{NNNms release}` | Нота **отпускается** через N мс от начала |
| _без `{}`_ | Интерполируется между ближайшими якорями |

<br>

---

<br>

<div align="center">

## 🎹 MIDI (FreePiano)

</div>

```mermaid
graph LR
    A[AstraKeys] -->|MIDI OUT| B[loopMIDI]
    B -->|Virtual Port| C[FreePiano]
    C --> D[🔊 Звук]

    classDef app fill:#1a1a1a,stroke:#d4af37,color:#d4af37,stroke-width:2px
    classDef mid fill:#1a1a1a,stroke:#d4af37,color:#d4af37,stroke-width:1.5px
    classDef out fill:#1a1a1a,stroke:#5cb85c,color:#5cb85c,stroke-width:2px

    class A app
    class B,C mid
    class D out
```

<br>

1. Установите [**loopMIDI**](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Создайте виртуальный порт *(например, `AstraKeys`)*
3. В AstraKeys откройте вкладку **MIDI** → включите **MIDI-выход** → выберите порт → нажмите **Тест**
4. В FreePiano выберите этот же порт как вход

<br>

---

<br>

<div align="center">

## 📁 Файлы настроек

</div>

Всё хранится рядом с приложением в JSON-формате:

| 📄 Файл | 🗂 Содержимое |
|:---|:---|
| `app_settings.json` | Язык, тема, MIDI, задержки, скорость, BPM |
| `playlist.json` | Сохранённый плейлист |
| `pedal_settings.json` | Символы педалей |
| `recordings_index.json` | Индекс всех записей |
| `overlay_settings.json` | Настройки оверлея |
| `window_state.json` | Позиция и размер окна |
| `hotkeys.json` | Кастомные горячие клавиши |
| `play_history.json` | История воспроизведений |
| `song_profiles.json` | Профили песен |
| `draft.txt` | Автосохранение ввода |
| `recordings/` | Записи `.json` + `.mid` |
| `backups/` | Автобэкапы плейлиста |

<br>

---

<br>

<div align="center">

## ❓ FAQ

</div>

<details>
<summary><b>🛡 Антивирус удаляет AstraKeys.exe</b></summary>
<br>

Ложное срабатывание PyInstaller. Добавьте файл в исключения:

**Windows Defender → Защита от вирусов → Исключения → Добавить файл.**

</details>

<details>
<summary><b>⌨ Клавиши не нажимаются в Roblox</b></summary>
<br>

Запустите AstraKeys **от имени администратора**. Roblox и автокликер должны иметь одинаковые права доступа.

</details>

<details>
<summary><b>🎹 MIDI-порт не появляется</b></summary>
<br>

Установите loopMIDI и создайте порт **до запуска** AstraKeys. Затем нажмите **⟳** во вкладке MIDI для обновления списка.

</details>

<details>
<summary><b>🔊 Нет звука в динамиках</b></summary>
<br>

```bash
pip install sounddevice numpy
```

Затем включите галочку **«Звук в динамиках»** во вкладке «Параметры».

</details>

<details>
<summary><b>⏱ Запись получилась кривой по таймингам</b></summary>
<br>

Откройте **Редактор → Обрезка** в менеджере записей. Точность также зависит от режима:

- 🎯 **«Без задержек»** — детерминированный
- 🎲 **«С задержками»** — рандомизированный

</details>

<details>
<summary><b>🎮 Можно ли использовать с другими играми?</b></summary>
<br>

Да — любая игра, где ноты играются клавишами `1234567890 qwerty...`. Убедитесь, что окно игры в фокусе.

</details>

<br>

---

<br>

<div align="center">

## 🛠 Стек

<br>

<p>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/pynput-e05a4d?style=for-the-badge&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/sounddevice-5cb85c?style=for-the-badge&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/mido-d4af37?style=for-the-badge&labelColor=0a0a0a">
<img src="https://img.shields.io/badge/PyInstaller-FFD43B?style=for-the-badge&logo=python&logoColor=0a0a0a&labelColor=0a0a0a">
</p>

</div>

<br>

---

<br>

<div align="center">

## 📊 Статистика

<br>

<img src="https://img.shields.io/github/v/release/SMisha2/AstraKeys?style=for-the-badge&color=d4af37&labelColor=0a0a0a&label=Release" alt="Release">
<img src="https://img.shields.io/github/release-date/SMisha2/AstraKeys?style=for-the-badge&color=d4af37&labelColor=0a0a0a&label=Updated" alt="Updated">
<img src="https://img.shields.io/github/commit-activity/m/SMisha2/AstraKeys?style=for-the-badge&color=d4af37&labelColor=0a0a0a&label=Commits" alt="Commits">
<img src="https://img.shields.io/github/issues/SMisha2/AstraKeys?style=for-the-badge&color=e05a4d&labelColor=0a0a0a&label=Issues" alt="Issues">

<br><br>

<a href="https://star-history.com/#SMisha2/AstraKeys&Date">
  <img src="https://api.star-history.com/svg?repos=SMisha2/AstraKeys&type=Date&theme=dark" alt="Star History" width="600">
</a>

</div>

<br>

---

<br>

<div align="center">

## 🤝 Вклад

</div>

**Pull requests приветствуются!** 🎉
По крупным изменениям сначала откройте [issue](https://github.com/SMisha2/AstraKeys/issues) для обсуждения.

```bash
# Fork → Branch → PR
git checkout -b feature/amazing-feature
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

<br>

<div align="center">

| 🐛 [Report Bug](https://github.com/SMisha2/AstraKeys/issues/new) · 💡 [Request Feature](https://github.com/SMisha2/AstraKeys/issues/new) · ⭐ [Star](https://github.com/SMisha2/AstraKeys/stargazers) |
|:---:|

</div>

<br>

---

<br>

<div align="center">

## ⚠️ Дисклеймер

</div>

> AstraKeys — инструмент для обучения и развлечения.
> Автоматизация может нарушать правила использования Roblox и других игр.
> Автор **не несёт ответственности** за блокировку аккаунтов или другие последствия.
> Используйте на свой страх и риск — предпочтительно в одиночных режимах и личных проектах.

<br>

---

<br>

<div align="center">

## 📜 Лицензия

Проект распространяется под лицензией **MIT** — используйте, форкайте, модифицируйте свободно.

<img src="https://img.shields.io/badge/License-MIT-5cb85c?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0a0a0a" alt="MIT">

</div>

<br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:d4af37,50:2b2418,100:0a0a0a&height=140&section=footer&text=Сделано%20с%20любовью%20к%20музыке&fontSize=20&fontColor=d4af37&fontAlignY=70&animation=twinkling" width="100%"/>

<div align="center">

<br>

<sub>
<b>Автор:</b> <a href="https://github.com/SMisha2">SMisha2</a>
&nbsp;·&nbsp;
<b>Версия:</b> <code>1.3.0</code>
&nbsp;·&nbsp;
<b>Обновлено:</b> 2026
</sub>

<br><br>

<a href="https://github.com/SMisha2/AstraKeys/stargazers">
  <img src="https://img.shields.io/badge/⭐_Поставьте_звезду_репозиторию-d4af37?style=for-the-badge&labelColor=0a0a0a" alt="Star">
</a>

<br><br>

<sub>⬆ <a href="#top">Наверх</a></sub>

</div>
