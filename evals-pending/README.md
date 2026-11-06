# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`. [PR 55](https://github.com/jig-code/codeguard/pull/55) restores
all three.

- `writing-rules/created-flag-tuples`: its grader `03-case-names-say-why` checks case
  names against a list of verbs, while the skill asks a name to say what is at stake, so
  the case fails on names the skill allows. PR 55 rewrites the skill's naming text and
  this case's graders.
- `writing-rules/unused-functions`: its grader `02-names-an-exact-tool` voted fail
  on replies that meet its rubric, declining the judge rule and recommending vulture.
  PR 55 rewrites that grader against its new skill text.
- `writing-rules/flipping-eval-case`: its grader `02-drops-the-contradicting-form`
  voted fail on a SKILL.md that meets its rubric, stating one convention with no broad
  catch in it. PR 55 rewrites that grader against its new skill text.
