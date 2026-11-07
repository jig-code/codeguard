# Eval Testing Guidelines

Eval tests verify LLM behavior with real model calls. They use `pydantic-evals` as the framework intends: a dataset of cases, a task function, built-in evaluators, and one experiment per run. Framework reference: https://pydantic.dev/docs/ai/evals/.

## Running Eval Tests

[docs/testing.md](../testing.md) says which changes need the eval tests and how to run them:

```bash
# Run all eval tests
uv run pytest -m llm -n 4

# Run one eval file
uv run pytest -m llm tests/rules/test_judge_prompt.py

# Run one case
uv run pytest -m llm tests/rules/test_judge_prompt.py -k "responsibility-placement: <case>"
```

To prove reliability, run each case several times; see "Reliability" below.

These rules cover codeguard's own LLM tests and evals. They do not cover `JudgeEvalRunner` and `codeguard eval`, which are product features codeguard ships for rule packages to evaluate their judge rules.

## Where Eval Tests Live

- Put eval tests under `tests/` beside the tests of the code they evaluate, and mark the class `@pytest.mark.llm`. Plain `uv run pytest` deselects them; `-m llm` selects them.
- Put the rules and cases they judge in `evals/judge/`, the fixture rule package, not in the test module.

## The Pattern

```python
@dataclass(frozen=True)
class JudgedChange:
    file: str
    changes: str


def violation_lines(inputs: JudgedChange) -> list[int]:
    skill = Skill.from_file(
        "responsibility-placement", EVALS / "python/skills/responsibility-placement/SKILL.md"
    )
    judge = Judges().uncached(EVALS, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name=MODEL))
    verdict = judge.judge(
        JudgeRequest(skill=skill, file=inputs.file, changes=inputs.changes)
    ).verdict
    return sorted(violation.line for violation in verdict.violations)


@pytest.mark.llm
class TestResponsibilityPlacementEval:
    def test_violation_lines(self):
        dataset = Dataset[JudgedChange, list[int], None](
            name="responsibility_placement_violations",
            cases=[
                Case(
                    name="method_reads_another_types_data",
                    inputs=JudgedChange(file="orders.py", changes="+    12\tdef total(order): ..."),
                    expected_output=[12],
                ),
                Case(
                    name="method_on_its_own_type",
                    inputs=JudgedChange(
                        file="orders.py", changes="+     4\t    def total(self): ..."
                    ),
                    expected_output=[],
                ),
                # every responsibility-placement scenario belongs in this dataset
            ],
            evaluators=[EqualsExpected()],
        )

        report = dataset.evaluate_sync(violation_lines, name=dataset.name)

        assert_eval_passed(report)
```

The rules behind it:

- **One dataset per task.** A dataset holds every case for one behavior of one LLM call, such as "responsibility-placement violations" or "routing an ambiguous statement". Add cases to it as scenarios appear; do not create a dataset per test method.
- **The task function calls the LLM exactly the way production code does,** through the same judge or agent object, then returns the value the cases compare. Do not wrap the call in a shared runner class.
- **Inputs are typed.** When a case needs more than a prompt (a file, its changes, deps that vary per case), make the inputs a frozen dataclass or Pydantic model and build the call inside the task function. Build domain objects with factories and fixtures per the `pytest-factoryboy` skill.
- **Expected results live in `Case.expected_output`,** never in evaluator constructor arguments or case metadata.
- **Name the experiment.** Pass `name=` to `evaluate_sync` so each run is identifiable in the report and its spans.
- **Assert with one `assert_eval_passed(report)`.** It fails on any failed assertion, any evaluator error, and any case whose task raised. codeguard has no such helper yet: define it once in a shared test module when the first eval needs it, and do not write another report assertion.
- Do not wrap evals in a shared eval runner class. A runner hides the framework's task and run options and tends to retry tasks that raise, and a report assertion that ignores cases whose task raised lets them pass. This covers codeguard's own LLM tests and evals, not `JudgeEvalRunner` and `codeguard eval`, which are product features for rule packages.

