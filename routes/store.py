"""Storefront blueprint serving the public catalog, product details, and search."""
from flask import Blueprint, abort, jsonify, render_template, request
from services import search_service

store_bp = Blueprint("store", __name__)


@store_bp.route("/")
def home():
    """Render the public storefront homepage."""
    products = search_service.list_products(per_page=100)
    return render_template("store/home.html", products=products.items,
                           categories=search_service.get_categories())


@store_bp.route("/products")
def product_list():
    """Display paginated list of catalog products filtered by optional category."""
    raw_category = request.args.get("category_id")
    if raw_category and (not raw_category.isdigit() or int(raw_category) < 1):
        abort(400)
    page = request.args.get("page", 1, type=int) or 1
    sort = request.args.get("sort", "name")
    if sort not in {"name", "price", "-price"}:
        abort(400)
    pagination = search_service.list_products(
        page=page, category_id=int(raw_category) if raw_category else None, sort=sort
    )
    return render_template("store/home.html", products=pagination.items, pagination=pagination,
                           categories=search_service.get_categories(), category_id=raw_category)


@store_bp.route("/product/<int:product_id>")
def product_detail(product_id: int):
    """Display individual product detail view."""
    product = search_service.get_product(product_id)
    if product is None:
        abort(404)
    return render_template("store/product.html", product=product)


@store_bp.route("/search")
def search():
    """Execute catalog keyword search and render matching products."""
    query = request.args.get("q", "").strip()
    product_ids = search_service.search_catalog(query)
    products = search_service.products_by_ids(product_ids)
    return render_template("store/home.html", products=products,
                           categories=search_service.get_categories(), search_query=query)


@store_bp.get("/autocomplete")
def autocomplete():
    prefix = request.args.get("q", "").strip()
    if len(prefix) > 100:
        abort(400)
    return jsonify(suggestions=search_service.autocomplete_query(prefix))
