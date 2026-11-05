import json
import os
import sys
import time
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path


class FakeCLI(ABC):
    @abstractmethod
    def parser(self) -> ArgumentParser: ...

    @abstractmethod
    def read_request(self, options: Namespace) -> dict[str, object]: ...

    @abstractmethod
    def write_response(self, options: Namespace, response: dict) -> None: ...

    def run(self) -> None:
        arguments = sys.argv[1:]
        options = self.parser().parse_args(arguments)
        response = json.loads(Path(os.environ["CODEGUARD_TEST_CLI_CONFIG"]).read_text())
        request = {
            "arguments": arguments,
            "prompt": sys.stdin.read(),
            "cwd": os.getcwd(),
            "environment": {
                key: os.environ[key]
                for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "PATH")
                if key in os.environ
            },
            **self.read_request(options),
        }
        record = response.get("record")
        if record_env := response.get("record_env"):
            directory = Path(os.environ[record_env])
            directory.mkdir(parents=True, exist_ok=True)
            record = directory / "request.json"
        if record:
            Path(record).write_text(json.dumps(request))
        if calls := response.get("calls"):
            with Path(calls).open("a") as stream:
                stream.write("called\n")
        time.sleep(response.get("delay", 0))
        self.write_response(options, response)
        sys.stderr.write(response.get("stderr", ""))
        sys.exit(response.get("exit_code", 0))
