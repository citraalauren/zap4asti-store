from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

import models

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')


def _get_session_cart_items():
    """Собирает гостевую корзину из сессии, дополняя данными о товаре.
    Если товар успели удалить из каталога — тихо убирает его из корзины."""
    cart = session.get('cart', {})
    items = []
    changed = False
    for product_id_str, quantity in list(cart.items()):
        product = models.get_product(int(product_id_str))
        if not product:
            del cart[product_id_str]
            changed = True
            continue
        items.append({
            'product_id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'image': product['image'],
            'quantity': quantity,
            'subtotal': product['price'] * quantity,
        })
    if changed:
        session['cart'] = cart
        session.modified = True
    return items


def get_cart_items():
    """Единая точка получения содержимого корзины — гостевой (сессия) или
    пользовательской (БД). Используется и в cart.py, и в orders.py."""
    if current_user.is_authenticated:
        return models.get_db_cart(current_user.id)
    return _get_session_cart_items()


@cart_bp.route('')
def view_cart():
    items = get_cart_items()
    total = sum(item['subtotal'] for item in items)
    return render_template('cart.html', items=items, total=total)


@cart_bp.route('/update/<int:product_id>', methods=['POST'])
def update(product_id):
    quantity = request.form.get('quantity', 1, type=int)

    if current_user.is_authenticated:
        models.update_db_cart_item(current_user.id, product_id, quantity)
    else:
        cart = session.get('cart', {})
        key = str(product_id)
        if quantity <= 0:
            cart.pop(key, None)
        elif key in cart:
            cart[key] = quantity
        session['cart'] = cart
        session.modified = True

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove(product_id):
    if current_user.is_authenticated:
        models.remove_from_db_cart(current_user.id, product_id)
    else:
        cart = session.get('cart', {})
        cart.pop(str(product_id), None)
        session['cart'] = cart
        session.modified = True

    flash('Товар удалён из корзины.', 'info')
    return redirect(url_for('cart.view_cart'))
