import json
import os
from pathlib import Path

FAKE_CLAUDE = Path(__file__).parent / "fakes" / "claude"
FAKE_CODEX = Path(__file__).parent / "fakes" / "codex"


def configure_fake_cli_response(response: dict[str, object]) -> None:
    Path(os.environ["CODEGUARD_TEST_CLI_CONFIG"]).write_text(json.dumps(response))
