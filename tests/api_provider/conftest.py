import pytest

from codeguard.api_provider import retrying_model


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    waited: list[float] = []

    async def wait(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(retrying_model.asyncio, "sleep", wait)
    return waited
