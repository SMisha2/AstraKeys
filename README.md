AstraKeys 🎹
<div align="center"><img src="https://img.shields.io/badge/version-1.2.0-d4af37?style=for-the-badge&logo=starship&logoColor=white" alt="Version"> <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Platform"> <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/license-MIT-5cb85c?style=for-the-badge" alt="License"> <img src="https://img.shields.io/badge/PRs-welcome-d4af37?style=for-the-badge" alt="PRs Welcome">
✨ Автоматический пианист для Roblox, MIDI-секвенсор и студия записей
Играйте, записывайте, редактируйте и экспортируйте музыку — всё в одном приложении с золотым интерфейсом.

📥 Скачать · 📖 Документация · 🐛 Баги · 💡 Идеи

</div>
📸 Скриншоты
<div align="center">
Главное окно	Оверлей нот
https://docs/screenshot_main.png	https://docs/screenshot_overlay.png
Редактор записей	Менеджер записей
https://docs/screenshot_editor.png	https://docs/screenshot_recordings.png
</div>
🌟 Возможности
<table> <tr> <td width="50%" valign="top">
🎵 Воспроизведение
📜 Плейлисты с drag & drop

🎹 Аккорды и ноты в формате Roblox

⏱️ Точная эмуляция нажатий клавиш

🎯 Два режима: без задержек / с человеческими задержками

📝 Запись и редактор
🔴 Запись нажатий в реальном времени (F12)

✂️ Обрезка записей (trim)

🔗 Склейка двух записей с паузой

⭐ Избранное, поиск, сортировка

📦 Импорт / экспорт ZIP-архивов

</td> <td width="50%" valign="top">
🎼 MIDI & Audio
🎹 MIDI-выход для FreePiano / loopMIDI

💾 Экспорт в .mid файлы

🔊 Локальный звук через динамики (ADSR-синтез)

🎚️ Регулировка громкости и авто-удержания

🎨 Интерфейс
🌗 Две темы: Золото и Песок

✨ Плавные анимации перехода темы

🌍 Полная локализация: RU / EN / UK

🪟 Оверлей нот поверх Roblox

🔄 Авто-обновления с GitHub

</td> </tr> </table>
🚀 Установка
Вариант 1: Готовый .exe (рекомендуется)
Перейдите в раздел Releases

Скачайте последний AstraKeys.exe

Запустите от имени администратора (нужно для эмуляции клавиатуры)

⚠️ Антивирус может ругаться — это ложное срабатывание PyInstaller. Добавьте файл в исключения.

Вариант 2: Из исходников
bash
# 1. Клонируйте репозиторий
git clone https://github.com/SMisha2/AstraKeys.git
cd AstraKeys

# 2. Установите зависимости
pip install PyQt6 requests
pip install mido python-rtmidi midiutil pynput
pip install sounddevice numpy pywin32

# 3. Запустите
python main.py
<details> <summary>🛠️ Сборка .exe через PyInstaller</summary>
bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed \
    --name "AstraKeys" \
    --icon "icon.ico" \
    main.py
</details>
🎮 Горячие клавиши
Клавиша	Действие
<kbd>F1</kbd>	▶️ Пуск / Пауза
<kbd>F2</kbd>	🔄 Рестарт песни
<kbd>F3</kbd> / <kbd>F4</kbd>	⏩ / ⏪ ±25 нот
<kbd>F5</kbd>	⏸️ Пауза воспроизведения записи
<kbd>F6</kbd>	❄️ Заморозка позиции
<kbd>F7</kbd>	🔀 Сменить режим (задержки)
<kbd>F8</kbd>	⏭️ Следующая песня
<kbd>F9</kbd>	⏹️ Стоп воспроизведения
<kbd>F10</kbd>	🎵 Последняя запись
<kbd>F12</kbd>	🔴 Начать / остановить запись
Символы педалей: - = [ ] (удерживают ноту пока зажаты)

🎼 Формат песен
AstraKeys использует нотную запись Roblox. Просто вставьте текст в поле ввода:

