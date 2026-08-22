from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

import models
from utils.helpers import (admin_required, allowed_file, delete_product_image,
                            save_product_image)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _validate_product_form(form, image_file, gallery_files=None):
    errors = []
    name = form.get('name', '').strip()
    category = form.get('category', '')
    price = form.get('price', type=float)
    description = form.get('description', '').strip()

    if not name:
        errors.append('Укажите название товара.')
    if category not in models.CATEGORIES:
        errors.append('Выберите корректную категорию.')
    if price is None or price < 0:
        errors.append('Укажите корректную цену (число не меньше 0).')
    if image_file and image_file.filename and not allowed_file(image_file.filename):
        errors.append('Недопустимый формат обложки (разрешены png, jpg, jpeg, webp, gif).')
    for gallery_file in (gallery_files or []):
        if not allowed_file(gallery_file.filename):
            errors.append(f'Недопустимый формат файла «{gallery_file.filename}» в дополнительных фото.')

    return errors, name, category, price, description


@admin_bp.route('/')
@admin_required
def dashboard():
    products = models.get_all_products_admin()
    orders = models.get_all_orders()
    reviews = models.get_all_reviews_admin()

    stats = {
        'products_count': len(products),
        'orders_count': len(orders),
        'reviews_count': len(reviews),
        'revenue': sum(o['total'] for o in orders if o['status'] != 'Новый'),
    }
    return render_template('admin/dashboard.html', stats=stats, recent_orders=orders[:5])


@admin_bp.route('/products')
@admin_required
def products():
    return render_template('admin/products.html', products=models.get_all_products_admin())


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        image_file = request.files.get('image')
        gallery_files = [f for f in request.files.getlist('images') if f and f.filename]
        errors, name, category, price, description = _validate_product_form(
            request.form, image_file, gallery_files)
        values = {'name': name, 'category': category, 'price': request.form.get('price', ''),
                  'description': description}

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin/edit_product.html', product=None,
                                    categories=models.CATEGORIES, values=values, gallery=[])

        image_name = None
        if image_file and image_file.filename:
            try:
                image_name = save_product_image(image_file)
            except OSError:
                flash('Не удалось обработать обложку — файл повреждён или это не картинка.', 'error')
                return render_template('admin/edit_product.html', product=None,
                                        categories=models.CATEGORIES, values=values, gallery=[])

        product_id = models.create_product(name, category, price, description, image_name)

        for order, gallery_file in enumerate(gallery_files):
            try:
                filename = save_product_image(gallery_file)
            except OSError:
                flash(f'Файл «{gallery_file.filename}» повреждён и не был добавлен.', 'error')
                continue
            models.add_product_image(product_id, filename, sort_order=order)

        flash('Товар добавлен.', 'success')
        return redirect(url_for('admin.products'))

    empty_values = {'name': '', 'category': '', 'price': '', 'description': ''}
    return render_template('admin/edit_product.html', product=None, categories=models.CATEGORIES,
                            values=empty_values, gallery=[])


@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = models.get_product(product_id)
    if not product:
        abort(404)

    if request.method == 'POST':
        image_file = request.files.get('image')
        gallery_files = [f for f in request.files.getlist('images') if f and f.filename]
        errors, name, category, price, description = _validate_product_form(
            request.form, image_file, gallery_files)
        values = {'name': name, 'category': category, 'price': request.form.get('price', ''),
                  'description': description}

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin/edit_product.html', product=product,
                                    categories=models.CATEGORIES, values=values,
                                    gallery=models.get_product_images(product_id))

        new_image_name = None
        if image_file and image_file.filename:
            try:
                new_image_name = save_product_image(image_file)
            except OSError:
                flash('Не удалось обработать обложку — файл повреждён или это не картинка.', 'error')
                return render_template('admin/edit_product.html', product=product,
                                        categories=models.CATEGORIES, values=values,
                                        gallery=models.get_product_images(product_id))
            delete_product_image(product['image'])

        models.update_product(product_id, name, category, price, description, image=new_image_name)

        existing_count = len(models.get_product_images(product_id))
        for order, gallery_file in enumerate(gallery_files):
            try:
                filename = save_product_image(gallery_file)
            except OSError:
                flash(f'Файл «{gallery_file.filename}» повреждён и не был добавлен.', 'error')
                continue
            models.add_product_image(product_id, filename, sort_order=existing_count + order)

        flash('Товар обновлён.', 'success')
        return redirect(url_for('admin.products'))

    values = {'name': product['name'], 'category': product['category'],
              'price': product['price'], 'description': product['description']}
    return render_template('admin/edit_product.html', product=product, categories=models.CATEGORIES,
                            values=values, gallery=models.get_product_images(product_id))


@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    image_names = models.delete_product(product_id)
    for image_name in image_names:
        delete_product_image(image_name)
    flash('Товар удалён.', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/<int:product_id>/images/<int:image_id>/delete', methods=['POST'])
@admin_required
def delete_gallery_image(product_id, image_id):
    image_name = models.delete_product_image_row(product_id, image_id)
    if image_name:
        delete_product_image(image_name)
        flash('Фото удалено.', 'success')
    return redirect(url_for('admin.edit_product', product_id=product_id))


@admin_bp.route('/orders')
@admin_required
def orders():
    return render_template('admin/orders.html', orders=models.get_all_orders(), statuses=models.ORDER_STATUSES)


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    status = request.form.get('status')
    if status not in models.ORDER_STATUSES:
        flash('Некорректный статус.', 'error')
        return redirect(url_for('admin.orders'))

    models.update_order_status(order_id, status)
    flash('Статус заказа обновлён.', 'success')
    return redirect(url_for('admin.orders'))


@admin_bp.route('/reviews')
@admin_required
def reviews():
    return render_template('admin/reviews.html', reviews=models.get_all_reviews_admin())


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def delete_review(review_id):
    models.delete_review(review_id)
    flash('Отзыв удалён.', 'success')
    return redirect(url_for('admin.reviews'))
