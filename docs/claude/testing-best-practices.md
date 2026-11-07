# Testing Best Practices

These guidelines apply when writing or reviewing test code. For quality gates (documentation, redundancy, mocking boundaries, assertions), see the test-quality skill in `.claude/skills/test-quality/SKILL.md`.

## Test Isolation

Tests must clean up properly:

- Patched clocks and timers must be restored (use `monkeypatch`, which undoes itself)
- Global state must be reverted
- Resources must be cleaned up in pytest fixtures (`yield`, then tear down)
- Files and repositories live under `tmp_path`, never in the working tree

## Mocking Boundaries

Mock at external boundaries only — where code leaves the process (model provider API call, judge CLI subprocess, HTTP request, AWS SDK call). Never mock internal dispatch, collaborating classes in the same bounded context, or private methods.

A common mistake is patching an internal dispatch table or collaborating class because it *eventually* calls an external service:

```python
# BAD - Patching internal dispatch and collaborating class
with (
    patch("myapp.classify._RUNNERS") as mock_runners,
    patch("myapp.handler.MyHandler.run_for_field", return_value=result),
):
    Classifier(model).classify(batches, evidence)

# GOOD - Mock the external call (LLM, HTTP, AWS SDK) at the seam the code injects
Classifier(TestModel(custom_output_args=expected)).classify(batches, evidence)
```

The bad version tests how `classify` dispatches internally — refactoring the dispatch breaks every test even if behavior is unchanged. The good version lets all internal code run and only substitutes what leaves the process.

### Layer 2: Integration Tests (scripted FunctionModel through the injected seam)

Script the model's answers with a pydantic-ai `FunctionModel` and hand it to the code through the seam it already takes, to capture and inspect what the code sends to the model. This verifies wiring without LLM calls.

**When to use:**
- Testing that a judge builds its request correctly
- Verifying the skill, the changes, or other context appears in instructions
- Testing judge-to-model integration

**IMPORTANT:** Hand the scripted model in through the constructor seam the code already has (`GeminiJudge` takes its `models`). Do not add `model` parameters to methods only so tests can pass one. Where an agent is module-level and has no such seam, use the `Agent.override()` context manager instead.

```python
def test_judge_sends_the_judge_instructions(tmp_path, make_judge_request):
    models = ScriptedGemini([verdict()])
    request = make_judge_request()

    GeminiJudge(tmp_path, MODEL, models, RecordingProcesses()).judge(request)

    assert models.info().instructions == request.instructions.strip()
```

**Shared test doubles** in `tests/gemini_provider/test_gemini_judge.py` and `tests/recording_judge.py`:
- `ScriptedGemini(answers)` - yields a `FunctionModel` that returns (or raises) each scripted answer in order and records every request in `requests`
- `RecordingJudge` - a judge that records each request it receives in `received`

### Layer 3: Eval Tests (Real LLM)

Use real LLM calls to verify agent behavior and output quality.

**When to use:**
- Testing that a judge finds the right violations in a change
- Verifying the judge does not flag a change that keeps the rule
- Regression testing prompt changes

Write them per [eval-testing-guidelines.md](eval-testing-guidelines.md); they are `@pytest.mark.llm`, and [docs/testing.md](../testing.md) says when to run them and how.

### Key Principles

1. **Test through public methods** - Don't test private methods like `_build_deps`. Script the model with a `FunctionModel` through the injected seam to verify what gets sent to the agent.

2. **Use the injected seam, or `Agent.override()`, for all agent testing** - Do NOT add `model` parameters to methods only for tests. Pass the scripted model through the constructor seam the code already has, or use the override context manager where there is none:
   ```python
   GeminiJudge(tmp_path, MODEL, ScriptedGemini([verdict()]), RecordingProcesses()).judge(request)

   with my_agent.override(model=recording_model):
       service.extract(user_prompt="test")  # No model parameter needed
   ```

3. **Eval tests call agents directly** - Keep eval tests focused on agent behavior by calling agents directly with constructed deps, not through services.

4. **Use `agent.override()` for multi-step code** - When testing code that invokes a module-level agent internally, with no seam to inject the model, use the override context manager:
   ```python
   with my_agent.override(model=TestModel(), deps=test_deps):
       pipeline.run(...)
   ```

## Agent Instructions

When creating or modifying the judge's instructions (`src/codeguard/review/judge.md`) or a rule's skill, follow [skills/writing-rules/SKILL.md](../../skills/writing-rules/SKILL.md). Key principles:

