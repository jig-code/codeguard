# Eval Testing Guidelines

Eval tests verify LLM behavior with real model calls. They use `pydantic-evals` as the framework intends: a dataset of cases, a task function, built-in evaluators, and one experiment per run. Framework reference: https://pydantic.dev/docs/ai/evals/.

## Running Eval Tests

Always use the task command:

```bash
# Run all eval tests
task backend:test_eval

# Run one eval file
task backend:test_eval -- referral_accounts/referral_visit/evals/test_referral_visit_extraction_eval.py

# Run one test
task backend:test_eval -- referral_accounts/referral_visit/evals/test_referral_visit_extraction_eval.py::TestReferralVisitExtractionEval::test_extracts_accounts_as_a_valid_list_across_representative_notes
```

To prove reliability, run the suite repeatedly in independent processes; see "Reliability" below.

## Where Eval Tests Live

- Put eval tests in an `evals/` directory beside the code they evaluate, named `test_*_eval.py`, marked `@pytest.mark.eval`.
- Add every new `evals/` directory to the `testpaths` in `backend/pytest-eval.ini`, or `task backend:test_eval` will not collect it.
- Give every `evals/` directory a `conftest.py` that re-exports `chat_workflow_core.testing.plugin`; copy an existing one. The plugin sets the `LLMJudge` model from `EVAL_JUDGE_MODEL_ARN` and flushes Logfire at the end of the session.

## The Pattern

```python
@dataclass(frozen=True)
class ReferralNoteInputs:
    note: str
    prior_messages: tuple[str, ...] = ()


def extract_account_names(inputs: ReferralNoteInputs) -> list[str]:
    directory = OfficeReferralAccountDirectory(office=None, accounts=[], prospects=[])
    extraction = ReferralVisitExtractor().extract(
        inputs.note,
        directory,
        list(inputs.prior_messages),
        visit_date=timezone.now(),
    )
    return sorted(account.name for account in extraction.accounts)


@pytest.mark.eval
class TestReferralVisitExtractionEval:
    def test_account_extraction(self):
        dataset = Dataset[ReferralNoteInputs, list[str], None](
            name="referral_visit_account_extraction",
            cases=[
                Case(
                    name="one_account_named_in_note",
                    inputs=ReferralNoteInputs(note="Visited Riverside Senior Living today..."),
                    expected_output=["Riverside Senior Living"],
                ),
                Case(
                    name="no_accounts_in_family_note",
                    inputs=ReferralNoteInputs(note="Spoke with the daughter about..."),
                    expected_output=[],
                ),
                # every account-extraction scenario belongs in this dataset
            ],
            evaluators=[EqualsExpected()],
        )

        report = dataset.evaluate_sync(extract_account_names, name=dataset.name)

        assert_eval_passed(report)
```

The rules behind it:

- **One dataset per task.** A dataset holds every case for one behavior of one LLM call, such as "account extraction" or "routing an ambiguous statement". Add cases to it as scenarios appear; do not create a dataset per test method.
- **The task function calls the LLM exactly the way production code does,** through the same agent object or extractor, then returns the value the cases compare. Do not wrap the call in a shared runner class.
- **Inputs are typed.** When a case needs more than a prompt (prior messages, a directory, deps that vary per case), make the inputs a frozen dataclass or Pydantic model and build the call inside the task function. Build domain objects with factories and fixtures per the `pytest-factoryboy` skill.
- **Expected results live in `Case.expected_output`,** never in evaluator constructor arguments or case metadata.
- **Name the experiment.** Pass `name=` to `evaluate_sync` so each run is identifiable in Logfire.
- **Assert with `assert_eval_passed`** from `chat_workflow_core.testing.eval_runner`. It fails on any failed assertion, any evaluator error, and any case whose task raised. Do not write another report assertion.
- Do not use `EvalRunner` or `assert_report_passed` in new evals. They are being removed: `EvalRunner` hides the framework's task and run options and retries tasks that raise, and `assert_report_passed` ignores cases whose task raised.

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
- Of the custom evaluators in `backend/testing/evaluators.py`, only `UnorderedEqualsExpected`, `MatchesAnyOfFields` (several outputs are equally valid) and `DoesNotContainTerms` remain for new evals. The others duplicate built-ins or projections and are being removed.
- Do not pass a model to `LLMJudge`; the eval plugin sets the judge model from `EVAL_JUDGE_MODEL_ARN`, separate from `CHAT_AI_MODEL_ARN`, so a run against a candidate model keeps the same judge. If the candidate is the judge's model, move the judge to another model first, so no model grades its own output. Write rubrics that state the exact property to check, and set `include_input=True` when the judgment depends on the input.

## The CI Bar

- **Every case passes on every run.** 100%, with no threshold below it.
- **No task retries.** Do not pass `retry_task`. A task that raises, including `UnexpectedModelBehavior` from an agent with no output retries, is a failure.
- Transient transport errors such as throttling belong to the model client, configured as in production. Eval code never retries them.
- `retry_evaluators` is allowed only for `LLMJudge` and other evaluators that call a model.
- A model upgrade meets the same bar. Newer models do not accept a temperature setting, so reliability comes from instructions.

## Reliability

`task backend:test_eval_reliability` runs the suite in independent processes and reports the pass rate; a reliable eval passes every run. Route a dataset's cases through `selected_eval_cases` so `CASE=<case_name>` can scope a reliability run to one case:

```bash
task backend:test_eval_reliability REPEAT=10
task backend:test_eval_reliability CASE=one_account_named_in_note REPEAT=10
```

A case that fails on any run is a real failure, not a flake. Fix it as below.

## Fix Instructions, Not Inputs

When an eval case fails, fix the agent's instructions, not the eval case input. Eval inputs represent realistic user language.

- **If the agent gets it wrong**: improve the instructions so it handles the input.
- **If the input is genuinely unreasonable**: remove the case rather than softening it.
- **Never strengthen input language** (for example, adding "this is non-negotiable") to work around an instruction gap.

## Eval Independence from Instruction Examples

Eval inputs must not duplicate text from the agent's instruction examples. A case that reuses an instruction example tests memorization, not the rule. Use different domains, phrasing and values from those in the agent's `*_instructions.md`.

## Debugging Failures

Eval runs report to the `otter-dev` Logfire project. Logfire picks the project from the write token; `LOGFIRE_PROJECT` only sets the `deployment.environment` label. CI uses the `LOGFIRE_TOKEN` repository secret, an `otter-dev` token. Locally, put an `otter-dev` write token in `LOGFIRE_TOKEN` in the root `.env`; with it blank, evals still run but send nothing.

Each experiment appears in Logfire with its cases, outputs and evaluator results. Pydantic-ai agents and extractors that call `AnthropicBedrock` directly both record their model requests and responses.
