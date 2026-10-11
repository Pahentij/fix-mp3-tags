Установка зависимостей после клонирования репозитория:
python3 -m pip install -r requirements.txt

Проверка:
python3 /path/to/fix_mp3_tags.py "/path/to/audiobooks" --dry-run

Запуск для внесения изменений в теги:
python3 /path/to/fix_mp3_tags.py "/path/to/audiobooks" --apply