# Testing Best Practices

These guidelines apply when writing or reviewing test code. For quality gates (documentation, redundancy, mocking boundaries, assertions), see the test-quality skill in `.claude/skills/test-quality/SKILL.md`.

## Test Isolation

Tests must clean up properly:

- Mock timers must be reset (`jest.useRealTimers()` in JavaScript)
- Global state must be reverted
- Resources must be cleaned up in `afterEach`/`afterAll` (JavaScript) or pytest fixtures (Python)
- Database transactions should be rolled back

## Mocking Boundaries

Mock at external boundaries only — where code leaves the process (LLM API call, HTTP request, AWS SDK call). Never mock internal dispatch, collaborating classes in the same bounded context, or private methods.

A common mistake is patching an internal dispatch table or collaborating class because it *eventually* calls an external service:

```python
# BAD - Patching internal dispatch and collaborating class
with (
    patch("myapp.nodes.classify._RUNNERS") as mock_runners,
    patch("myapp.handler.MyHandler.run_for_field", return_value=result),
):
    classify(batches, evidence)

# GOOD - Mock the external call (LLM, HTTP, AWS SDK)
with my_agent.override(model=TestModel(custom_output_args=expected)):
    classify(batches, evidence)
```

The bad version tests how `classify` dispatches internally — refactoring the dispatch breaks every test even if behavior is unchanged. The good version lets all internal code run and only substitutes what leaves the process.

### Layer 2: Integration Tests (SequentialTestModel + Agent.override)

Use `SequentialTestModel` with `Agent.override()` to capture and inspect what services send to agents. This verifies wiring without LLM calls.

**When to use:**
- Testing that services build deps correctly
- Verifying evidence, context, or state appears in instructions
- Testing service-to-agent integration

**IMPORTANT:** Use `Agent.override()` context manager instead of passing model parameters to services. This is the pydantic-ai recommended pattern that keeps services clean and testable without modifying their interfaces.

```python
from testing.agent_models import (
    SequentialTestModel,
    extract_instructions_text,
)
from agents.services.my_agent import my_agent  # Import the agent directly

def test_service_includes_evidence():
    recording_model = SequentialTestModel([valid_response])

    # Use Agent.override() - do NOT pass model to service methods
    with my_agent.override(model=recording_model):
        service.extract(user_prompt="test")

    instructions = extract_instructions_text(recording_model.captured_messages)
    assert "expected content" in instructions
```

**Shared utilities** in `testing/agent_models.py`:
- `SequentialTestModel(responses)` - TestModel that returns each scripted response in order and captures messages in the `captured_messages` attribute
- `extract_instructions_text(messages)` - Extract instructions from captured messages

### Layer 3: Eval Tests (Real LLM)

Use real LLM calls to verify agent behavior and output quality.

**When to use:**
- Testing that agents extract correct data from inputs
- Verifying clarification behavior
- Regression testing prompt changes

Write them per [eval-testing-guidelines.md](eval-testing-guidelines.md).

### Key Principles

1. **Test services through public methods** - Don't test private methods like `_build_deps`. Use `SequentialTestModel` with `Agent.override()` to verify what gets sent to the agent.

2. **Use `Agent.override()` for all agent testing** - Do NOT add `model` parameters to service methods. Instead, use the override context manager:
   ```python
   from agents.services.my_agent import my_agent

   with my_agent.override(model=recording_model):
       service.extract(user_prompt="test")  # No model parameter needed
   ```

3. **Eval tests call agents directly** - Keep eval tests focused on agent behavior by calling agents directly with constructed deps, not through services.

4. **Use `agent.override()` for workflows** - When testing LangGraph workflows where agents are invoked internally, use the override context manager:
   ```python
   with my_agent.override(model=TestModel(), deps=test_deps):
       workflow.invoke(...)
   ```

## Agent Instructions

When creating or modifying agent instructions, refer to `.claude/skills/agent-prompts/SKILL.md`. Key principles:

- Schema defines WHAT (structure), instructions define HOW (behavior) and WHEN (clarification)
- Include explicit completion criteria and clarification strategy
- Add natural language interpretation guidelines to reduce unnecessary clarification
- Use dynamic context injection via `@agent.instructions` for runtime values
- Include worked examples showing expected input/output behavior

## Mocking Guidelines

Tests should verify behavior, not implementation. Over-mocking creates brittle tests that break on refactoring even when behavior is unchanged.

### When to Mock

Mock at external boundaries and for exception cases:

- **External APIs**: HTTP calls, third-party services, cloud providers
- **Time/randomness**: For deterministic, reproducible tests
- **Exception paths**: Error conditions that are hard to trigger naturally (network failures, disk full, etc.)

### Never Mock the Database

Unit tests use a real test database. Use Factory Boy to create test data instead of mocking querysets, model instances, or relationships. Mocked querysets diverge from real ORM behavior and hide issues like missing fields, broken relationships, or queryset method changes.

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

**Good test**: Verifies that calling `process_order(order)` results in the correct database state and API calls.

**Bad test**: Mocks internal `_validate_order()` and `_calculate_total()` calls, then asserts they were called with specific arguments.

## Avoid Redundant Tests

Do not write a test that only verifies something already proven by other tests. Before adding a test, ask: "If this test were deleted, would any behavior go unverified?" If the answer is no, don't write it.

Common redundant test patterns to avoid:

- **Smoke tests**: Do not write tests that merely verify a concrete type works with generic infrastructure (e.g., passing `MatchCriteriaState` through `build_field_registry` to check the metadata comes out right). If the generic logic is already tested and the concrete type's metadata is declarative config, the smoke test adds no new signal.
- **Pass-through subclass tests**: Do not write tests for a subclass that adds no custom logic (e.g., `class ADLStateMapper(StateMapper[ADLState]): pass`). If the subclass body is empty or only sets type parameters, its behavior is entirely inherited and already covered by the base class tests. Only test a subclass when it overrides or extends behavior.
- **`isinstance` / subclass checks**: If other tests in the file call methods or access attributes on the object, a separate `test_is_instance_of(MyClass)` or `test_is_subclass` adds nothing — the object's type is proven by the other tests succeeding.
- **Protocol conformance checks**: If every test calls `mapper.apply()` and asserts on the result, a separate `test_satisfies_protocol` that checks `isinstance(mapper, Protocol)` adds no value.
- **Exhaustive enum/literal value iteration**: Looping over every member of an Enum or Literal to assert it's accepted is testing framework validation (Pydantic, stdlib), not business behavior. Test the values that matter to your logic; the framework guarantees the rest.
- **Domain-variant test files**: Do not create per-domain test files (e.g., `wellsky_domain/adl/tests/test_update_interpreter.py`, `wellsky_domain/match_criteria/tests/test_update_interpreter.py`) that replay the same operations (add/remove/update) through a generic class with different model types. If the generic class is already tested with synthetic models in its own test suite (e.g., `chat_workflow_core/tests/test_update_interpreter.py`), per-domain files that just plug in real models exercise the same code paths. Only add domain-specific tests when the domain introduces custom logic, overrides, or edge cases that the generic tests cannot reach.

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