text
[eT] [eT] [6eT] [ey] [6eT] [4qe] [qe] [6qe] [qE] 4 [6qe] 6 [QPS]
Правила синтаксиса
Синтаксис	Значение
q	Одиночная нота (строчная = белая клавиша)
Q	Одиночная нота (заглавная = чёрная клавиша)
[qwe]	Аккорд (ноты играются одновременно)
- / = / [ / ]	Педаль (удержание)
 (пробел)	Игнорируется
Клавиши-ноты
text
1 2 3 4 5 6 7 8 9 0   →   C D E F G A B C D E
q w e r t y u i o p   →   F G A B C D E F G A
a s d f g h j k l     →   B C D E F G A B C
z x c v b n m         →   D E F G A B C
Заглавные буквы и символы (!@#$%^&*()) — диезы (чёрные клавиши).

🎹 Настройка MIDI (FreePiano)
Установите loopMIDI

Создайте виртуальный порт (например, AstraKeys)

В AstraKeys откройте вкладку MIDI → включите «Отправлять ноты через MIDI»

Выберите созданный порт → Тест (C-мажор)

В FreePiano выберите этот же порт как вход

Готово! Теперь ноты уходят в FreePiano параллельно с эмуляцией клавиатуры.

📁 Файлы настроек
Все настройки хранятся рядом с приложением в JSON:

Файл	Что хранит
app_settings.json	Язык, тема, MIDI, задержки
playlist.json	Сохранённый плейлист
pedal_settings.json	Символы педалей
recordings_index.json	Индекс всех записей
overlay_settings.json	Настройки оверлея
window_state.json	Позиция и размер окна
recordings/	Сами записи (.json + .mid)
❓ FAQ
<details> <summary><b>Антивирус удаляет AstraKeys.exe</b></summary>
Ложное срабатывание PyInstaller. Добавьте в исключения Windows Defender → «Защита от вирусов» → «Исключения».

</details><details> <summary><b>Клавиши не нажимаются в Roblox</b></summary>
Запустите AstraKeys от имени администратора. Roblox и автокликер должны иметь одинаковые права.

</details><details> <summary><b>MIDI-порт не появляется</b></summary>
Установите loopMIDI и создайте порт до запуска AstraKeys. Если не помогло — нажмите ⟳ в MIDI-вкладке.

</details><details> <summary><b>Нет звука в динамиках</b></summary>
bash
pip install sounddevice numpy
Затем включите галочку «Звук нот в динамиках» во вкладке «Параметры».

</details><details> <summary><b>Запись получилась кривой по таймингам</b></summary>
В менеджере записей откройте Редактор → Обрезка. Точность воспроизведения также зависит от режима: «Без задержек» — детерминированный, «С задержками» — рандомизированный.

</details><details> <summary><b>Можно ли использовать с другими играми?</b></summary>
Да, любая игра, где ноты играются клавишами 1234567890 qwerty.... Просто убедитесь, что окно игры в фокусе.

</details>
⚠️ Дисклеймер
AstraKeys — это инструмент для обучения и развлечения.
Автоматизация может нарушать правила использования Roblox и других игр.
Автор не несёт ответственности за блокировку аккаунтов или другие последствия.
Используйте на свой страх и риск — предпочтительно в одиночных режимах и личных проектах.

🛠️ Технологии
<div align="center">
https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white	https://img.shields.io/badge/PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white	https://img.shields.io/badge/MIDI-d4af37?style=flat-square
https://img.shields.io/badge/pynput-e05a4d?style=flat-square	https://img.shields.io/badge/sounddevice-5cb85c?style=flat-square	https://img.shields.io/badge/numpy-013243?style=flat-square&logo=numpy
</div>
🤝 Вклад
Pull requests приветствуются! По крупным изменениям сначала откройте issue для обсуждения.

bash
# Форк → ветка → PR
git checkout -b feature/amazing-feature
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
📜 Лицензия
Проект распространяется под лицензией MIT — используйте, форкайте, модифицируйте свободно.

<div align="center">
💛 Сделано с любовью к музыке
Автор: SMisha2
Версия: 1.2.0 · Обновлено: 2025

⭐ Если AstraKeys вам помог — поставьте звезду репозиторию! ⭐

⬆️ Наверх

</div>