## Projecting the Output

The task function returns exactly what the case compares. When only part of the output matters, project it in the task function and compare the projection with `EqualsExpected()`:

- Project to plain comparable values (strings, enums, tuples, sorted lists, small dataclasses) or to the real output type when every field matters.
- When order is not part of the contract, sort in the projection.
- Project from the output; never filter on a field and then compare that same field. That comparison is always true when the item exists.

When a single case only needs some fields of a model, a case-level `Contains(value={...})` checks those key/value pairs without a projection.

## Evaluators

Use the framework's built-in evaluators:

| Evaluator | Use for |
|---|---|
| `EqualsExpected()` | The output equals the case's expected output. The default for deterministic output. |
| `Equals(value)` | The output equals a fixed value, as a case-level check. Use `Equals(None)` for a case that expects no output: `EqualsExpected()` skips cases whose expected output is `None`. |
| `Contains(value)` | Substring, list membership, or key/value pairs of a dict or model. |
| `IsInstance(type_name)` | The output type. |
| `MaxDuration(seconds)` | Task duration. |
| `LLMJudge(rubric)` | Non-deterministic text such as summaries and generated messages. Never for output that can be checked exactly. |
| `GEval(...)` | Scored judgment with explicit evaluation steps. |
| `HasMatchingSpan`, `ToolCorrectness`, `TrajectoryMatch`, `ArgumentCorrectness`, `MaxToolCalls`, `MaxModelRequests` | What the agent did: spans, tool calls and their arguments, request counts. |

- Put evaluators shared by every case at dataset level. Add a case-level evaluator only for a check one case needs.
- Write a custom evaluator only for logic no built-in provides. It checks one thing, compares the output against the case's expected output, and does not share a name with a built-in.
- Do not pass a model to each `LLMJudge`; set one default judge model for the session with `set_default_judge_model`, separate from the model under test, so a run against a candidate model keeps the same judge. If the candidate is the judge's model, move the judge to another model first, so no model grades its own output. Write rubrics that state the exact property to check, and set `include_input=True` when the judgment depends on the input.

## The CI Bar

- **Every case passes on every run.** 100%, with no threshold below it.
- **No task retries.** Do not pass `retry_task`. A task that raises, including `UnexpectedModelBehavior` from an agent with no output retries, is a failure.
- Transient transport errors such as throttling belong to the model client, configured as in production. Eval code never retries them.
- `retry_evaluators` is allowed only for `LLMJudge` and other evaluators that call a model.
- A model upgrade meets the same bar. Newer models do not accept a temperature setting, so reliability comes from instructions.

## Reliability

`--llm-runs N` runs each LLM test N times; a reliable eval passes every run. [docs/testing.md](../testing.md) sets how many runs a change needs. `-k` scopes a reliability run to one case:

```bash
uv run pytest -m llm -n 4 --llm-runs 10
uv run pytest -m llm -n 4 --llm-runs 10 -k "responsibility-placement: <case>"
```

A case that fails on any run is a real failure, not a flake. Fix it as below.

## Fix Instructions, Not Inputs

When an eval case fails, fix the agent's instructions, not the eval case input. Eval inputs represent realistic user language.

- **If the agent gets it wrong**: improve the instructions so it handles the input.
- **If the input is genuinely unreasonable**: remove the case rather than softening it.
- **Never strengthen input language** (for example, adding "this is non-negotiable") to work around an instruction gap.

## Eval Independence from Instruction Examples

Eval inputs must not duplicate text from the agent's instruction examples. A case that reuses an instruction example tests memorization, not the rule. Use different domains, phrasing and values from those in the judge's instructions (`src/codeguard/review/judge.md`) and the rule's `SKILL.md`.

## Debugging Failures

Tests send nothing to Logfire: the autouse `no_telemetry` fixture removes `LOGFIRE_TOKEN`. Read a failure from the test report, which shows each case's output and evaluator results. To check what a run recorded, capture its spans in the test (`capfire`) and assert on their attributes.
