from decimal import Decimal


def charge(email: str, amount: Decimal) -> None:
    print(f"charging {email} {amount}")
