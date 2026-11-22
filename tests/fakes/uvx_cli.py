import sys
from argparse import REMAINDER, ArgumentParser, Namespace

from cli_process import FakeCLI


class FakeUvx(FakeCLI):
    def parser(self) -> ArgumentParser:
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--quiet", action="store_true")
        parser.add_argument("--from", dest="source", required=True)
        parser.add_argument("command", choices=["codeguard"])
        parser.add_argument("arguments", nargs=REMAINDER)
        return parser

    def read_request(self, options: Namespace) -> dict[str, object]:
        return {}

    def write_response(self, options: Namespace, response: dict) -> None:
        sys.stdout.write(response.get("stdout", ""))
