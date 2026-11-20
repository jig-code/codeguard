from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    JsonValue,
    Tag,
    TypeAdapter,
    ValidationError,
)


class _Usage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0


class _TurnCompleted(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["turn.completed"]
    usage: _Usage = _Usage()


class _CommandExecution(BaseModel):
    """A shell command Codex ran: its native tools read the repository through commands."""

    model_config = ConfigDict(frozen=True)

    type: Literal["command_execution"]
    command: str


class _OtherItem(BaseModel):
    """A message, reasoning or any other item the judge doesn't read."""

    model_config = ConfigDict(frozen=True)

    type: str


def _item_kind(item: dict[str, object]) -> str:
    return "command_execution" if item.get("type") == "command_execution" else "other"


class _ItemCompleted(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["item.completed"]
    item: Annotated[
        Annotated[_CommandExecution, Tag("command_execution")]
        | Annotated[_OtherItem, Tag("other")],
        Discriminator(_item_kind),
    ]


class _OtherEvent(BaseModel):
    """A thread, turn start or any other event the judge doesn't read."""

    model_config = ConfigDict(frozen=True)

    type: str


_EVENT_KINDS = ("turn.completed", "item.completed")


def _event_kind(event: dict[str, object]) -> str:
    kind = event.get("type")
    return str(kind) if kind in _EVENT_KINDS else "other"


_STREAM_EVENT: TypeAdapter[_TurnCompleted | _ItemCompleted | _OtherEvent] = TypeAdapter(
    Annotated[
        Annotated[_TurnCompleted, Tag("turn.completed")]
        | Annotated[_ItemCompleted, Tag("item.completed")]
        | Annotated[_OtherEvent, Tag("other")],
        Discriminator(_event_kind),
    ]
)


class CodexResult(BaseModel):
    """What `codex exec --json` printed about its turn. Codex prints no count of the
    requests it made."""

    model_config = ConfigDict(frozen=True)

    usage: _Usage | None = None
    tool_calls: tuple[dict[str, JsonValue], ...] = ()

    @classmethod
    def from_stream(cls, stream: str) -> Self:
        events = [event for line in stream.splitlines() if (event := _parsed(line))]
        turns = [event for event in events if isinstance(event, _TurnCompleted)]
        return cls(
            usage=turns[-1].usage if turns else None,
            tool_calls=tuple(
                {"tool": event.item.type, "command": event.item.command}
                for event in events
                if isinstance(event, _ItemCompleted) and isinstance(event.item, _CommandExecution)
            ),
        )

    @property
    def telemetry(self) -> dict[str, object]:
        """The usage and tool calls, under the keys every judge records them with."""
        usage = self.usage
        return {
            **(
                {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cache_read_input_tokens": usage.cached_input_tokens,
                    "thinking_tokens": usage.reasoning_output_tokens,
                }
                if usage
                else {}
            ),
            "tool_calls": self.tool_calls,
        }


def _parsed(line: str) -> _TurnCompleted | _ItemCompleted | _OtherEvent | None:
    """The event on one line, or None for a line that holds none, such as a log line."""
    try:
        return _STREAM_EVENT.validate_json(line)
    except ValidationError:
        return None
