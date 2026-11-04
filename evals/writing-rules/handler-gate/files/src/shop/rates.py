import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
FALLBACK_RATES = {"USD": 1.0}


def load_rates(path: Path) -> dict[str, float]:
    try:
        return json.loads(path.read_text())
    except OSError:
        return FALLBACK_RATES


def parse_rate(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        # A blank or malformed cell means "no rate"; the caller skips it.
        logger.info("skipping unparseable rate %r", text)
        return None
