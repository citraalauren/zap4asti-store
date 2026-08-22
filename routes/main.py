from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import models
from utils.helpers import product_image_url

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    category = request.args.get('category') or None
    if category not in (None, *models.CATEGORIES.keys()):
        category = None
    search = request.args.get('q', '').strip() or None
    page = request.args.get('page', 1, type=int)

    products, total, total_pages, page = models.get_products(
        category=category, search=search, page=page, per_page=12
    )

    return render_template(
        'index.html',
        products=products,
        total=total,
        total_pages=total_pages,
        page=page,
        current_category=category,
        search=search or '',
    )


@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = models.get_product(product_id)
    if not product:
        abort(404)

    reviews = models.get_reviews_for_product(product_id)
    avg_rating, review_count = models.get_product_rating(product_id)

    can_review = False
    if current_user.is_authenticated:
        can_review = (
            models.has_purchased(current_user.id, product_id)
            and not models.has_reviewed(current_user.id, product_id)
        )

    cover_url = product_image_url(product['image'])
    gallery_urls = [product_image_url(row['image']) for row in models.get_product_images(product_id)]
    image_urls = ([cover_url] if cover_url else []) + [url for url in gallery_urls if url]

    return render_template(
        'product.html',
        product=product,
        reviews=reviews,
        avg_rating=avg_rating,
        review_count=review_count,
        can_review=can_review,
        image_urls=image_urls,
    )


@main_bp.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    product = models.get_product(product_id)
    if not product:
        abort(404)

    if not models.has_purchased(current_user.id, product_id):
        flash('Оставлять отзыв может только покупатель этого товара.', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))

    if models.has_reviewed(current_user.id, product_id):
        flash('Вы уже оставили отзыв на этот товар.', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))

    rating = request.form.get('rating', type=int)
    text = request.form.get('text', '').strip()

    if not rating or not (1 <= rating <= 5) or not text:
        flash('Укажите рейтинг (1–5) и текст отзыва.', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))

    models.create_review(product_id, current_user.id, rating, text)
    flash('Спасибо за отзыв!', 'success')
    return redirect(url_for('main.product_detail', product_id=product_id))
