from datetime import datetime

DEFAULT_SOURCE = "web"


def record(event: str, stamp: datetime = datetime.now(), source: str = DEFAULT_SOURCE) -> dict:
    return {"event": event, "at": stamp.isoformat(), "source": source}


def tags_for(event: str, extra: frozenset[str] = frozenset()) -> frozenset[str]:
    return frozenset({event}) | extra
