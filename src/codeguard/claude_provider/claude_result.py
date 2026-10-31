from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    JsonValue,
    Tag,
    TypeAdapter,
    field_validator,
)

from codeguard.review import JudgeNoVerdict, Verdict


class ModelUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(alias="inputTokens")
    output_tokens: int = Field(alias="outputTokens")
    cache_read_input_tokens: int = Field(alias="cacheReadInputTokens")
    cache_creation_input_tokens: int = Field(alias="cacheCreationInputTokens")
    thinking_tokens: int = Field(alias="thinkingTokens")
    cost_usd: float = Field(alias="costUSD")


class UsageWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    utilization: float


class _SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    filenames: tuple[str, ...] = ()
    content: str | None = None


class _ReadInput(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    file_path: str


class _SearchInput(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    path: str | None = None


class _ToolUse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["tool_use"]
    id: str

    def loaded_files(self, root: Path, result: JsonValue) -> list[str]:
        return []

    @property
    def call(self) -> dict[str, JsonValue]:
        """The tool's name and the arguments it was called with."""
        raise NotImplementedError


class _OtherToolUse(_ToolUse):
    """A call to a tool that loads no files the judge reports."""

    name: str
    input: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def call(self) -> dict[str, JsonValue]:
        return {"tool": self.name, **self.input}


class _ReadUse(_ToolUse):
    name: Literal["Read"]
    input: _ReadInput

    def loaded_files(self, root: Path, result: JsonValue) -> list[str]:
        return [_relative(root, self.input.file_path)]

    @property
    def call(self) -> dict[str, JsonValue]:
        return {"tool": self.name, **self.input.model_dump(exclude_none=True)}


class _SearchUse(_ToolUse):
    name: Literal["Grep", "Glob"]
    input: _SearchInput

    def loaded_files(self, root: Path, result: JsonValue) -> list[str]:
        """The file searched and the files the search showed; its result is parsed here,
        once the call it answers says it is a search result."""
        if result is None:
            return []
        search = _SearchResult.model_validate(result)
        searched = self.input.path
        files = [
            *([searched] if searched is not None and (root / searched).is_file() else []),
            *search.filenames,
            *_files_in_lines(root, search.content),
        ]
        return [_relative(root, file) for file in files]

    @property
    def call(self) -> dict[str, JsonValue]:
        return {"tool": self.name, **self.input.model_dump(exclude_none=True)}


class _ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["tool_result"]
    tool_use_id: str
    is_error: bool = False


class _OtherPart(BaseModel):
    """Text, thinking and any other content the judge doesn't read."""

    model_config = ConfigDict(frozen=True)

    type: str


_VERDICT_TOOL = "StructuredOutput"
_TOOL_KINDS = {"Read": "read", "Grep": "search", "Glob": "search"}


def _part_kind(part: dict[str, object]) -> str:
    match part.get("type"):
        case "tool_use":
            return _TOOL_KINDS.get(str(part.get("name")), "tool_use")
        case "tool_result":
            return "tool_result"
        case _:
            return "other"


_ContentPart = Annotated[
    Annotated[_ReadUse, Tag("read")]
    | Annotated[_SearchUse, Tag("search")]
    | Annotated[_OtherToolUse, Tag("tool_use")]
    | Annotated[_ToolResult, Tag("tool_result")]
    | Annotated[_OtherPart, Tag("other")],
    Discriminator(_part_kind),
]


class _MessageBody(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: tuple[_ContentPart, ...]

    @field_validator("content", mode="before")
    @classmethod
    def _text_is_one_part(cls, content: object) -> object:
        return [{"type": "text", "text": content}] if isinstance(content, str) else content


class _AssistantMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["assistant"]
    message: _MessageBody


class _UserMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["user"]
    message: _MessageBody
    tool_use_result: JsonValue = None


class _RateLimitInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    unified_windows: dict[str, UsageWindow] = Field(default_factory=dict, alias="unifiedWindows")


class _RateLimitEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["rate_limit_event"]
    rate_limit_info: _RateLimitInfo


class _OtherMessage(BaseModel):
    """System, stream and any other message the judge doesn't read."""

    model_config = ConfigDict(frozen=True)

    type: str


class ClaudeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["result"]
    is_error: bool
    subtype: str
    num_turns: int
    duration_ms: int
    duration_api_ms: int
    total_cost_usd: float
    model_usage: dict[str, ModelUsage] = Field(alias="modelUsage")
    usage_windows: dict[str, UsageWindow] = {}
    structured_output: Verdict | None = None
    loaded_files: tuple[str, ...] = ()
    tool_calls: tuple[dict[str, JsonValue], ...] = ()

    @classmethod
    def from_stream(cls, stream: str, root: Path) -> Self:
        messages = [
            _STREAM_MESSAGE.validate_json(line) for line in stream.splitlines() if line.strip()
        ]
        results = [message for message in messages if isinstance(message, cls)]
        if not results:
            raise JudgeNoVerdict(f"claude printed no result:\n{stream}")
        windows = [
            message.rate_limit_info.unified_windows
            for message in messages
            if isinstance(message, _RateLimitEvent)
        ]
        tool_results = {
            part.tool_use_id: message.tool_use_result
            for message in messages
            if isinstance(message, _UserMessage)
            for part in message.message.content
            if isinstance(part, _ToolResult) and not part.is_error
        }
        tool_uses = [
            part
            for message in messages
            if isinstance(message, _AssistantMessage)
            for part in message.message.content
            if isinstance(part, _ToolUse)
        ]
        loaded_files = (
            file for use in tool_uses for file in use.loaded_files(root, tool_results.get(use.id))
        )
        return results[-1].model_copy(
            update={
                "usage_windows": windows[-1] if windows else {},
                "loaded_files": tuple(dict.fromkeys(loaded_files)),
                # The verdict comes as a call to this tool; it reads nothing.
                "tool_calls": tuple(
                    use.call for use in tool_uses if use.call["tool"] != _VERDICT_TOOL
                ),
            }
        )

    @property
    def telemetry(self) -> dict[str, object]:
        usages = self.model_usage.values()
        return {
            "is_error": self.is_error,
            "subtype": self.subtype,
            "num_turns": self.num_turns,
            "duration_ms": self.duration_ms,
            "duration_api_ms": self.duration_api_ms,
            "cost_usd": self.total_cost_usd,
            "input_tokens": sum(usage.input_tokens for usage in usages),
            "output_tokens": sum(usage.output_tokens for usage in usages),
            "cache_read_input_tokens": sum(usage.cache_read_input_tokens for usage in usages),
            "cache_creation_input_tokens": sum(
                usage.cache_creation_input_tokens for usage in usages
            ),
            "thinking_tokens": sum(usage.thinking_tokens for usage in usages),
            "model_usage": {model: usage.model_dump() for model, usage in self.model_usage.items()},
            "tool_calls": self.tool_calls,
            **{
                f"{window}_utilization": usage.utilization
                for window, usage in self.usage_windows.items()
            },
        }


_MESSAGE_KINDS = ("assistant", "user", "rate_limit_event", "result")


def _message_kind(message: dict[str, object]) -> str:
    kind = message.get("type")
    return str(kind) if kind in _MESSAGE_KINDS else "other"


_STREAM_MESSAGE: TypeAdapter[
    _AssistantMessage | _UserMessage | _RateLimitEvent | ClaudeResult | _OtherMessage
] = TypeAdapter(
    Annotated[
        Annotated[_AssistantMessage, Tag("assistant")]
        | Annotated[_UserMessage, Tag("user")]
        | Annotated[_RateLimitEvent, Tag("rate_limit_event")]
        | Annotated[ClaudeResult, Tag("result")]
        | Annotated[_OtherMessage, Tag("other")],
        Discriminator(_message_kind),
    ]
)


def _files_in_lines(root: Path, content: str | None) -> Iterator[str]:
    if content is None:
        return
    for line in content.splitlines():
        prefixes = (line[:end] for end, char in enumerate(line) if char in ":-")
        file = next((prefix for prefix in prefixes if (root / prefix).is_file()), None)
        if file is not None:
            yield file


def _relative(root: Path, path: str) -> str:
    resolved = (root / path).resolve()
    if resolved.is_relative_to(root.resolve()):
        return str(resolved.relative_to(root.resolve()))
    return path
