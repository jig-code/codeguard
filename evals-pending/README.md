# Skipped skill eval cases

`claude plugin eval` runs every case under `evals/`, and has no option to skip one, so a
skipped case lives here until the change that restores it moves it back to
`evals/writing-rules/`. [PR 55](https://github.com/jig-code/codeguard/pull/55) restores
both.

- `writing-rules/writes-rule-created-flag-tuples`: its agent states one requirement twice,
  and its Why proposes a fix where the graders split on whether that's allowed.
  [PR 77](https://github.com/jig-code/codeguard/pull/77) restores it, with the skill and
  its graders saying how to state a prohibition once and what a Why leaves out.
- `writing-rules/changes-rule-flipping-eval-case`: its grader `02-drops-the-contradicting-form`
  voted fail on a SKILL.md that meets its rubric, stating one convention with no broad
  catch in it. PR 55 rewrites that grader against its new skill text.
