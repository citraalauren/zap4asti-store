"""Обновляет картинки товаров в shop.db на тематичные изображения с LoremFlickr,
чтобы они соответствовали названию и категории товара (вместо случайных
картинок с picsum.photos, среди которых иногда попадался фламинго).

Для каждого товара подобран список кандидатов-ключевых слов от самого
конкретного к самому общему. Скрипт живьём проверяет каждый URL и
использует первый, который реально отдаёт картинку (HTTP 200) — так как
LoremFlickr отдаёт HTTP 500 для некоторых сочетаний ключевых слов, слепая
подстановка ключевого слова без проверки может привести к битой ссылке.

Запуск:
    python update_images.py
"""
import sqlite3
import time
import urllib.error
import urllib.request

DB_PATH = 'shop.db'
IMAGE_BASE = 'https://loremflickr.com/400/400'

# Кандидаты ключевых слов на товар (id -> список от самого конкретного к
# самому общему). Последним в списке у каждого товара стоит ключевое слово,
# проверенное как надёжно рабочее на момент написания скрипта.
KEYWORD_CANDIDATES = {
    1: ['processor,cpu', 'intel,cpu', 'chip', 'circuit', 'computer'],   # Intel Core i5-13600K
    2: ['processor,cpu', 'intel,cpu', 'chip', 'circuit', 'computer'],   # Intel Core i9-14900K
    3: ['processor,cpu', 'amd,cpu', 'chip', 'circuit', 'computer'],     # AMD Ryzen 5 7600X
    4: ['processor,cpu', 'amd,cpu', 'chip', 'circuit', 'computer'],     # AMD Ryzen 7 7800X3D
    5: ['graphics-card,gpu', 'nvidia,gpu', 'gpu', 'graphics-card', 'computer'],  # RTX 4070
    6: ['graphics-card,gpu', 'nvidia,gpu', 'gpu', 'graphics-card', 'computer'],  # RTX 4080 SUPER
    7: ['graphics-card,gpu', 'amd,gpu', 'gpu', 'graphics-card', 'computer'],     # RX 7800 XT
    8: ['graphics-card,gpu', 'nvidia,gpu', 'gpu', 'graphics-card', 'computer'],  # RTX 4060 Ti
    9: ['ram,memory', 'ram', 'computer'],   # Kingston FURY Beast 16GB DDR5
    10: ['ram,memory', 'ram', 'computer'],  # Corsair Vengeance 32GB DDR5
    11: ['ram,memory', 'ram', 'computer'],  # G.Skill Trident Z5 32GB DDR5
    12: ['ssd,hard-drive', 'ssd', 'harddrive', 'computer'],  # Samsung 980 PRO NVMe SSD
    13: ['ssd,hard-drive', 'ssd', 'harddrive', 'computer'],  # WD Black SN850X NVMe SSD
    14: ['hard-drive,storage', 'harddrive,storage', 'harddrive', 'ssd', 'computer'],  # Seagate Barracuda HDD
    15: ['ssd,hard-drive', 'ssd', 'harddrive', 'computer'],  # Kingston NV2 NVMe SSD
    16: ['power-supply,psu', 'battery,psu', 'battery', 'computer'],  # Corsair RM750x
    17: ['power-supply,psu', 'battery,psu', 'battery', 'computer'],  # be quiet! Straight Power 11
    18: ['power-supply,psu', 'battery,psu', 'battery', 'computer'],  # DeepCool PF600
    19: ['computer-case,pc-case', 'pc-case,case', 'case', 'computer'],  # NZXT H510 Flow
    20: ['computer-case,pc-case', 'pc-case,case', 'case', 'computer'],  # Lian Li Lancool 215
}

# Резервное ключевое слово по категории — используется, если для товара нет
# записи в KEYWORD_CANDIDATES (например, товар был добавлен вручную позже).
CATEGORY_FALLBACK = {
    'cpu': ['processor,cpu', 'chip', 'circuit', 'computer'],
    'gpu': ['graphics-card,gpu', 'gpu', 'graphics-card', 'computer'],
    'ram': ['ram,memory', 'ram', 'computer'],
    'storage': ['ssd,hard-drive', 'ssd', 'harddrive', 'computer'],
    'psu': ['power-supply,psu', 'battery,psu', 'battery', 'computer'],
    'case': ['computer-case,pc-case', 'pc-case,case', 'case', 'computer'],
}

# Абсолютный запасной вариант, если вообще ни один кандидат не сработал —
# LoremFlickr без ключевого слова отдаёт случайное фото, но всегда отвечает
# HTTP 200/302, так что товар точно не останется без картинки.
LAST_RESORT_URL = IMAGE_BASE

TRIES_PER_CANDIDATE = 2
RETRY_DELAY_SECONDS = 2


def url_is_working(url):
    """Делает реальный HTTP-запрос и проверяет, что LoremFlickr отдал
    картинку (200 после редиректа), а не ошибку (например 500)."""
    for attempt in range(TRIES_PER_CANDIDATE):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        if attempt < TRIES_PER_CANDIDATE - 1:
            time.sleep(RETRY_DELAY_SECONDS)
    return False


def pick_working_image_url(product_id, category):
    candidates = KEYWORD_CANDIDATES.get(product_id) or CATEGORY_FALLBACK[category]
    for keyword in candidates:
        url = f'{IMAGE_BASE}/{keyword}'
        if url_is_working(url):
            return url, keyword
    return LAST_RESORT_URL, None


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    products = conn.execute('SELECT id, name, category, image FROM products ORDER BY id').fetchall()

    if not products:
        print('В базе данных нет товаров — нечего обновлять.')
        conn.close()
        return

    print(f'Найдено товаров: {len(products)}. Подбираю рабочие картинки...\n')

    updated = 0
    for product in products:
        image_url, matched_keyword = pick_working_image_url(product['id'], product['category'])
        conn.execute('UPDATE products SET image = ? WHERE id = ?', (image_url, product['id']))
        updated += 1
        label = matched_keyword or '(запасной вариант — все кандидаты недоступны)'
        print(f"  #{product['id']:<3} [{product['category']:<7}] {product['name']:<40} -> {label}")

    conn.commit()
    conn.close()
    print(f'\nГотово: обновлено {updated} товаров в {DB_PATH}.')


if __name__ == '__main__':
    main()
