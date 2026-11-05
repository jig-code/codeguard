# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`.

- `writing-rules/created-flag-tuples`: skipped until
  [PR 55](https://github.com/jig-code/codeguard/pull/55) restores it. On Opus 5.5 it
  fails `03-case-names-say-the-stake` (a valid case's name that says the code lacks the
  violation instead of what it keeps safe) and `10-few-distinct-cases` (when two
  `invalid` cases differ). PR 55 rewrites the skill text and this case's graders, which
  is where those two sentences belong.
