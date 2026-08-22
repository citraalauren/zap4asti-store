from routes.admin import admin_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.cart import cart_bp
from routes.main import main_bp
from routes.orders import orders_bp

__all__ = ['admin_bp', 'api_bp', 'auth_bp', 'cart_bp', 'main_bp', 'orders_bp']
