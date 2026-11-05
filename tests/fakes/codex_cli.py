import json
import sys
import tomllib
from argparse import ArgumentParser, Namespace
from pathlib import Path

from cli_process import FakeCLI


class FakeCodexCLI(FakeCLI):
    def parser(self) -> ArgumentParser:
        parser = ArgumentParser(allow_abbrev=False)
        commands = parser.add_subparsers(required=True)
        execute = commands.add_parser("exec", allow_abbrev=False)
        execute.add_argument("--ignore-user-config", action="store_true")
        execute.add_argument("--ignore-rules", action="store_true")
        execute.add_argument("--ephemeral", action="store_true")
        execute.add_argument(
            "--sandbox",
            choices=["read-only", "workspace-write", "danger-full-access"],
            required=True,
        )
        execute.add_argument("--skip-git-repo-check", action="store_true")
        execute.add_argument("--cd", type=Path, required=True)
        execute.add_argument("--model", required=True)
        execute.add_argument("--json", action="store_true")
        execute.add_argument("--output-schema", type=Path, required=True)
        execute.add_argument("--output-last-message", type=Path, required=True)
        execute.add_argument("--disable", action="append", default=[])
        execute.add_argument("-c", "--config", action="append", default=[])
        execute.add_argument("prompt", choices=["-"])
        return parser

    def read_request(self, options: Namespace) -> dict[str, object]:
        settings = tomllib.loads("\n".join(options.config))
        return {
            "schema": json.loads(options.output_schema.read_text()),
            "instructions": Path(settings["model_instructions_file"]).read_text(),
        }

    def write_response(self, options: Namespace, response: dict) -> None:
        if response.get("answer") is not None:
            options.output_last_message.write_text(response["answer"])
        sys.stdout.write(response.get("stdout", ""))
