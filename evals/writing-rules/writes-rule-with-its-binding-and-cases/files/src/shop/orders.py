from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price: Decimal


def order_total(lines: list[OrderLine]) -> Decimal:
    return sum((line.unit_price * line.quantity for line in lines), Decimal(0))
