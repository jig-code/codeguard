import json
import sys
from argparse import ArgumentParser, Namespace

from cli_process import FakeCLI


class FakeClaudeCLI(FakeCLI):
    def parser(self) -> ArgumentParser:
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--safe-mode", action="store_true")
        parser.add_argument("-p", action="store_true")
        parser.add_argument("--model", required=True)
        parser.add_argument("--output-format", choices=["stream-json"], required=True)
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--json-schema", type=json.loads, required=True)
        parser.add_argument("--tools", required=True)
        parser.add_argument("--permission-prompts", choices=["none"], required=True)
        parser.add_argument("--system-prompt", required=True)
        parser.add_argument("--no-session-persistence", action="store_true")
        return parser

    def read_request(self, options: Namespace) -> dict[str, object]:
        return {"schema": options.json_schema, "instructions": options.system_prompt}

    def write_response(self, options: Namespace, response: dict) -> None:
        sys.stdout.write(response.get("stdout", ""))
