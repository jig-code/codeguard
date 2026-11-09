---
name: test-quality
description: "Covers what makes a codeguard test give signal and how to assert, mock, name and structure it, including codeguard's LLM tests. Use when writing, editing or reviewing test_*.py or conftest.py files, including test changes made as part of a feature."
---

# Test quality

## Foundational principle

Tests are deterministic: each assertion compares against a value the test can predict in
full. Control an unpredictable value (an id, a timestamp) with a fixture or an injected
value such as a clock rather than leaving it out of the assertion.

Assert with `==`. Use containment (`in`) when the asserted fragment is exact and complete
and sits inside a larger value whose content another component authors, so a whole-value
`==` would pin that component's content rather than the SUT's. Detail and the ownership
test: [signal-and-mocking.md](references/signal-and-mocking.md).

Build test setup with a factory or a direct write, not get-or-create
(`mkdir(exist_ok=True)`, `dict.setdefault`): every test starts from an empty `tmp_path`,
so get-or-create only hides intent.

## Gates

Object construction (factories, fixtures, helpers, constants, where values come from)
belongs to the `pytest-factoryboy` skill. Gates 5, 9, 11, 13, 14, 15 and 16 point there.

1. **Signal.** Each test fails for a plausible bug in your own code, not only for an edit
   to the declaration it mirrors, a framework change or already-tested code; an
   integration test names the wiring bug only it catches. A test without signal is
   maintenance with no protection. [redundant-tests.md](references/redundant-tests.md)
2. **Real objects over mocks.** Use `patch`, `MagicMock` or `monkeypatch.setattr` only
   at the process boundary, and build the SUT through its production factory with the
   double injected. Mocks below the
   boundary pass while production breaks.
   [signal-and-mocking.md](references/signal-and-mocking.md)
3. **`==` over `in`**, as in the foundational principle. Containment passes on output
   you didn't predict. [signal-and-mocking.md](references/signal-and-mocking.md)
4. **Whole result objects.** When the result type has `__eq__`, assert it with one `==`
   (gate 12 covers a field you can't predict); field-by-field asserts miss fields added
   later.
   [signal-and-mocking.md](references/signal-and-mocking.md)
5. **Reuse and construction hygiene:** `pytest-factoryboy`.
6. **Eval inputs differ from instruction examples.** A case that reuses text from
   `src/codeguard/review/judge.md` or the rule's `SKILL.md` tests memorization.
   [eval-testing-guidelines.md](references/eval-testing-guidelines.md)
7. **LLM tests follow the eval guidelines.** Each fixture case is reviewed through
   `Rules.review`, as `codeguard review` does, against the outcome the case expects, with
   no shared runner and no retries; a judge regression shows only on the production path.
   [eval-testing-guidelines.md](references/eval-testing-guidelines.md)
8. **Names match assertions and production vocabulary.** A coined term sends readers
   looking for a concept the code doesn't have.
   [signal-and-mocking.md](references/signal-and-mocking.md)
9. **Fixture design:** `pytest-factoryboy`.
10. **A helper sets up; it doesn't perform the act under test.** A helper that computes
    production's value or returns a method's result hides the behavior being tested.
    [helpers-and-results.md](references/helpers-and-results.md)
11. **Sourcing values:** `pytest-factoryboy`.
12. **No normalizing the result before asserting.** Each field edited out of the actual
    result is a field no longer guarded.
    [helpers-and-results.md](references/helpers-and-results.md)
13. **Construction-helper parameters:** `pytest-factoryboy`.
14. **Helpers earn their existence:** `pytest-factoryboy`.
15. **Test data through fixtures:** `pytest-factoryboy`.
16. **Test object construction:** `pytest-factoryboy`.
17. **Arrange, act and assert stay in the test body.** A phase hidden in a fixture or
    helper hides the cause and effect the test exists to show.
    [helpers-and-results.md](references/helpers-and-results.md)

## Review scope

Review every new and modified test file on the branch, untracked ones included
(`git status`), not only the file being edited. Read the package's `conftest.py` and test
utility modules first so local helpers can be checked against shared ones (gate 5).

Decide the verdict for a recurring shape once and apply it to every instance. When an
instance seems to need a different verdict, sharpen the rule instead.

## Review checklist

For each test, check:

- Every `patch`, `MagicMock`, `monkeypatch.setattr` and subclass of a shared fake (gate 2).
- Every `assert`: exact, whole, and not normalized first (gates 3, 4, 12).
- What would make the test fail, and for an integration test the wiring bug it alone
  catches (gate 1).
- The name against what the assertion proves (gate 8).
- Each helper's return value and each fixture's actions (gates 10, 17).
- Each fixture, factory, helper and module-level constant or function (gates 5, 9, 11,
  13–16, in `pytest-factoryboy`).
- LLM tests and their fixture cases (gates 6, 7).

## References

- [signal-and-mocking.md](references/signal-and-mocking.md): gates 2–4 and 8, with the
  fakes codeguard tests use. Read when mocking, asserting or naming.
- [redundant-tests.md](references/redundant-tests.md): gate 1, the three no-signal
  defects and when an integration test earns its level.
- [helpers-and-results.md](references/helpers-and-results.md): gates 10, 12 and 17.
  Read when a helper or fixture does more than build an object.
- [testing-best-practices.md](references/testing-best-practices.md): isolation and
  testing through public methods.
- [pytest-guidelines.md](references/pytest-guidelines.md): marks and environment
  variables.
- [pydantic-ai-testing-guidelines.md](references/pydantic-ai-testing-guidelines.md):
  scripting the Gemini judge's model with `TestModel` and `FunctionModel`.
- [eval-testing-guidelines.md](references/eval-testing-guidelines.md): gates 6 and 7,
  how codeguard's LLM tests run and the bar they meet.
