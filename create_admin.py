"""Ручное создание администратора.

Запуск: python create_admin.py
Если в .env заданы ADMIN_EMAIL и ADMIN_PASSWORD — использует их без вопросов
(и в этом случае администратор, скорее всего, уже создан автоматически при
старте приложения — скрипт просто сообщит об этом).
Иначе запрашивает имя, email и пароль интерактивно.
"""
import getpass
import os
import sys

from dotenv import load_dotenv

import models
from app import create_app

load_dotenv()


def main():
    app = create_app()
    with app.app_context():
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        name = 'Администратор'

        if email and password:
            print(f'Использую ADMIN_EMAIL/ADMIN_PASSWORD из .env: {email}')
        else:
            name = input('Имя администратора: ').strip() or 'Администратор'
            email = input('Email администратора: ').strip()
            password = getpass.getpass('Пароль администратора: ')

        if not email or not password:
            print('Email и пароль обязательны. Отмена.')
            sys.exit(1)

        existing = models.get_user_by_email(email)
        if existing:
            if existing.is_admin:
                print(f'Пользователь {email} уже является администратором.')
            else:
                print(f'Пользователь {email} уже существует, но не администратор. '
                      'Смените ему роль напрямую в БД либо используйте другой email.')
            sys.exit(0)

        models.create_user(name, email, password, role='admin')
        print(f'Администратор {email} успешно создан.')


if __name__ == '__main__':
    main()
