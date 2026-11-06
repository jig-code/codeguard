# Pydantic-AI Testing Guidelines

These guidelines apply when writing or reviewing tests for pydantic-ai agents.

## Use TestModel for Agent Testing

When testing pydantic-ai agents, use `TestModel` with the agent's `.override()` method to control agent output without making real LLM calls.

**Always configure `TestModel` with realistic output data.** `TestModel()` with no arguments returns default/zero values for every field (e.g., `None` for nullable fields, `""` for strings). This makes tests meaningless — you can't tell whether the code actually processed the LLM result or just passed through a default. Use `custom_output_args` with realistic, domain-appropriate values so tests demonstrate that LLM output flows through the system correctly.

```python
from pydantic_ai.models.test import TestModel

# BAD - TestModel with no args returns None/defaults for every field
# Assertions like `assert "profile.dob" in result` pass but prove nothing
test_model = TestModel()

# GOOD - Realistic output demonstrates values flowing through the system
test_model = TestModel(custom_output_args={"dob": "1990-01-01"})

with my_agent.override(model=test_model):
    result = service.call_agent(...)
```

## Use SequentialTestModel When Calls Need Distinct Responses

`TestModel` returns the same `custom_output_args` on every call. When a test invokes an agent multiple times and each call should produce different output, use `SequentialTestModel`. It returns the next scripted response per call and raises if called more times than scripted, so the call count is asserted for free.

```python
from testing.agent_models import SequentialTestModel

model = SequentialTestModel(
    [
        {"items": [{"activity_id": "bathing", "notes": "needs assistance"}]},
        {"items": [{"activity_id": "non-smoker", "notes": "prefers non-smoking"}]},
    ]
)

result = classify_evidence(fields, "evidence", model=model)
assert model.call_count == 2
```

**When to use which:**
- `TestModel(custom_output_args=...)` — single agent call with one output type.
- `SequentialTestModel([...])` — multiple agent calls needing distinct per-call responses, or capturing the prompt sent to the agent via `.captured_messages`. Responses are returned in order; a call past the end of the list raises.
- `FunctionModel` — when the per-call response must be chosen by the call's output schema rather than call order (e.g. a multi-batch update where each batch carries a different field).

## Simulate Agent Errors with `__raise__`

To test error handling when an agent fails, use `TestModel` with `{"__raise__": "error message"}`:

```python
# PREFERRED - Use TestModel's __raise__ pattern
error_model = TestModel(custom_output_args={"__raise__": "LLM call failed"})

with my_agent.override(model=error_model):
    result = service.call_agent(...)

# AVOID - Don't monkeypatch internal methods to simulate agent errors
monkeypatch.setattr(SomeInternalClass, "some_method", lambda: raise Exception())
```

This tests error handling at the correct boundary (the LLM call) rather than mocking internal implementation details.

## Testing Dynamic Instructions (`@agent.instructions`)

Never construct a fake `RunContext` (via `MagicMock`, `SimpleNamespace`, or similar) to call instruction functions directly. Instead, run the agent with `SequentialTestModel` and use `extract_instructions_text()` to verify the injected content appears in the prompt.

```python
from testing.agent_models import (
    SequentialTestModel,
    extract_instructions_text,
)
from myapp.agent import my_agent, MyDeps

def test_dynamic_instructions_include_context():
    deps = MyDeps(active_item="bathing")
    model = SequentialTestModel([valid_response])

    my_agent.run_sync(user_prompt="hello", deps=deps, model=model)

    instructions = extract_instructions_text(model.captured_messages)
    assert "bathing" in instructions
```

This exercises the real pydantic-ai plumbing and catches issues (wrong deps type, decorator misconfiguration) that a synthetic `RunContext` would miss.

## When to Use Agent.override() vs Model Parameter

Use `Agent.override()` when:
- Testing LangGraph workflows via `GraphRunner` (agents are invoked internally)
- Testing the raw `Agent` instance directly (without `AgentRunner`)

Use the `model` parameter when:
- Testing via `AgentRunner.run_sync()` or `AgentRunner.run()`

```python
# Testing an agent directly via AgentRunner - pass model parameter
result = care_plan.run_sync(user_prompt=message, deps=deps, model=test_model)

# Testing via GraphRunner - use override (no way to pass model through workflow)
with care_plan_agent.override(model=test_model):
    result = runner.run("message")
```
