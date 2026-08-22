from flask import Blueprint, jsonify, request, session
from flask_login import current_user

import delivery
import models
from utils.helpers import get_cart_count

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    """JSON-эндпоинт для кнопок «В корзину» — используется main.js для анимации
    «улёта» товара в иконку корзины и toast-уведомления без перезагрузки страницы."""
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get('product_id'))
        quantity = max(1, int(data.get('quantity', 1)))
    except (TypeError, ValueError):
        return jsonify(success=False, message='Некорректные данные.'), 400

    product = models.get_product(product_id)
    if not product:
        return jsonify(success=False, message='Товар не найден.'), 404

    if current_user.is_authenticated:
        models.add_to_db_cart(current_user.id, product_id, quantity)
    else:
        cart = session.get('cart', {})
        key = str(product_id)
        cart[key] = cart.get(key, 0) + quantity
        session['cart'] = cart
        session.modified = True

    return jsonify(
        success=True,
        message=f'«{product["name"]}» добавлен в корзину.',
        cart_count=get_cart_count(),
    )


@api_bp.route('/delivery/cities')
def delivery_cities():
    """Список городов, где есть пункты выдачи у выбранной службы —
    используется чекаутом для каскадного выбора провайдер -> город -> пункт."""
    provider = request.args.get('provider', '')
    if provider not in delivery.get_providers():
        return jsonify(cities=[])
    return jsonify(cities=delivery.get_cities(provider))


@api_bp.route('/delivery/points')
def delivery_points():
    provider = request.args.get('provider', '')
    city = request.args.get('city', '')
    if provider not in delivery.get_providers():
        return jsonify(points=[])
    return jsonify(points=delivery.get_points(provider, city))
