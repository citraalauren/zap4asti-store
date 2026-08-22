from flask import (Blueprint, flash, redirect, render_template,
                    render_template_string, request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

import models
from utils.helpers import merge_session_cart

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('Заполните имя, email и пароль.', 'error')
            return render_template('register.html', name=name, email=email)

        if len(password) < 6:
            flash('Пароль должен быть не короче 6 символов.', 'error')
            return render_template('register.html', name=name, email=email)

        user = models.create_user(name, email, password)
        if not user:
            flash('Пользователь с таким email уже зарегистрирован.', 'error')
            return render_template('register.html', name=name, email=email)

        login_user(user)
        merge_session_cart(user.id)
        flash('Регистрация прошла успешно! Добро пожаловать.', 'success')
        return redirect(url_for('main.index'))

    return render_template('register.html', name='', email='')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = models.get_user_by_email(email)
        if not user or not user.check_password(password):
            flash('Неверный email или пароль.', 'error')
            return render_template('login.html', email=email)

        login_user(user)
        merge_session_cart(user.id)
        flash(f'С возвращением, {user.name}!', 'success')

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('main.index'))

    return render_template('login.html', email='')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))


# Отдельного profile.html в структуре проекта нет (см. фикс. список файлов),
# поэтому страница профиля рендерится строкой, расширяющей общий base.html.
_PROFILE_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Профиль — Zap4asti Store{% endblock %}
{% block content %}
<section class="profile-page" data-aos="fade-up">
  <h1>Профиль</h1>
  <div class="profile-card">
    <p><strong>Имя:</strong> {{ user.name }}</p>
    <p><strong>Email:</strong> {{ user.email }}</p>
    <p><strong>Роль:</strong> {{ 'Администратор' if user.is_admin else 'Покупатель' }}</p>
  </div>

  <h2>Мои заказы</h2>
  {% if orders %}
  <div class="orders-list">
    {% for order in orders %}
    <div class="order-card">
      <div class="order-card__header">
        <span>Заказ №{{ order.id }}</span>
        <span class="badge badge--{{ order.status|status_class }}">{{ order.status }}</span>
      </div>
      <p>Сумма: {{ order.total|price }} ₽</p>
      <p>Адрес: {{ order.address }}</p>
      <p class="order-card__date">{{ order.created_at }}</p>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <p>У вас пока нет заказов. <a href="{{ url_for('main.index') }}">Перейти в каталог</a></p>
  {% endif %}
</section>
{% endblock %}
"""


@auth_bp.route('/profile')
@login_required
def profile():
    orders = models.get_user_orders(current_user.id)
    return render_template_string(_PROFILE_TEMPLATE, user=current_user, orders=orders)
