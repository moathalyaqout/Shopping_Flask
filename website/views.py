from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Product, CartProduct, Cart, Review
from sqlalchemy import asc, desc
from . import db
import json

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    total_items = 0
    if cart:
        total_items = sum(item.quantity for item in cart.products)


    products = Product.query.order_by(asc(getattr(Product, "name"))).all()

    return render_template("home.html", user=current_user, products=products, total_items=total_items)


@views.route('/product-details/<int:product_id>', methods=['GET'])
@login_required
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'name': product.name,
        'price': str(product.price),
        'description': product.description,
        'image': product.image,
        'impact': product.environmental_impact
    })


@views.route('/product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    total_items = sum(item.quantity for item in cart.products) if cart.products else 0
    reviews = Review.query.filter_by(product_id=product_id).all()

    if request.method == 'POST':
        content = request.form.get('content')
        rating = request.form.get('rating')
        if not content or not rating:
            flash('Review content and rating are required.', 'error')
        else:
            review = Review(content=content, rating=int(rating), user_id=current_user.id, product_id=product_id)
            db.session.add(review)
            db.session.commit()
            flash('Your review has been added.', 'success')
            # Redirect to the same page to show the updated list of reviews
            return redirect(url_for('views.product_detail', product_id=product_id))

    return render_template("product_details.html", user=current_user, product=product, total_items=total_items, reviews=reviews)

@views.route('/sort-products', methods=['GET'])
@login_required
def sort_products():
    sort_option = request.args.get('sort', 'name')  # Default sort by name

    products = Product.query.order_by(asc(getattr(Product, sort_option))).all()

    products_data = [{
        'id': product.id,
        'name': product.name,
        'price': str(product.price),
        'description': product.description,
        'image': product.image,
        'impact': product.environmental_impact
    } for product in products]

    return jsonify(products_data)


@views.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    # Check if the cart exists or create a new one
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)

    # Check if the product is already in the cart
    cart_product = CartProduct.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_product:
        cart_product.quantity += 1  # Increase quantity if product is already in the cart
    else:
        # Add new product to the cart
        new_cart_product = CartProduct(cart_id=cart.id, product_id=product_id, quantity=1)
        db.session.add(new_cart_product)

    db.session.commit()

    # Calculate the total number of items in the cart
    total_items = sum(item.quantity for item in cart.products)

    return jsonify({'cartCount': total_items})



@views.route('/cart')
@login_required
def show_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    formatted_total= 0
    if not cart:
        flash('Your cart is empty!', 'info')
        return render_template('cart.html', items=[], total=0)

    # Fetch all cart products and their details
    cart_products = CartProduct.query.filter_by(cart_id=cart.id).all()

    items = []
    total = 0
    for cp in cart_products:
        # Fetch product details from the Product model using the product_id from cp
        product = Product.query.get(cp.product_id)
        if not product:
            continue  # Skip this iteration if the product is not found

        item = {
            'id': product.id,
            'cartProduct_Id' : cp.id,
            'name': product.name,
            'price': product.price,
            'quantity': cp.quantity,
            'subtotal': cp.quantity * product.price,
            'image': product.image  # Assuming your product model has an 'image' field
        }
        items.append(item)
        total += item['subtotal']
        formatted_total = format(total, ".2f")  # Ensures two decimal places
    return render_template('cart.html', user=current_user, items=items, total=formatted_total)


@views.route('/remove-from-cart/<int:cart_product_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_product_id):
    # Retrieve the CartProduct instance
    cart_product = CartProduct.query.get_or_404(cart_product_id)

    # Security check to ensure the user is modifying their own cart
    if cart_product.cart.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return jsonify({'error': 'Unauthorized'}), 403

    # Remove the product from the database
    db.session.delete(cart_product)
    db.session.commit()

    flash('Item removed successfully.', 'success')
    return jsonify({'success': 'Item removed successfully', 'cartProductId': cart_product_id})


@views.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    # Retrieve the user's cart
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        # If no cart exists, return a simple error message
        return jsonify({'error': 'No cart to clear'}), 404

    # Retrieve all cart products and delete them
    cart_products = CartProduct.query.filter_by(cart_id=cart.id).all()
    for product in cart_products:
        db.session.delete(product)

    # Commit changes to the database
    db.session.commit()

    flash('Your cart has been cleared!', 'success')
    return jsonify({'success': 'Cart cleared successfully'}), 200


@views.route('/checkout', methods=['GET'])
@login_required
def checkout():
    return render_template('checkout.html', user=current_user)

