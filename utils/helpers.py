import os
import uuid
from functools import wraps

from flask import abort, current_app, session, url_for
from flask_login import current_user, login_required
from PIL import Image, ImageOps

import models

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def admin_required(f):
    """Разрешает доступ только пользователям с ролью admin. Неавторизованных
    сначала отправляет на логин (через login_required), авторизованных без
    роли admin — обрывает 403."""

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file_storage):
    """Сохраняет загруженное фото товара в UPLOAD_FOLDER с ресайзом до 400x400
    (cover-crop) и возвращает сгенерированное имя файла."""
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    image = Image.open(file_storage.stream)
    if ext in ('jpg', 'jpeg') and image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    fitted = ImageOps.fit(image, (400, 400), Image.LANCZOS)
    fitted.save(path)
    return filename


def delete_product_image(filename):
    """Удаляет локальный файл фото товара, если он есть. Внешние URL
    (демо-товары с picsum.photos) не трогает."""
    if not filename or filename.startswith('http'):
        return
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        os.remove(path)


def merge_session_cart(user_id):
    """Переносит гостевую корзину из сессии в корзину пользователя в БД
    после входа/регистрации и очищает сессионную корзину."""
    cart = session.get('cart', {})
    for product_id_str, quantity in cart.items():
        product = models.get_product(int(product_id_str))
        if product:
            models.add_to_db_cart(user_id, int(product_id_str), quantity)
    session.pop('cart', None)


def get_cart_count():
    """Количество товаров в корзине текущего пользователя (гостя или
    авторизованного) — используется в шапке сайта на каждой странице."""
    if current_user.is_authenticated:
        return models.get_db_cart_count(current_user.id)
    return sum(session.get('cart', {}).values())


def format_price(value):
    return f'{value:,.0f}'.replace(',', ' ')


STATUS_CLASSES = {
    'Новый': 'new',
    'Оплачен': 'paid',
    'В обработке': 'processing',
    'Отправлен': 'shipped',
    'Выполнен': 'done',
}


def status_class(status):
    """CSS-класс для цветной плашки статуса заказа (латиница — не завязываемся
    на экранирование кириллицы в селекторах)."""
    return STATUS_CLASSES.get(status, 'new')


def review_word(n):
    """Склонение слова «отзыв» под число (1 отзыв, 2 отзыва, 5 отзывов)."""
    if n % 10 == 1 and n % 100 != 11:
        return 'отзыв'
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return 'отзыва'
    return 'отзывов'


def product_image_url(image):
    """Единая точка разрешения фото товара: внешний URL демо-товаров
    (picsum.photos) отдаётся как есть, локально загруженный файл — через
    static. Используется во всех шаблонах, где показывается фото товара."""
    if not image:
        return None
    if image.startswith('http://') or image.startswith('https://'):
        return image
    return url_for('static', filename=f'images/products/{image}')
