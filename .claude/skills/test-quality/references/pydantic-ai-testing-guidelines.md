# Scripting the model (pydantic-ai)

The Gemini judge runs a pydantic-ai agent. Tests replace the model, not the agent or the
code around it, so no LLM is called and every line of codeguard still runs.

## Pass the model through the seam the code takes

`GeminiJudge` takes its models in its constructor; hand it the scripted model there. Don't
add a `model` parameter to a method only so a test can pass one. Where code runs a
module-level agent with no seam, use `agent.override(model=...)`; where the test itself
runs the agent, pass `model=` to `run_sync`.

## Choose the double by the calls the test makes

- `ScriptedGemini([...])`, the default: a `FunctionModel` that returns or raises each
  scripted answer in order, records every request in `requests`, and raises when called
  more times than scripted. Assert `models.answers == []` to prove every answer was used.
- `TestModel(custom_output_args=...)`: one call with one output.
- A `FunctionModel` that picks its answer from the request: when the answer depends on the
  call's output schema or content rather than call order.

```python
models = ScriptedGemini([calls(("read_file", {"path": "a.py"})), verdict(VIOLATION)])

judgement = judge_with(tmp_path, models).judge(make_judge_request())

assert judgement.verdict.violations == (Violation.model_validate(VIOLATION),)
assert models.answers == []
```

Give a `TestModel` realistic `custom_output_args`; bare `TestModel()` returns empty
defaults, so the test can't show the output flowed through. A bare `TestModel()` is fine
for an agent that isn't under test in a path test (routing, error flow), and the test's
name says it is about the path.

## Errors

Have the scripted model raise what the provider would
(`ScriptedGemini([http_error(400, "Bad request.")])`, then
`pytest.raises(JudgeProcessError)`), not a patched internal method.

## Instructions

To check instructions the agent assembles at run time, run the agent inside
`capture_run_messages()` and read the `instructions` of the `ModelRequest` it sent, or
read `models.info().instructions` from `ScriptedGemini`. A hand-built `RunContext` skips
the real plumbing (deps type, decorator wiring).
