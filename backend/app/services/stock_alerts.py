from app.models.core import Product, Notification
from app.services.purchasing import calculate_reorder_recommendation
from app.services.notifications import create_notification
from sqlalchemy.orm import Session


def get_stock_alert(product: Product):
    if float(product.reorder_level or 0) <= 0 or float(product.target_quantity or 0) <= 0:
        return None

    recommendation = calculate_reorder_recommendation(
        product=product,
        reorder_level=float(product.reorder_level),
        target_quantity=float(product.target_quantity),
    )

    if recommendation.stock_status not in ('LOW_STOCK', 'OUT_OF_STOCK'):
        return None

    return recommendation


def sync_stock_notification(
    db: Session,
    product: Product,
    user_id: str | None = None,
):
    recommendation = get_stock_alert(product)
    if recommendation is None:
        return None

    notification_type = 'STOCK_OUT' if recommendation.stock_status == 'OUT_OF_STOCK' else 'STOCK_LOW'
    severity = 'CRITICAL' if recommendation.stock_status == 'OUT_OF_STOCK' else 'WARNING'

    existing = (
        db.query(Notification)
        .filter(
            Notification.business_id == product.business_id,
            Notification.notification_type == notification_type,
            Notification.entity_type == 'product',
            Notification.entity_id == product.id,
            Notification.is_read == False,
        )
        .first()
    )

    if existing is not None:
        return existing

    if recommendation.stock_status == 'OUT_OF_STOCK':
        title = 'Product out of stock'
        message = f'{product.name} is out of stock. Suggested order quantity: {recommendation.suggested_order_quantity:g}.'
    else:
        title = 'Product low in stock'
        message = f'{product.name} is low in stock ({recommendation.current_quantity:g} remaining). Suggested order quantity: {recommendation.suggested_order_quantity:g}.'

    return create_notification(
        db=db,
        business_id=product.business_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity,
        entity_type='product',
        entity_id=product.id,
    )
