import sys
from pathlib import Path


def fake_codex_script(record: Path, answer: str | None, before: str = "") -> str:
    return f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path

arguments = sys.argv[1:]
settings = {{}}
for index, argument in enumerate(arguments):
    if argument == "-c":
        key, value = arguments[index + 1].split("=", 1)
        settings[key] = json.loads(value)
schema = Path(arguments[arguments.index("--output-schema") + 1])
instructions = Path(settings["model_instructions_file"])
Path({str(record)!r}).write_text(json.dumps({{
    "arguments": arguments,
    "prompt": sys.stdin.read(),
    "instructions": instructions.read_text(),
    "schema": json.loads(schema.read_text()),
    "cwd": os.getcwd(),
    "environment": {{key: os.environ[key] for key in
        ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "PATH") if key in os.environ}},
}}))
{before}
answer = {answer!r}
if answer is not None:
    Path(arguments[arguments.index("--output-last-message") + 1]).write_text(answer)
print(json.dumps({{"type": "turn.completed", "usage": {{"input_tokens": 10, "output_tokens": 5}}}}))
"""
