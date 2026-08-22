"""Точка входа для WSGI-хостинга (PythonAnywhere и аналогичные).

Локально этот файл не используется — для разработки по-прежнему запускайте
`python app.py`. Он нужен только серверу PythonAnywhere, который импортирует
из него переменную `application`, а не запускает `app.py` напрямую.

Как использовать на PythonAnywhere:
1. Откройте вкладку Web -> ваше приложение -> ссылку "WSGI configuration file"
   (обычно /var/www/<username>_pythonanywhere_com_wsgi.py).
2. Замените ВСЁ содержимое открывшегося файла на содержимое этого файла.
3. Замените PROJECT_PATH ниже на реальный путь к проекту на сервере,
   например: /home/ваш_логин/zap4asti-store
4. Сохраните и нажмите зелёную кнопку "Reload" на вкладке Web.
"""
import os
import sys

PROJECT_PATH = '/home/yourusername/zap4asti-store'

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

from app import create_app  # noqa: E402

application = create_app()
