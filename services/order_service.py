"""Order service handling checkout workflow and state machine transitions."""
from typing import Any
from decimal import Decimal

from sqlalchemy.orm import joinedload, selectinload
from extensions import db
from models import Order, OrderItem, Product

# State machine defining valid order lifecycle transitions
ORDER_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["paid", "cancelled"],
    "paid": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered", "returned"],
    "delivered": ["refunded"],
    "cancelled": [],
    "returned": ["refunded"],
    "refunded": [],
}


def checkout(user_id: int, cart: dict[int, int]) -> Any:
    """Create a new order from items in the session cart within an atomic transaction.

    :param user_id: ID of the purchasing customer.
    :param cart: Session cart dictionary mapping product_id to quantity.
    :return: Created Order model instance.
    :raises ValueError: If cart is empty or stock is insufficient.
    """
    quantities = {}
    for raw_id, value in (cart or {}).items():
        try:
            product_id = int(raw_id)
            quantity = int(value.get("quantity")) if isinstance(value, dict) else int(value)
        except (TypeError, ValueError, AttributeError):
            raise ValueError("Cart contains invalid items.")
        if product_id <= 0 or quantity <= 0:
            raise ValueError("Cart quantities must be positive whole numbers.")
        quantities[product_id] = quantities.get(product_id, 0) + quantity
    if not quantities:
        raise ValueError("Your cart is empty.")

    try:
        products = Product.query.filter(Product.id.in_(quantities)).with_for_update().all()
        products_by_id = {product.id: product for product in products}
        if len(products_by_id) != len(quantities):
            raise ValueError("One or more products are no longer available.")
        for product_id, quantity in quantities.items():
            product = products_by_id[product_id]
            if quantity > product.stock:
                raise ValueError(f"Insufficient stock for {product.name}.")

        total_amount = sum(
            (Decimal(products_by_id[product_id].price) * quantity
             for product_id, quantity in quantities.items()),
            Decimal("0.00"),
        )
        order = Order(user_id=user_id, status="pending", total=total_amount)
        db.session.add(order)
        db.session.flush()
        for product_id, quantity in quantities.items():
            product = products_by_id[product_id]
            product.stock -= quantity
            db.session.add(OrderItem(order_id=order.id, product_id=product_id,
                                     quantity=quantity, unit_price=product.price))
        db.session.commit()
        return order
    except Exception:
        db.session.rollback()
        raise


def change_status(order_id: int, new_status: str) -> Any:
    """Transition an existing order to a new status using the state machine.

    :param order_id: ID of the order to transition.
    :param new_status: Desired target order status.
    :return: Updated Order model instance.
    :raises ValueError: If the status transition is not permitted by ORDER_STATUS_TRANSITIONS.
    """
    order = db.session.get(Order, order_id)
    if order is None:
        raise ValueError("Order not found.")
    if new_status not in ORDER_STATUS_TRANSITIONS.get(order.status, []):
        raise ValueError(f"Invalid order status transition: {order.status} to {new_status}.")
    order.status = new_status
    db.session.commit()
    from services.notify_service import queue_notification
    queue_notification(
        recipient=order.user.email, channel="email", subject=f"Order {order.id} update",
        message=f"Your order status is now {new_status}.",
        context={"order_id": order.id, "status": new_status},
        idempotency_key=f"order:{order.id}:status:{new_status}",
    )
    return order


def get_order(order_id: int) -> Any:
    """Retrieve an order by ID.

    :param order_id: Primary key ID of the order.
    :return: Order model instance or None.
    """
    return Order.query.options(
        selectinload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.shipment),
    ).filter_by(id=order_id).first()


def get_user_orders(user_id: int) -> list[Any]:
    """Retrieve all orders placed by a specific user.

    :param user_id: User identifier.
    :return: List of Order model instances ordered by created_at desc.
    """
    return Order.query.options(selectinload(Order.items).joinedload(OrderItem.product)).filter_by(
        user_id=user_id
    ).order_by(Order.created_at.desc()).all()
