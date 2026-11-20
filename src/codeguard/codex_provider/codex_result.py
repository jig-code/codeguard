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

    @property
    def telemetry(self) -> dict[str, object]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_input_tokens": self.cached_input_tokens,
            "thinking_tokens": self.reasoning_output_tokens,
        }


class _TurnCompleted(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["turn.completed"]
    usage: _Usage = _Usage()


class _CommandExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["command_execution"]
    command: str


class _UnreadItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str


def _item_kind(item: dict[str, object]) -> str:
    return "command_execution" if item.get("type") == "command_execution" else "unread"


class _ItemCompleted(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["item.completed"]
    item: Annotated[
        Annotated[_CommandExecution, Tag("command_execution")]
        | Annotated[_UnreadItem, Tag("unread")],
        Discriminator(_item_kind),
    ]


class _UnreadEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str


_EVENT_KINDS = ("turn.completed", "item.completed")


def _event_kind(event: dict[str, object]) -> str:
    kind = event.get("type")
    return str(kind) if kind in _EVENT_KINDS else "unread"


_STREAM_EVENT: TypeAdapter[_TurnCompleted | _ItemCompleted | _UnreadEvent] = TypeAdapter(
    Annotated[
        Annotated[_TurnCompleted, Tag("turn.completed")]
        | Annotated[_ItemCompleted, Tag("item.completed")]
        | Annotated[_UnreadEvent, Tag("unread")],
        Discriminator(_event_kind),
    ]
)


class CodexResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    usage: _Usage | None = None
    tool_calls: tuple[dict[str, JsonValue], ...] = ()

    @classmethod
    def from_stream(cls, stream: str) -> Self:
        events = [event for line in stream.splitlines() if (event := _event_on(line))]
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
        usage = self.usage.telemetry if self.usage else {}
        return {**usage, "tool_calls": self.tool_calls}


def _event_on(line: str) -> _TurnCompleted | _ItemCompleted | _UnreadEvent | None:
    try:
        return _STREAM_EVENT.validate_json(line)
    except ValidationError:
        return None
