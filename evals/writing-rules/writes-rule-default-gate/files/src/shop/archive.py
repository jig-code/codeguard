from pathlib import Path


def export_orders(orders: list[dict], path: Path, *, overwrite: bool = True) -> None:
    with path.open("w" if overwrite else "x") as file:
        for order in orders:
            file.write(f"{order['id']},{order['total']}\n")


def page_of(orders: list[dict], size: int = 50) -> list[dict]:
    return orders[:size]
