import re
import shutil
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness.filesystem import (
    FIND_FILES_KIND,
    READ_FILE_KIND,
    SEARCH_FILES_KIND,
    FileSystem,
    FindFilesCallPart,
    ReadFileCallPart,
    SearchFilesCallPart,
)

from codeguard.config import ConfigError, JudgeProvider

_FILE_TOOL_KINDS = (READ_FILE_KIND, SEARCH_FILES_KIND, FIND_FILES_KIND)
_MAX_READ_LINES = 2000
# A search or listing records every file it shows as one the verdict depends on, so a
# larger cap would make a verdict go stale on more files' changes, and cost more tokens.
_MAX_RESULTS = 200
_SEARCH_MATCH = re.compile(r"(?P<file>[^\[].*?):\d+:")
_NO_MATCHES = "No matches found."


def file_system_tools(root: Path) -> FileSystem[object]:
    return FileSystem[object](
        root_dir=root,
        read_only=True,
        content_hashes=False,
        tools=[kind.name for kind in _FILE_TOOL_KINDS],
        max_read_lines=_MAX_READ_LINES,
        max_search_results=_MAX_RESULTS,
        max_find_results=_MAX_RESULTS,
    )


def working_directory(root: Path) -> LocalWorkspaceBackend:
    """The model gets only read tools; the harness runs `rg` here so a search skips the
    files git ignores."""
    return LocalWorkspaceBackend(root)


def require_ripgrep(provider: JudgeProvider) -> None:
    """Without `rg` the harness searches with `grep -E`, which rejects regexes `rg` takes,
    so a search would differ by machine."""
    if shutil.which("rg") is None:
        raise ConfigError(
            f"The {provider} judge searches files with ripgrep: install it and put rg on PATH"
        )


def file_tool_calls(messages: Sequence[ModelMessage]) -> Iterator[ToolCallPart]:
    """The file tools' calls, in the order the model made them."""
    kinds = {kind.id for kind in _FILE_TOOL_KINDS}
    return (
        call
        for message in messages
        if isinstance(message, ModelResponse)
        for call in message.tool_calls
        if call.tool_kind in kinds
    )


def loaded_files(messages: Sequence[ModelMessage]) -> tuple[str, ...]:
    """The files the model read, and the files a search or listing showed it, each once.
    A call the tool sent back to retry loaded nothing."""
    answers = {
        part.tool_call_id: part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.outcome == "success"
    }
    return tuple(
        dict.fromkeys(
            file
            for call in file_tool_calls(messages)
            if call.tool_call_id in answers
            for file in _files_shown(call, answers[call.tool_call_id])
        )
    )


def _files_shown(call: ToolCallPart, answer: ToolReturnPart) -> Iterable[str]:
    lines = answer.model_response_str().splitlines()
    match call:
        case ReadFileCallPart(typed_args={"path": path}):
            return (path,)
        case SearchFilesCallPart():
            return (match["file"] for line in lines if (match := _SEARCH_MATCH.match(line)))
        case FindFilesCallPart():
            return (line for line in lines if _names_a_file(line))
        case _:
            return ()


def _names_a_file(found: str) -> bool:
    return not found.startswith("[") and not found.endswith("/") and found != _NO_MATCHES
