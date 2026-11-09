# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`.

- `writing-rules/writes-rule-created-flag-tuples`: four counted runs each missed 3 of 3,
  each on a different grader: whether a framework's own get-or-create call keeps the
  rule, whether the eval's cases are distinct, whether the statement is one convention,
  and whether the Why states only the harm. [PR 77](https://github.com/jig-code/codeguard/pull/77) restores it.
