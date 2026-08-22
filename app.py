import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_talisman import Talisman
from flask_wtf import CSRFProtect

import models
from init_db import ensure_admin, seed_demo_data
from utils.helpers import format_price, product_image_url, review_word, status_class

# Явный путь к .env: под WSGI (PythonAnywhere и т. п.) текущая рабочая
# директория процесса не обязательно совпадает с папкой проекта, поэтому
# load_dotenv() без пути мог бы не найти файл.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    app.config['DATABASE'] = os.path.join(base_dir, os.environ.get('DATABASE', 'shop.db'))
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static', 'images', 'products')
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 МБ на загружаемое фото

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите, чтобы продолжить.'
    login_manager.login_message_category = 'info'

    csrf.init_app(app)

    # force_https/strict_transport_security/session_cookie_secure выключены:
    # сайт обслуживается по обычному HTTP в локальной сети (0.0.0.0), без TLS-сертификата.
    # С secure-cookie сессия и корзина не работали бы при заходе не с localhost.
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        session_cookie_secure=False,
        content_security_policy={
            'default-src': "'self'",
            'script-src': ["'self'", 'cdn.jsdelivr.net'],
            'style-src': ["'self'", 'cdn.jsdelivr.net'],
            'font-src': ["'self'", 'cdn.jsdelivr.net'],
            # loremflickr.com — текущий источник тематичных фото товаров (см. update_images.py);
            # picsum.photos/fastly.picsum.photos оставлены для товаров, которые ещё не обновлены,
            # или для БД, пересозданной заново из демо-данных (init_db.py).
            'img-src': ["'self'", 'data:', 'loremflickr.com', 'picsum.photos', 'fastly.picsum.photos'],
        },
    )

    app.teardown_appcontext(models.close_db)

    @login_manager.user_loader
    def load_user(user_id):
        return models.get_user_by_id(int(user_id))

    from routes import admin_bp, api_bp, auth_bp, cart_bp, main_bp, orders_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    app.jinja_env.filters['price'] = format_price
    app.jinja_env.filters['status_class'] = status_class
    app.jinja_env.filters['review_word'] = review_word
    app.jinja_env.globals['product_image_url'] = product_image_url

    @app.context_processor
    def inject_globals():
        from utils.helpers import get_cart_count
        return {'cart_count': get_cart_count(), 'CATEGORIES': models.CATEGORIES}

    with app.app_context():
        models.init_db(app.config['DATABASE'])
        seed_demo_data()
        ensure_admin()

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 3000))
    debug = os.environ.get('FLASK_DEBUG', 'False').strip().lower() == 'true'
    print(f'Zap4asti Store запущен: http://127.0.0.1:{port} (в локальной сети — по IP этого компьютера, порт {port})')
    app.run(host='0.0.0.0', port=port, debug=debug)
