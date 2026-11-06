# How a review works

A review checks the changed files against the project's rules: pattern rules first, then
the judge for each judge rule whose triggers the change touches. It runs when an agent
stops, in CI ([CI](add-codeguard.md#ci)), and when you run `codeguard review`
([CLI](cli.md)). [The review pipeline](review-pipeline.md) has the design.

## What the judge sees and reports

The judge gets the code the change touched, as
[Judge input](judge-design.md#judge-input) lists, and reads the rest with its tools. A new
file is sent whole but for its blank lines outside a function or method; every file with
`--all` is sent whole, all of it marked changed. A review reports only what the
[review-scope invariant](architecture.md#invariants) allows: violations a changed or
removed line is part of.

codeguard ignores added and removed blank lines, which change nothing in any language.
Other whitespace can change meaning, such as indentation in Python, so codeguard
leaves it to the formatter.

A verdict is reused until the changed code, the rest of the file, the rule, the model, or a
file the judge loaded changes ([Verdict cache](review-pipeline.md#verdict-cache)).

The judge's reason and its [confidence scale](judge-design.md#judge-input) are part of
its verdict. A judged diagnostic prints its confidence, so a warning below
`confidence_threshold` ([Settings](configuration.md#settings))
shows how far it fell short:

```
app/orders.py:12: warning no-pre-derived-arguments: The call passes both lines and the context they come from. (confidence 0.70) [3f1c9a2b7d40]
```

## The hooks

When an agent or subagent stops, the hook runs `codeguard review` in its working
directory: the uncommitted and untracked files, whoever changed them and however. The
hook runs the codeguard the plugin ships, not one on your PATH. Claude Code and Codex get the same behaviour.
[Troubleshooting](using-codeguard.md#troubleshooting) covers a hook that doesn't run.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed `claude` call or the time
  limit). The hook passes `--judge-errors-as-warnings`, since the agent can't fix those;
  CI still fails on them, unless the PR has the
  [`codeguard-allow-judge-errors` label](using-codeguard.md#merge-a-pr-despite-a-judge-error).
- The hook passes `--skip-ci-only`, so [`ci_only` rules](configuration.md#rule-package-keys) don't
  run.
