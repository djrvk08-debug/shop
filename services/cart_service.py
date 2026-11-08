"""Cart service managing user session cart stored as a dictionary mapping product_id to quantity."""
from decimal import Decimal

from extensions import db
from models import Product


def _cart_quantities(cart: dict) -> dict[int, int]:
    quantities = {}
    for raw_id, value in (cart or {}).items():
        try:
            product_id = int(raw_id)
            quantity = int(value.get("quantity")) if isinstance(value, dict) else int(value)
        except (TypeError, ValueError, AttributeError):
            continue
        if product_id > 0 and quantity > 0:
            quantities[product_id] = quantity
    return quantities


def _product(product_id: int) -> Product:
    if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
        raise ValueError("A valid product is required.")
    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError("Product is unavailable.")
    return product


def _check_stock(product: Product, quantity: int) -> None:
    if quantity > product.stock:
        raise ValueError(f"Only {product.stock} units of {product.name} are in stock.")


def get_cart_items(cart: dict[int, int]) -> list[dict]:
    """Fetch product models and compute line totals for items currently in cart.

    :param cart: Session cart mapping product_id to quantity.
    :return: List of item dictionaries containing product details and line totals.
    """
    items = []
    for product_id, quantity in _cart_quantities(cart).items():
        product = _product(product_id)
        _check_stock(product, quantity)
        items.append({
            "product": product,
            "product_id": product.id,
            "quantity": quantity,
            "unit_price": Decimal(product.price),
            "line_total": Decimal(product.price) * quantity,
        })
    return items


def add_item(cart: dict[int, int], product_id: int, quantity: int = 1) -> dict[int, int]:
    """Add a quantity of product_id to the cart session dictionary.

    :param cart: Session cart mapping product_id to quantity.
    :param product_id: ID of the product to add.
    :param quantity: Number of units to add (must be positive).
    :return: Updated cart dictionary.
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive whole number.")
    product = _product(product_id)
    quantities = _cart_quantities(cart)
    new_quantity = quantities.get(product.id, 0) + quantity
    _check_stock(product, new_quantity)
    quantities[product.id] = new_quantity
    return quantities


def update_item(cart: dict[int, int], product_id: int, quantity: int) -> dict[int, int]:
    """Update the quantity of an existing item in the session cart.

    :param cart: Session cart mapping product_id to quantity.
    :param product_id: ID of the product to update.
    :param quantity: New quantity. If 0 or negative, remove the item.
    :return: Updated cart dictionary.
    """
    quantities = _cart_quantities(cart)
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError("Quantity must be a whole number.")
    if quantity <= 0:
        quantities.pop(int(product_id), None)
        return quantities
    product = _product(product_id)
    _check_stock(product, quantity)
    quantities[product.id] = quantity
    return quantities


def remove_item(cart: dict[int, int], product_id: int) -> dict[int, int]:
    """Remove a product from the cart dictionary.

    :param cart: Session cart mapping product_id to quantity.
    :param product_id: ID of the product to remove.
    :return: Updated cart dictionary.
    """
    quantities = _cart_quantities(cart)
    try:
        quantities.pop(int(product_id), None)
    except (TypeError, ValueError):
        pass
    return quantities


def total(cart: dict[int, int]) -> Decimal:
    """Calculate the subtotal value for all items in the session cart.

    :param cart: Session cart mapping product_id to quantity.
    :return: Total price as a Decimal.
    """
    return sum((item["line_total"] for item in get_cart_items(cart)), Decimal("0.00"))


def clear_cart(cart: dict[int, int]) -> dict[int, int]:
    """Empty the session cart dictionary.

    :param cart: Session cart mapping product_id to quantity.
    :return: An empty cart dictionary.
    """
    cart.clear()
    return cart