- Schema defines WHAT (structure), instructions define HOW (behavior) and WHEN (what counts as a violation)
- Include explicit completion criteria
- Add natural language interpretation guidelines to reduce false positives
- Use dynamic context injection via `@agent.instructions` for runtime values
- Include worked examples showing expected input/output behavior

## Mocking Guidelines

Tests should verify behavior, not implementation. Over-mocking creates brittle tests that break on refactoring even when behavior is unchanged.

### When to Mock

Mock at external boundaries and for exception cases:

- **External APIs**: HTTP calls, third-party services, cloud providers
- **Time/randomness**: For deterministic, reproducible tests
- **Exception paths**: Error conditions that are hard to trigger naturally (network failures, disk full, etc.)

### Never Mock Git or the Filesystem

Tests use a real temporary git repository (`GitRepo`, the `repo` fixture) and real files under `tmp_path`. Use Factory Boy to create test data instead of mocking git output, file reads, or the objects built from them. Mocked git output diverges from real git behavior and hides issues like wrong diff ranges, missing untracked files, or changed command flags.

### When NOT to Mock

Avoid mocking internal implementation details:

- **Internal method calls**: Don't mock methods within the same class/module
- **Collaborating classes**: Don't mock classes within the same bounded context
- **Arguments between components**: Don't assert on internal data structures passed between internal components
- **Private methods**: If you need to mock a private method, the design likely needs refactoring

### Why This Matters

Over-mocking leads to:

- **False confidence**: Tests pass but don't exercise real code paths
- **Brittle tests**: Refactoring breaks tests even when behavior is unchanged
- **Testing implementation**: Mocking internal calls tests HOW code works, not WHAT it does

**Good test**: Verifies that calling `process_order(order)` results in the correct stored state and API calls.

**Bad test**: Mocks internal `_validate_order()` and `_calculate_total()` calls, then asserts they were called with specific arguments.

## Avoid Redundant Tests

Do not write a test that only verifies something already proven by other tests. Before adding a test, ask: "If this test were deleted, would any behavior go unverified?" If the answer is no, don't write it.

Common redundant test patterns to avoid:

- **Smoke tests**: Do not write tests that merely verify a concrete type works with generic infrastructure (e.g., passing `OrderState` through a generic `build_registry` to check the metadata comes out right). If the generic logic is already tested and the concrete type's metadata is declarative config, the smoke test adds no new signal.
- **Pass-through subclass tests**: Do not write tests for a subclass that adds no custom logic (e.g., `class OrderStateMapper(StateMapper[OrderState]): pass`). If the subclass body is empty or only sets type parameters, its behavior is entirely inherited and already covered by the base class tests. Only test a subclass when it overrides or extends behavior.
- **`isinstance` / subclass checks**: If other tests in the file call methods or access attributes on the object, a separate `test_is_instance_of(MyClass)` or `test_is_subclass` adds nothing — the object's type is proven by the other tests succeeding.
- **Protocol conformance checks**: If every test calls `mapper.apply()` and asserts on the result, a separate `test_satisfies_protocol` that checks `isinstance(mapper, Protocol)` adds no value.
- **Exhaustive enum/literal value iteration**: Looping over every member of an Enum or Literal to assert it's accepted is testing framework validation (Pydantic, stdlib), not business behavior. Test the values that matter to your logic; the framework guarantees the rest.
- **Domain-variant test files**: Do not create per-domain test files (e.g., `orders/tests/test_update_interpreter.py`, `invoices/tests/test_update_interpreter.py`) that replay the same operations (add/remove/update) through a generic class with different model types. If the generic class is already tested with synthetic models in its own test suite (e.g., `core/tests/test_update_interpreter.py`), per-domain files that just plug in real models exercise the same code paths. Only add domain-specific tests when the domain introduces custom logic, overrides, or edge cases that the generic tests cannot reach.

## Assertion Guidelines

### Prefer Equality Over Containment Checks

When the expected value is deterministic and known, use `==` instead of `in`. Containment checks (`in`) are weaker assertions that can pass even when the actual value contains unexpected content or has changed in unintended ways. This applies to strings, collections, and any type that supports equality comparison.

```python
# AVOID - Weak assertions that mask bugs
assert "expected_value" in result.name
assert expected_item in result_list
assert key in result_dict

# PREFERRED - Exact match catches any unexpected changes
assert result.name == "expected_value"
assert result_list == [expected_item]
assert result_dict == {key: expected_value}
```

Use `in` only when you genuinely need a containment check (e.g., verifying a keyword appears in a long, non-deterministic string like LLM output, or checking membership in a collection whose other elements are irrelevant to the test).
