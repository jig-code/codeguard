# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`. [PR 55](https://github.com/jig-code/codeguard/pull/55) restores
it.

- `writing-rules/writes-rule-created-flag-tuples`: its grader that checked case names against a list
  of verbs failed names the skill allows, and is removed. PR 55 rewrites this case's
  other graders against its new skill text.
