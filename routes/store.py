"""Storefront blueprint serving the public catalog, product details, and search."""
from flask import Blueprint, abort, render_template, request

store_bp = Blueprint("store", __name__)


@store_bp.route("/")
def home():
    """Render the public storefront homepage."""
    # TODO: Fetch featured products and category hierarchy via catalog service
    return render_template("store/home.html")


@store_bp.route("/products")
def product_list():
    """Display paginated list of catalog products filtered by optional category."""
    # TODO: Parse query params (page, category_id, sort)
    # TODO: Delegate product retrieval and pagination to catalog service
    return render_template("store/home.html")


@store_bp.route("/product/<int:product_id>")
def product_detail(product_id: int):
    """Display individual product detail view."""
    # TODO: Fetch product by product_id from service or abort(404)
    # TODO: Pass product data to template
    return render_template("store/product.html", product_id=product_id)


@store_bp.route("/search")
def search():
    """Execute catalog keyword search and render matching products."""
    query = request.args.get("q", "").strip()
    # TODO: Query search_service.search_catalog(query)
    # TODO: Retrieve matching Product entities and pass to search template
    return render_template("store/home.html", search_query=query)
