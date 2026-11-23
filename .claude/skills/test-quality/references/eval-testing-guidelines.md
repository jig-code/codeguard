# LLM tests (gates 6, 7)

- How codeguard's LLM tests run
- Cases
- The bar
- Failures

These rules cover codeguard's own LLM tests. Their fixture cases test the judge, not
their rule, so the writing-rules guidance on rule eval cases doesn't apply.
[docs/testing.md](../../../../docs/testing.md) sets out how the LLM tests, skill evals
and rule evals differ.

## How codeguard's LLM tests run

`tests/project/test_judge_prompt.py` parametrizes one test over every judged case of the
fixture rules' rule evals (`evals/judge/python/rule-evals/<rule>.yaml`). For each case it
writes the case's edits into a `WorkingTree.temporary`, with a `.codeguard/config.yaml` that
includes only that rule, and reviews them with
`ProjectReview.of(Project.load(working_tree)).review(...)` on the changed lines: the path
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
- Review through `ProjectReview.review`, as above. Don't wrap the review in a shared runner class:
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
