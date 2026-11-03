"""The judge's read-only file tools over Codex's stdio MCP transport."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import JsonValue

from codeguard.review.file_tools import FileTools


@dataclass(frozen=True)
class FileServer:
    files: FileTools
    journal: Path

    def result(self, method: str, params: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if method == "initialize":
            return {
                "protocolVersion": str(params.get("protocolVersion", "2024-11-05")),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "codeguard-files", "version": "1"},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.function_schema.json_schema,
                        "annotations": {"readOnlyHint": True},
                    }
                    for tool in self.files.tools
                ]
            }
        if method == "tools/call":
            tool = next(tool for tool in self.files.tools if tool.name == params["name"])
            arguments = tool.function_schema.validator.validate_python(params.get("arguments", {}))
            text = tool.function_schema.function(**arguments)
            with self.journal.open("a") as journal:
                journal.write(json.dumps(self.files.loaded_files) + "\n")
            return {"content": [{"type": "text", "text": text}]}
        raise ValueError(f"Unsupported MCP method: {method}")

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            if "id" not in request:
                continue
            try:
                result = self.result(request["method"], request.get("params", {}))
                response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
            except (ValueError, KeyError, StopIteration) as error:
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -32602, "message": str(error)},
                }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    FileServer(FileTools(Path(sys.argv[1])), Path(sys.argv[2])).serve()
