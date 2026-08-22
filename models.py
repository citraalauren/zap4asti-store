import sqlite3

import bcrypt
from flask import current_app, g
from flask_login import UserMixin

# Категории товаров: slug -> отображаемое имя (используется в CHECK-констрейнте
# таблицы products и в фильтрах каталога)
CATEGORIES = {
    'cpu': 'Процессоры',
    'gpu': 'Видеокарты',
    'ram': 'Оперативная память',
    'storage': 'Накопители',
    'psu': 'Блоки питания',
    'case': 'Корпуса',
}

# Статусы заказа в порядке жизненного цикла
ORDER_STATUSES = ['Новый', 'Оплачен', 'В обработке', 'Отправлен', 'Выполнен']

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('cpu', 'gpu', 'ram', 'storage', 'psu', 'case')),
    price REAL NOT NULL CHECK(price >= 0),
    description TEXT NOT NULL DEFAULT '',
    image TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
    UNIQUE(user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Новый',
    total REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(product_id, user_id)
);
"""


def init_db(db_path):
    """Создаёт таблицы БД, если их ещё нет. Не привязана к контексту Flask —
    вызывается как из app.py при старте, так и из standalone-скрипта init_db.py."""
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn):
    """Точечные миграции для баз, созданных до появления новых колонок —
    CREATE TABLE IF NOT EXISTS не добавляет колонки в уже существующую таблицу."""
    columns = {row[1] for row in conn.execute('PRAGMA table_info(orders)').fetchall()}
    if 'delivery_type' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN delivery_type TEXT NOT NULL DEFAULT 'courier'")
    if 'delivery_provider' not in columns:
        conn.execute('ALTER TABLE orders ADD COLUMN delivery_provider TEXT')


def get_db():
    """Возвращает соединение с БД для текущего контекста приложения Flask."""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.name = row['name']
        self.email = row['email']
        self.password_hash = row['password_hash']
        self.role = row['role']

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


def _hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')


def create_user(name, email, password, role='user'):
    """Создаёт пользователя. Возвращает User либо None, если email уже занят."""
    db = get_db()
    try:
        cur = db.execute(
            'INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)',
            (name, email, _hash_password(password), role),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None
    return get_user_by_id(cur.lastrowid)


def get_user_by_id(user_id):
    row = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return User(row) if row else None


def get_user_by_email(email):
    row = get_db().execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    return User(row) if row else None


# ---------------------------------------------------------------------------
# Товары
# ---------------------------------------------------------------------------

def get_products(category=None, search=None, page=1, per_page=12):
    db = get_db()
    where = []
    params = []
    if category:
        where.append('category = ?')
        params.append(category)
    if search:
        where.append('name LIKE ?')
        params.append(f'%{search}%')
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    total = db.execute(f'SELECT COUNT(*) FROM products {where_sql}', params).fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    rows = db.execute(
        f'SELECT * FROM products {where_sql} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
        params + [per_page, offset],
    ).fetchall()
    return rows, total, total_pages, page


def get_product(product_id):
    return get_db().execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()


def create_product(name, category, price, description, image):
    db = get_db()
    cur = db.execute(
        'INSERT INTO products (name, category, price, description, image) VALUES (?, ?, ?, ?, ?)',
        (name, category, price, description, image),
    )
    db.commit()
    return cur.lastrowid


def update_product(product_id, name, category, price, description, image=None):
    db = get_db()
    if image is not None:
        db.execute(
            'UPDATE products SET name=?, category=?, price=?, description=?, image=? WHERE id=?',
            (name, category, price, description, image, product_id),
        )
    else:
        db.execute(
            'UPDATE products SET name=?, category=?, price=?, description=? WHERE id=?',
            (name, category, price, description, product_id),
        )
    db.commit()


def delete_product(product_id):
    """Удаляет товар и возвращает имена файлов всех его фото (обложка +
    галерея) — чтобы вызывающий код удалил сами файлы с диска."""
    db = get_db()
    row = db.execute('SELECT image FROM products WHERE id = ?', (product_id,)).fetchone()
    gallery_rows = db.execute(
        'SELECT image FROM product_images WHERE product_id = ?', (product_id,)
    ).fetchall()
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    images = [row['image']] if row else []
    images += [r['image'] for r in gallery_rows]
    return images


def get_all_products_admin():
    return get_db().execute('SELECT * FROM products ORDER BY created_at DESC, id DESC').fetchall()


# ---------------------------------------------------------------------------
# Дополнительные фото товара (галерея)
# ---------------------------------------------------------------------------

def get_product_images(product_id):
    return get_db().execute(
        'SELECT * FROM product_images WHERE product_id = ? ORDER BY sort_order, id',
        (product_id,),
    ).fetchall()


def add_product_image(product_id, image, sort_order=0):
    db = get_db()
    db.execute(
        'INSERT INTO product_images (product_id, image, sort_order) VALUES (?, ?, ?)',
        (product_id, image, sort_order),
    )
    db.commit()


def delete_product_image_row(product_id, image_id):
    """Удаляет одну картинку из галереи товара. Возвращает имя файла для
    удаления с диска, либо None, если такой картинки у этого товара нет."""
    db = get_db()
    row = db.execute(
        'SELECT image FROM product_images WHERE id = ? AND product_id = ?',
        (image_id, product_id),
    ).fetchone()
    if not row:
        return None
    db.execute('DELETE FROM product_images WHERE id = ?', (image_id,))
    db.commit()
    return row['image']


# ---------------------------------------------------------------------------
# Корзина (БД — для авторизованных пользователей)
# ---------------------------------------------------------------------------

def get_db_cart(user_id):
    return get_db().execute(
        """SELECT ci.product_id AS product_id, ci.quantity AS quantity,
                  p.name AS name, p.price AS price, p.image AS image,
                  (ci.quantity * p.price) AS subtotal
           FROM cart_items ci JOIN products p ON p.id = ci.product_id
           WHERE ci.user_id = ?
           ORDER BY ci.id""",
        (user_id,),
    ).fetchall()


def add_to_db_cart(user_id, product_id, quantity=1):
    db = get_db()
    existing = db.execute(
        'SELECT quantity FROM cart_items WHERE user_id=? AND product_id=?', (user_id, product_id)
    ).fetchone()
    if existing:
        db.execute(
            'UPDATE cart_items SET quantity=? WHERE user_id=? AND product_id=?',
            (existing['quantity'] + quantity, user_id, product_id),
        )
    else:
        db.execute(
            'INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)',
            (user_id, product_id, quantity),
        )
    db.commit()


def update_db_cart_item(user_id, product_id, quantity):
    db = get_db()
    if quantity <= 0:
        remove_from_db_cart(user_id, product_id)
        return
    db.execute(
        'UPDATE cart_items SET quantity=? WHERE user_id=? AND product_id=?',
        (quantity, user_id, product_id),
    )
    db.commit()


def remove_from_db_cart(user_id, product_id):
    db = get_db()
    db.execute('DELETE FROM cart_items WHERE user_id=? AND product_id=?', (user_id, product_id))
    db.commit()


def clear_db_cart(user_id):
    db = get_db()
    db.execute('DELETE FROM cart_items WHERE user_id=?', (user_id,))
    db.commit()


def get_db_cart_count(user_id):
    row = get_db().execute(
        'SELECT COALESCE(SUM(quantity), 0) AS c FROM cart_items WHERE user_id=?', (user_id,)
    ).fetchone()
    return row['c']


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------

def create_order(user_id, address, phone, comment, items, delivery_type='courier', delivery_provider=None):
    """items: список dict {product_id, name, price, quantity}. Возвращает id заказа."""
    db = get_db()
    total = sum(i['price'] * i['quantity'] for i in items)
    cur = db.execute(
        'INSERT INTO orders (user_id, address, phone, comment, status, total, delivery_type, delivery_provider) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (user_id, address, phone, comment, 'Новый', total, delivery_type, delivery_provider),
    )
    order_id = cur.lastrowid
    db.executemany(
        'INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (?, ?, ?, ?, ?)',
        [(order_id, i['product_id'], i['name'], i['price'], i['quantity']) for i in items],
    )
    db.commit()
    return order_id


def get_order(order_id):
    return get_db().execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()


def get_order_items(order_id):
    return get_db().execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()


def get_user_orders(user_id):
    return get_db().execute(
        'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC, id DESC', (user_id,)
    ).fetchall()


def get_all_orders():
    return get_db().execute(
        """SELECT o.*, u.name AS user_name, u.email AS user_email
           FROM orders o JOIN users u ON u.id = o.user_id
           ORDER BY o.created_at DESC, o.id DESC"""
    ).fetchall()


def update_order_status(order_id, status):
    db = get_db()
    db.execute('UPDATE orders SET status=? WHERE id=?', (status, order_id))
    db.commit()


def mark_order_paid(order_id, user_id):
    """Переводит заказ в статус 'Оплачен', только если он принадлежит пользователю
    и ещё не оплачен. Возвращает True при успехе."""
    db = get_db()
    row = db.execute(
        'SELECT status FROM orders WHERE id=? AND user_id=?', (order_id, user_id)
    ).fetchone()
    if not row or row['status'] != 'Новый':
        return False
    db.execute("UPDATE orders SET status='Оплачен' WHERE id=?", (order_id,))
    db.commit()
    return True


def has_purchased(user_id, product_id):
    row = get_db().execute(
        """SELECT 1 FROM order_items oi JOIN orders o ON o.id = oi.order_id
           WHERE o.user_id = ? AND oi.product_id = ? AND o.status != 'Новый' LIMIT 1""",
        (user_id, product_id),
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Отзывы
# ---------------------------------------------------------------------------

def create_review(product_id, user_id, rating, text):
    db = get_db()
    try:
        cur = db.execute(
            'INSERT INTO reviews (product_id, user_id, rating, text) VALUES (?, ?, ?, ?)',
            (product_id, user_id, rating, text),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None
    return cur.lastrowid


def has_reviewed(user_id, product_id):
    row = get_db().execute(
        'SELECT 1 FROM reviews WHERE user_id=? AND product_id=?', (user_id, product_id)
    ).fetchone()
    return row is not None


def get_reviews_for_product(product_id):
    return get_db().execute(
        """SELECT r.*, u.name AS user_name FROM reviews r
           JOIN users u ON u.id = r.user_id
           WHERE r.product_id = ? ORDER BY r.created_at DESC, r.id DESC""",
        (product_id,),
    ).fetchall()


def get_product_rating(product_id):
    row = get_db().execute(
        'SELECT AVG(rating) AS avg_rating, COUNT(*) AS cnt FROM reviews WHERE product_id=?',
        (product_id,),
    ).fetchone()
    avg = round(row['avg_rating'], 1) if row['avg_rating'] is not None else 0
    return avg, row['cnt']


def get_all_reviews_admin():
    return get_db().execute(
        """SELECT r.*, u.name AS user_name, p.name AS product_name
           FROM reviews r JOIN users u ON u.id = r.user_id JOIN products p ON p.id = r.product_id
           ORDER BY r.created_at DESC, r.id DESC"""
    ).fetchall()


def delete_review(review_id):
    db = get_db()
    db.execute('DELETE FROM reviews WHERE id=?', (review_id,))
    db.commit()
