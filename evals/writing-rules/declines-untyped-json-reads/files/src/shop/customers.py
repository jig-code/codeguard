import json
from pathlib import Path

from django.contrib.auth.models import User


def find_or_create_customer(email: str) -> tuple[User, bool]:
    user, created = User.objects.get_or_create(email=email)
    return user, created


def load_settings(path: Path) -> dict:
    settings = json.loads(path.read_text())
    return settings


def legacy_export(customers):
    for customer in customers:
        print(customer.email)
