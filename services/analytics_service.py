"""Analytics service providing reporting aggregations, heap-based top sellers, and shipment metrics."""
from datetime import date, datetime, timedelta, timezone
from typing import Any
from sqlalchemy import func
from extensions import db
from models import Order, OrderItem, Product, Shipment


def best_sellers(k: int = 10) -> list[dict[str, Any]]:
    """Determine the top k best-selling products using a min-heap.

    :param k: Number of top items to retrieve.
    :return: List of dicts containing product_id, product_name, and total_sold count.
    """
    if not isinstance(k, int) or k <= 0:
        return []
    rows = db.session.query(
        Product.id.label("product_id"), Product.name.label("product_name"),
        func.sum(OrderItem.quantity).label("total_sold"),
    ).join(OrderItem, OrderItem.product_id == Product.id).join(
        Order, Order.id == OrderItem.order_id
    ).filter(Order.status.in_(["paid", "processing", "shipped", "delivered"])).group_by(
        Product.id, Product.name
    ).order_by(func.sum(OrderItem.quantity).desc(), Product.name.asc()).limit(k).all()
    return [dict(product_id=row.product_id, product_name=row.product_name,
                 total_sold=int(row.total_sold)) for row in rows]


def sales_by_day(days: int = 30) -> list[dict[str, Any]]:
    """Compute aggregated sales revenue and volume broken down per calendar day.

    :param days: Number of recent days to include in report.
    :return: List of daily dict records with date, total_orders, and total_revenue.
    """
    if not isinstance(days, int) or days <= 0:
        return []
    days = min(days, 366)
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)
    rows = db.session.query(
        func.date(Order.created_at).label("sales_date"),
        func.count(Order.id).label("total_orders"),
        func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
    ).filter(
        Order.status == "delivered",
        Order.created_at >= datetime.combine(start_day, datetime.min.time(), timezone.utc),
    ).group_by(func.date(Order.created_at)).all()
    aggregates = {str(row.sales_date): row for row in rows}
    results = []
    for offset in range(days):
        current_day = start_day + timedelta(days=offset)
        row = aggregates.get(current_day.isoformat())
        results.append({
            "date": current_day,
            "total_orders": int(row.total_orders) if row else 0,
            "total_revenue": row.total_revenue if row else 0,
        })
    return results


def shipments_by_status() -> dict[str, int]:
    """Calculate counts of shipments grouped by current delivery status.

    :return: Dictionary mapping delivery status strings to counts.
    """
    rows = db.session.query(Shipment.status, func.count(Shipment.id)).group_by(Shipment.status).all()
    return {status: int(count) for status, count in rows}


def orders_by_status() -> dict[str, int]:
    """Calculate counts of orders grouped by current lifecycle status.

    :return: Dictionary mapping order status strings to counts.
    """
    rows = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    return {status: int(count) for status, count in rows}
