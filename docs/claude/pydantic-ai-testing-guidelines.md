# Pydantic-AI Testing Guidelines

These guidelines apply when writing or reviewing tests for pydantic-ai agents.

## Use TestModel for Agent Testing

When testing pydantic-ai agents, hand a `TestModel` to the code through the seam it takes its model by (or the agent's `.override()` method where there is none) to control agent output without making real LLM calls.

**Always configure `TestModel` with realistic output data.** `TestModel()` with no arguments returns default/zero values for every field (e.g., `None` for nullable fields, `""` for strings). This makes tests meaningless — you can't tell whether the code actually processed the LLM result or just passed through a default. Use `custom_output_args` with realistic, domain-appropriate values so tests demonstrate that LLM output flows through the system correctly.

```python
from pydantic_ai.models.test import TestModel

# BAD - TestModel with no args returns None/defaults for every field
# Assertions like `assert result.verdict.violations == ()` pass but prove nothing
test_model = TestModel()

# GOOD - Realistic output demonstrates values flowing through the system
test_model = TestModel(
    custom_output_args={"reason": "print bypasses logging.", "violations": [VIOLATION]}
)

with my_agent.override(model=test_model):
    result = service.call_agent(...)
```

## Script a FunctionModel When Calls Need Distinct Responses

`TestModel` returns the same `custom_output_args` on every call. When a test invokes an agent multiple times and each call should produce different output, script the answers with a `FunctionModel` whose function pops the next answer per call. `ScriptedGemini` in `tests/gemini_provider/test_gemini_judge.py` does this: popping from an empty list raises if the model is called more times than scripted, and asserting the list is empty afterwards proves every answer was used.

```python
models = ScriptedGemini([calls(("read_file", {"path": "a.py"})), verdict(VIOLATION)])

judgement = judge_with(tmp_path, models).judge(make_judge_request())

assert judgement.verdict.violations == (Violation.model_validate(VIOLATION),)
assert models.answers == []
```

**When to use which:**
- `TestModel(custom_output_args=...)` — single agent call with one output type.
- A scripted `FunctionModel` (`ScriptedGemini([...])`) — multiple agent calls needing distinct per-call responses, or capturing the prompt sent to the agent via its recorded `requests`. Answers are returned in order; a call past the end of the list raises.
- A `FunctionModel` that chooses by request — when the per-call response must be chosen by the call's output schema or content rather than call order.

## Simulate Agent Errors from the Model

To test error handling when an agent fails, have the scripted model raise the error the provider would, such as pydantic-ai's `ModelHTTPError`:

```python
# PREFERRED - The scripted model raises at the LLM call
models = ScriptedGemini([http_error(400, "Bad request.")])

with pytest.raises(JudgeProcessError):
    judge_with(tmp_path, models).judge(make_judge_request())

# AVOID - Don't monkeypatch internal methods to simulate agent errors
monkeypatch.setattr(SomeInternalClass, "some_method", lambda: raise Exception())
```

This tests error handling at the correct boundary (the LLM call) rather than mocking internal implementation details.

## Testing Dynamic Instructions (`@agent.instructions`)

Never construct a fake `RunContext` (via `MagicMock`, `SimpleNamespace`, or similar) to call instruction functions directly. Instead, run the agent with a `TestModel` inside `capture_run_messages()` and read the `instructions` of the `ModelRequest` it sent to verify the injected content appears in the prompt.

```python
from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ModelRequest
from pydantic_ai.models.test import TestModel
from myapp.agent import my_agent, MyDeps


def test_dynamic_instructions_include_context():
    deps = MyDeps(rule="no-print")

    with capture_run_messages() as messages:
        my_agent.run_sync(user_prompt="hello", deps=deps, model=TestModel())

    [request, *_] = [m for m in messages if isinstance(m, ModelRequest)]
    assert "no-print" in request.instructions
```

This exercises the real pydantic-ai plumbing and catches issues (wrong deps type, decorator misconfiguration) that a synthetic `RunContext` would miss.

## When to Use the Injected Seam vs Agent.override() vs Model Parameter

Use the injected seam when:
- The code under test takes its model or model source through its constructor (`GeminiJudge` takes `models`)

Use `Agent.override()` when:
- Testing code that invokes a module-level agent internally, with no seam to pass a model through
- Testing the raw `Agent` instance directly without running it yourself

Use the `model` parameter when:
- The test itself calls `agent.run_sync()` or `agent.run()`

```python
# The code takes its models through its constructor - inject the scripted model
judgement = GeminiJudge(tmp_path, MODEL, ScriptedGemini([verdict()]), processes).judge(request)

# Running an agent directly - pass model parameter
result = my_agent.run_sync(user_prompt=message, deps=deps, model=test_model)

# Code that runs a module-level agent internally - use override (no way to pass model through)
with my_agent.override(model=test_model):
    result = pipeline.run("message")
```
