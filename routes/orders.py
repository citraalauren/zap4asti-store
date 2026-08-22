from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import delivery
import models
from routes.cart import get_cart_items

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = get_cart_items()
    if not items:
        flash('Ваша корзина пуста.', 'error')
        return redirect(url_for('cart.view_cart'))

    total = sum(item['subtotal'] for item in items)
    providers = delivery.get_providers()

    if request.method == 'POST':
        delivery_type = request.form.get('delivery_type', 'courier')
        phone = request.form.get('phone', '').strip()
        comment = request.form.get('comment', '').strip()

        address = ''
        delivery_provider = None
        if delivery_type == 'pickup':
            delivery_provider = request.form.get('delivery_provider', '')
            city = request.form.get('delivery_city', '').strip()
            point = request.form.get('delivery_point', '').strip()
            valid_point = point in delivery.get_points(delivery_provider, city)
            if delivery_provider not in providers or not city or not valid_point:
                flash('Выберите службу доставки, город и пункт выдачи из списка.', 'error')
                return render_template('checkout.html', items=items, total=total, providers=providers)
            address = delivery.format_pickup_address(delivery_provider, city, point)
        else:
            delivery_type = 'courier'
            address = request.form.get('address', '').strip()
            if not address:
                flash('Укажите адрес доставки.', 'error')
                return render_template('checkout.html', items=items, total=total, providers=providers)

        if not phone:
            flash('Укажите телефон.', 'error')
            return render_template('checkout.html', items=items, total=total, providers=providers)

        order_items = [
            {
                'product_id': item['product_id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
            }
            for item in items
        ]
        order_id = models.create_order(current_user.id, address, phone, comment, order_items,
                                        delivery_type=delivery_type, delivery_provider=delivery_provider)
        return redirect(url_for('orders.pay', order_id=order_id))

    return render_template('checkout.html', items=items, total=total, providers=providers)


@orders_bp.route('/checkout/pay/<int:order_id>')
@login_required
def pay(order_id):
    order = models.get_order(order_id)
    if not order or order['user_id'] != current_user.id:
        abort(404)
    if order['status'] != 'Новый':
        return redirect(url_for('orders.success', order_id=order_id))
    return render_template('payment.html', order=order)


@orders_bp.route('/checkout/pay/<int:order_id>', methods=['POST'])
@login_required
def confirm_payment(order_id):
    ok = models.mark_order_paid(order_id, current_user.id)
    if not ok:
        flash('Не удалось оплатить заказ: он уже оплачен или не найден.', 'error')
        return redirect(url_for('cart.view_cart'))

    models.clear_db_cart(current_user.id)
    flash('Оплата прошла успешно!', 'success')
    return redirect(url_for('orders.success', order_id=order_id))


@orders_bp.route('/order/success/<int:order_id>')
@login_required
def success(order_id):
    order = models.get_order(order_id)
    if not order or order['user_id'] != current_user.id:
        abort(404)
    items = models.get_order_items(order_id)
    return render_template('order_success.html', order=order, items=items)
