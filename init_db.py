"""Инициализация БД: создание таблиц, демо-товары, первый администратор.

Запускается автоматически при старте app.py, либо вручную:
    python init_db.py
"""
import os

from dotenv import load_dotenv

import models

load_dotenv()

DEMO_PRODUCTS = [
    # Процессоры
    {'name': 'Intel Core i5-13600K', 'category': 'cpu', 'price': 28990,
     'description': '14 ядер (6P+8E), до 5.1 ГГц, разблокированный множитель, сокет LGA1700. '
                     'Отличный выбор для игр и многозадачности.',
     'image': 'https://picsum.photos/400/400?random=1'},
    {'name': 'Intel Core i9-14900K', 'category': 'cpu', 'price': 54990,
     'description': '24 ядра (8P+16E), до 6.0 ГГц, топовый флагман для энтузиастов и стриминга.',
     'image': 'https://picsum.photos/400/400?random=2'},
    {'name': 'AMD Ryzen 5 7600X', 'category': 'cpu', 'price': 22990,
     'description': '6 ядер/12 потоков, до 5.3 ГГц, сокет AM5, встроенная графика Radeon.',
     'image': 'https://picsum.photos/400/400?random=3'},
    {'name': 'AMD Ryzen 7 7800X3D', 'category': 'cpu', 'price': 39990,
     'description': '8 ядер/16 потоков с 3D V-Cache, лучший игровой процессор в линейке Ryzen 7000.',
     'image': 'https://picsum.photos/400/400?random=4'},
    # Видеокарты
    {'name': 'NVIDIA GeForce RTX 4070', 'category': 'gpu', 'price': 62990,
     'description': '12 ГБ GDDR6X, трассировка лучей, DLSS 3. Уверенный 1440p в современных играх.',
     'image': 'https://picsum.photos/400/400?random=5'},
    {'name': 'NVIDIA GeForce RTX 4080 SUPER', 'category': 'gpu', 'price': 109990,
     'description': '16 ГБ GDDR6X, флагманская производительность для 4K-гейминга.',
     'image': 'https://picsum.photos/400/400?random=6'},
    {'name': 'AMD Radeon RX 7800 XT', 'category': 'gpu', 'price': 54990,
     'description': '16 ГБ GDDR6, отличное соотношение цены и производительности в 1440p.',
     'image': 'https://picsum.photos/400/400?random=7'},
    {'name': 'NVIDIA GeForce RTX 4060 Ti', 'category': 'gpu', 'price': 44990,
     'description': '8 ГБ GDDR6X, компактное решение для 1080p/1440p с низким энергопотреблением.',
     'image': 'https://picsum.photos/400/400?random=8'},
    # Оперативная память
    {'name': 'Kingston FURY Beast 16GB DDR5-5600', 'category': 'ram', 'price': 6490,
     'description': 'Комплект 2x8 ГБ, DDR5-5600, невысокие тайминги, алюминиевый радиатор.',
     'image': 'https://picsum.photos/400/400?random=9'},
    {'name': 'Corsair Vengeance 32GB DDR5-6000', 'category': 'ram', 'price': 12990,
     'description': 'Комплект 2x16 ГБ, DDR5-6000 CL36, поддержка Intel XMP 3.0.',
     'image': 'https://picsum.photos/400/400?random=10'},
    {'name': 'G.Skill Trident Z5 32GB DDR5-6400', 'category': 'ram', 'price': 15990,
     'description': 'Комплект 2x16 ГБ, DDR5-6400 CL32, RGB-подсветка, для энтузиастов.',
     'image': 'https://picsum.photos/400/400?random=11'},
    # Накопители
    {'name': 'Samsung 980 PRO 1TB NVMe SSD', 'category': 'storage', 'price': 8990,
     'description': 'PCIe 4.0, скорость чтения до 7000 МБ/с, контроллер Samsung Elpis.',
     'image': 'https://picsum.photos/400/400?random=12'},
    {'name': 'WD Black SN850X 2TB NVMe SSD', 'category': 'storage', 'price': 15990,
     'description': 'PCIe 4.0, оптимизирован для игр, скорость чтения до 7300 МБ/с.',
     'image': 'https://picsum.photos/400/400?random=13'},
    {'name': 'Seagate Barracuda 2TB HDD', 'category': 'storage', 'price': 5490,
     'description': '3.5", 7200 об/мин, 256 МБ кэша — надёжное хранилище большого объёма.',
     'image': 'https://picsum.photos/400/400?random=14'},
    {'name': 'Kingston NV2 1TB NVMe SSD', 'category': 'storage', 'price': 5990,
     'description': 'PCIe 4.0, компактный и доступный накопитель для системного диска.',
     'image': 'https://picsum.photos/400/400?random=15'},
    # Блоки питания
    {'name': 'Corsair RM750x 750W 80+ Gold', 'category': 'psu', 'price': 11990,
     'description': 'Полностью модульный, сертификат 80+ Gold, тихий вентилятор 135 мм.',
     'image': 'https://picsum.photos/400/400?random=16'},
    {'name': 'be quiet! Straight Power 11 850W', 'category': 'psu', 'price': 14990,
     'description': '80+ Gold, японские конденсаторы, гарантия 5 лет.',
     'image': 'https://picsum.photos/400/400?random=17'},
    {'name': 'DeepCool PF600 600W', 'category': 'psu', 'price': 4490,
     'description': 'Немодульный, сертификат 80+ Bronze, бюджетное решение для домашнего ПК.',
     'image': 'https://picsum.photos/400/400?random=18'},
    # Корпуса
    {'name': 'NZXT H510 Flow', 'category': 'case', 'price': 7990,
     'description': 'Улучшенная вентиляция, продуманный кабель-менеджмент, закалённое стекло.',
     'image': 'https://picsum.photos/400/400?random=19'},
    {'name': 'Lian Li Lancool 215', 'category': 'case', 'price': 8490,
     'description': 'Сетчатая передняя панель, 2 вентилятора 160 мм в комплекте, отличный airflow.',
     'image': 'https://picsum.photos/400/400?random=20'},
]


def seed_demo_data():
    """Заполняет каталог демо-товарами, только если таблица products пуста."""
    db = models.get_db()
    count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    if count > 0:
        return
    for item in DEMO_PRODUCTS:
        models.create_product(
            item['name'], item['category'], item['price'], item['description'], item['image']
        )


def ensure_admin():
    """Создаёт администратора из ADMIN_EMAIL/ADMIN_PASSWORD (.env), если такого
    пользователя ещё нет. Ничего не делает, если переменные не заданы."""
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    if not email or not password:
        return
    if models.get_user_by_email(email):
        return
    models.create_user('Администратор', email, password, role='admin')


if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        pass  # create_app() уже вызвал init_db, seed_demo_data и ensure_admin
    print(f'База данных готова: {app.config["DATABASE"]}')
    print('Демо-товары и администратор (если заданы ADMIN_EMAIL/ADMIN_PASSWORD) созданы.')
