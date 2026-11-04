import json
import os
from pathlib import Path

FAKE_CLI = Path(__file__).parent / "fakes" / "claude"


def configure_fake_cli_response(response: dict[str, object]) -> str:
    Path(os.environ["CODEGUARD_TEST_CLI_CONFIG"]).write_text(json.dumps(response))
    return str(FAKE_CLI)
