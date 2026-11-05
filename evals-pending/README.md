# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`.

- `writing-rules/created-flag-tuples`: skipped until
  [PR 55](https://github.com/jig-code/codeguard/pull/55) restores it. Its grader
  `03-case-names-say-why` checks case names against a list of verbs, while the skill
  asks a name to say what is at stake, so the case fails on names the skill allows.
  PR 55 rewrites the skill's naming text and this case's graders.
