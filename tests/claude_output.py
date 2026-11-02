import json

MODEL_USAGE = {
    "inputTokens": 4,
    "outputTokens": 134,
    "cacheReadInputTokens": 8553,
    "cacheCreationInputTokens": 588,
    "thinkingTokens": 20,
    "costUSD": 0.0022,
}
RATE_LIMIT_EVENT = {
    "type": "rate_limit_event",
    "rate_limit_info": {
        "status": "allowed",
        "unifiedWindows": {
            "five_hour": {"utilization": 0.16, "resetsAt": 1792207200},
            "seven_day": {"utilization": 0.11, "resetsAt": 1792591200},
        },
    },
}


def claude_result(violations: list[dict]) -> dict:
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 3,
        "duration_ms": 2036,
        "duration_api_ms": 1901,
        "total_cost_usd": 0.0022,
        "modelUsage": {"claude-sonnet-5-5": MODEL_USAGE},
        "structured_output": {"reason": "Judged.", "violations": violations},
    }


def tool_use(name: str, use_id: str = "toolu_1", **arguments: object) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "id": use_id, "name": name, "input": arguments}]
        },
    }


def tool_result(use_id: str, **result: object) -> dict:
    return {
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": use_id, "content": ""}]},
        "tool_use_result": result,
    }


AGREEMENT = {"agrees": True, "why": "Both rest on the same code."}


def claude_agreement(agreement: dict) -> dict:
    return {**claude_result([]), "structured_output": agreement}


def fake_claude_script(
    violations: list[dict],
    before: str = "",
    messages: tuple[dict, ...] = (),
    agreement: dict = AGREEMENT,
) -> str:
    """A claude that answers a judge call with the verdict, and a grading call (asked for the
    agreement schema) with the agreement, without running `before`."""
    stream = "\n".join(
        json.dumps(message) for message in (RATE_LIMIT_EVENT, *messages, claude_result(violations))
    )
    graded = json.dumps(claude_agreement(agreement))
    return (
        "#!/bin/sh\n"
        "case \"$*\" in *agrees*) cat > /dev/null; cat <<'EOF'\n"
        f"{graded}\nEOF\nexit 0;; esac\n"
        f"{before}cat > /dev/null\ncat <<'EOF'\n{stream}\nEOF\n"
    )
