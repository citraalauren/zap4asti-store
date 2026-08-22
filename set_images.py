"""Вручную назначает конкретные, зафиксированные (не случайные) картинки товарам.

В отличие от update_images.py (который берёт случайное фото по ключевому слову
с loremflickr.com и оно меняется при каждом заходе на сайт), этот скрипт
проставляет ровно ту ссылку, которую вы сами укажете — она не будет меняться.

Как использовать:
1. Найдите в интернете (см. инструкцию в чате) картинку для нужного товара.
2. Если это страница с картинкой — кликните по картинке правой кнопкой ->
   "Копировать адрес картинки" (Copy image address). Ссылка должна вести
   ПРЯМО на файл и заканчиваться на .jpg/.png/.webp и т.п.
3. Впишите эту ссылку напротив нужного товара в словарь IMAGE_URLS ниже
   (замените None на 'https://...').
4. Запустите: python set_images.py
   На PythonAnywhere: активируйте venv (workon zap4asti-venv), затем
   cd ~/zap4asti-store && python set_images.py, и нажмите Reload на вкладке Web.

Товары, для которых оставлено None, останутся без изменений.
"""
import sqlite3
import urllib.error
import urllib.request

DB_PATH = 'shop.db'

# id -> ссылка на картинку. Впишите свои ссылки вместо None.
# id и названия товаров смотрите в админ-панели (/admin/products) —
# они идут в том же порядке, что и в каталоге по умолчанию.
IMAGE_URLS = {
    1: None,   # Intel Core i5-13600K
    2: None,   # Intel Core i9-14900K
    3: None,   # AMD Ryzen 5 7600X
    4: None,   # AMD Ryzen 7 7800X3D
    5: None,   # NVIDIA GeForce RTX 4070
    6: None,   # NVIDIA GeForce RTX 4080 SUPER
    7: None,   # AMD Radeon RX 7800 XT
    8: None,   # NVIDIA GeForce RTX 4060 Ti
    9: None,   # Kingston FURY Beast 16GB DDR5-5600
    10: None,  # Corsair Vengeance 32GB DDR5-6000
    11: None,  # G.Skill Trident Z5 32GB DDR5-6400
    12: None,  # Samsung 980 PRO 1TB NVMe SSD
    13: None,  # WD Black SN850X 2TB NVMe SSD
    14: None,  # Seagate Barracuda 2TB HDD
    15: None,  # Kingston NV2 1TB NVMe SSD
    16: None,  # Corsair RM750x 750W 80+ Gold
    17: None,  # be quiet! Straight Power 11 850W
    18: None,  # DeepCool PF600 600W
    19: None,  # NZXT H510 Flow
    20: None,  # Lian Li Lancool 215
}


def url_is_reachable(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    to_update = {pid: url for pid, url in IMAGE_URLS.items() if url}
    if not to_update:
        print('В IMAGE_URLS все ссылки — None, менять нечего. '
              'Впишите ссылки на картинки и запустите скрипт снова.')
        conn.close()
        return

    for product_id, url in to_update.items():
        row = conn.execute('SELECT name FROM products WHERE id = ?', (product_id,)).fetchone()
        if not row:
            print(f'  #{product_id}: товар с таким id не найден, пропускаю.')
            continue

        ok = url_is_reachable(url)
        status = 'OK' if ok else 'НЕ ОТКРЫЛАСЬ (проверьте ссылку!)'
        print(f"  #{product_id} {row['name']:<40} -> {status}")

        conn.execute('UPDATE products SET image = ? WHERE id = ?', (url, product_id))

    conn.commit()
    conn.close()
    print(f'\nГотово: обновлено {len(to_update)} товаров.')


if __name__ == '__main__':
    main()
