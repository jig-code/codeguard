# LLM tests (gates 6, 7)

- How codeguard's LLM tests run
- Cases
- The bar
- Failures
- pydantic-evals datasets

codeguard has three kinds of eval, each testing something different. This reference
covers only the LLM tests.

| | Tests | Cases | Runs with | Guidance |
|---|---|---|---|---|
| LLM tests | codeguard's judge: that it reaches the right verdict on a rule and a change | `evals/judge/` | `uv run pytest -m llm` | This reference |
| Rule evals | A project's or package's judge rules: that each rule's wording gets the right verdicts from the judge | `rule-evals/` beside the rules | `codeguard eval`, a product feature built on pydantic-evals | The writing-rules skill's [judge-rules.md](../../../../skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases) |
| Skill evals | The writing-rules skill: that an agent following it writes good rules | `evals/writing-rules/` | `claude plugin eval` | [docs/skill-evals.md](../../../../docs/skill-evals.md) |

The judge fixtures in `evals/judge/` use the rule eval format, but they are LLM test
cases: they test the judge, not their rule, so the rule eval guidance doesn't apply.

## How codeguard's LLM tests run

`tests/rules/test_judge_prompt.py` parametrizes one test over every judged case of the
fixture rules' rule evals (`evals/judge/python/rule-evals/<rule>.yaml`). For each case it
writes the case's edits into a `WorkingTree.temporary`, with a `.codeguard/config.yaml` that
includes only that rule, and reviews them with
`Rules(working_tree).review(working_tree.changed_lines("HEAD"))`: the path
`codeguard review` takes, with the real judge the fixture package names. It asserts the
review has no judge errors and that its outcome is the case's expected outcome.

Mark an LLM test `@pytest.mark.llm` on its class. Plain `uv run pytest` deselects it.

```bash
uv run pytest -m llm -n 4
uv run pytest -m llm -n 4 --llm-runs 10 -k "exception-handling: <case>"
uv run pytest -m llm -n 4 --judge-provider gemini
```

`--llm-runs N` runs each case N times (default 3). `--judge-provider` and `--judge-model`
judge every case with another provider or model than its package names. `docs/testing.md`
says which changes need the LLM tests and how many runs.

## Cases

- Each case tests one judge behavior, such as reporting a violation that a removed line
  creates, and no two cases test the same one.
- A review-scope case may hold an old violation in code the change doesn't touch, which
  the review must leave unreported. Keep it small and plain, and let it break no other
  rule.
- A new scenario is a new case in the fixture rule's rule eval, not a new test method or
  test module. The rules and cases live in `evals/judge/`, not in the test module.
- A case's expected result lives in the case (`expected_output`).
- One case per input, judged on its whole review outcome.
- Review through `Rules.review`, as above. Don't wrap the review in a shared runner class:
  a runner hides run options and tends to retry what raised.
- Case inputs use different domains, phrasing and values from the examples in
  `src/codeguard/review/judge.md` and the rule's file, `rules/judge/<id>.md` (gate 6). A
  case that reuses an example tests memorization.

## The bar

- Every case passes on every run, with no threshold below 100%.
- No retries of a case. A judge that raises, or a judge error in the review, is a failure.
- Transient transport errors such as throttling belong to the provider client, configured
  as in production; test code never retries them.
- A model upgrade meets the same bar. Newer models take no temperature setting, so
  reliability comes from the instructions.

## Failures

A case that fails on any run is a real failure, not a flake. Fix the judge's
instructions or the rule's skill, not the case input, which stands for realistic code.
When the input is unreasonable, remove the case rather than softening it. Never add
emphasis to the input ("this is non-negotiable") to cover an instruction gap.

Tests send nothing to Logfire (the autouse `no_telemetry` fixture). Read a failure from
the test report, which lists the review's diagnostics; to check what a run recorded,
capture its spans with `capfire` and assert on their attributes.

## pydantic-evals datasets

When an LLM test evaluates a pydantic-evals `Dataset`:

- One dataset per behavior of one LLM call, holding every case for it. Its task function
  calls the LLM the way production does and returns the value the cases compare.
- Expected results live in `Case.expected_output`, not in evaluator arguments or metadata.
- Compare with built-in evaluators, `EqualsExpected()` by default, set at dataset level. A
  case that expects no output uses `Equals(None)`, since `EqualsExpected()` skips cases
  whose expected output is `None`. Write a custom evaluator only for logic no built-in
  has, under a name no built-in uses.
- Project the output in the task function to what the case compares: plain values, sorted
  when order isn't part of the contract. Don't filter on a field and then compare that
  field.
- `LLMJudge` only for text that can't be checked exactly, with one default judge model set
  by `set_default_judge_model` that differs from the model under test.
- No `retry_task`; `retry_evaluators` only for evaluators that call a model.
- Name the experiment (`evaluate_sync(task, name=dataset.name)`) and assert with one
  report assertion that fails on any failed case, evaluator error or raised task.
