from dataclasses import dataclass

from app.models.core import Product


@dataclass
class ReorderRecommendation:
    product_id: str
    product_name: str
    sku: str | None
    current_quantity: float
    reorder_level: float
    target_quantity: float
    suggested_order_quantity: float
    unit_cost: float
    estimated_cost: float
    stock_status: str


def calculate_reorder_recommendation(
    product: Product,
    reorder_level: float,
    target_quantity: float,
) -> ReorderRecommendation:
    current_quantity = float(product.quantity or 0)
    unit_cost = float(product.cost or 0)

    if reorder_level < 0:
        raise ValueError('reorder_level must be >= 0')

    if target_quantity <= reorder_level:
        raise ValueError('target_quantity must be greater than reorder_level')

    suggested_order_quantity = max(target_quantity - current_quantity, 0.0)

    if current_quantity <= 0:
        stock_status = 'OUT_OF_STOCK'
    elif current_quantity <= reorder_level:
        stock_status = 'LOW_STOCK'
    else:
        stock_status = 'IN_STOCK'

    return ReorderRecommendation(
        product_id=product.id,
        product_name=product.name,
        sku=product.sku,
        current_quantity=current_quantity,
        reorder_level=reorder_level,
        target_quantity=target_quantity,
        suggested_order_quantity=suggested_order_quantity,
        unit_cost=unit_cost,
        estimated_cost=suggested_order_quantity * unit_cost,
        stock_status=stock_status,
    )
