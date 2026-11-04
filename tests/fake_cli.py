import json
import os
import shutil
import sys
import time
from pathlib import Path


def install_fake_cli(executable: Path, response: dict[str, object]) -> str:
    shutil.copyfile(Path(__file__).with_suffix(".sh"), executable)
    shutil.copyfile(__file__, executable.parent / ".fake-cli")
    interpreter = executable.parent / ".fake-python"
    if not interpreter.exists():
        interpreter.symlink_to(sys.executable)
    executable.chmod(0o755)
    Path(f"{executable}.json").write_text(json.dumps(response))
    return str(executable)


def main() -> None:
    executable, *arguments = sys.argv[1:]
    response = json.loads(Path(f"{executable}.json").read_text())
    request = {
        "arguments": arguments,
        "prompt": sys.stdin.read(),
        "cwd": os.getcwd(),
        "environment": {
            key: os.environ[key]
            for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "PATH")
            if key in os.environ
        },
    }
    if "--output-schema" in arguments:
        schema = Path(arguments[arguments.index("--output-schema") + 1])
        request["schema"] = json.loads(schema.read_text())
        settings = dict(
            arguments[index + 1].split("=", 1)
            for index, argument in enumerate(arguments)
            if argument == "-c"
        )
        request["instructions"] = Path(json.loads(settings["model_instructions_file"])).read_text()
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
    if response.get("answer") is not None:
        Path(arguments[arguments.index("--output-last-message") + 1]).write_text(response["answer"])
    sys.stdout.write(response.get("stdout", ""))
    sys.stderr.write(response.get("stderr", ""))
    sys.exit(response.get("exit_code", 0))


if __name__ == "__main__":
    main()
