# How a review works

A review checks the changed files against the project's rules. It runs when an agent
stops, in CI ([CI](add-codeguard.md#ci)), and when you run `codeguard review`
([CLI](cli.md)). This page says what a review reports and what the hook does with it.

## What a review reports

A review reports only violations that a line the change adds, edits or removes is part
of: on that line, or for a removed line, where it was. These are the change's changed
lines. What the line held before doesn't matter: editing a line that already broke a rule reports it,
so code a change touches is left better than it was found. Untouched code isn't reported,
even in the function or class around the change: adding a line to a method doesn't
report the method's name, and renaming a variable doesn't report the class's design. A
changed line that breaks a rule together with the code around it is reported, such as a
method that gives its class another responsibility. Other functions and classes in the
file, and the other blocks of a statement around the change, such as the `except` of a
`try` whose body changed, are never reported.

Added and removed blank lines are never part of a change, in any language. Other
whitespace can change meaning, such as indentation in Python, so codeguard leaves it to
the formatter. `--all` reviews every file whole.

A judge rule's violation comes with the judge's confidence: 1.0 when it is certain, 0.9
when the verdict rests on a reading of the rule a reviewer could contest, 0.7 when
something in the repository points to an exception the rule allows, and 0.5 when it is as
likely as not. An error below `confidence_threshold`
([Settings](configuration.md#settings)) is reported as a warning, with its confidence,
and doesn't block, so a warning shows how far it fell short:

```
app/orders.py:12: warning no-pre-derived-arguments: The call passes both lines and the context they come from. (confidence 0.70) [3f1c9a2b7d40]
```

A review stops judging after `review_time_limit_minutes`
([Settings](configuration.md#settings)). Each rule and file it didn't judge is reported
as not checked, at the rule's severity, as a failed judge call is, so an unchecked
`error` rule fails the review.

## The hook

When an agent or subagent stops, the hook runs `codeguard review` in its working
directory: the uncommitted and untracked files, whoever changed them and however. The
hook runs the codeguard the plugin ships, not one on your PATH. Claude Code and Codex get
the same behaviour. [Troubleshooting](using-codeguard.md#troubleshooting) covers a hook
that doesn't run.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed judge call or the time limit).
  The agent can't fix those; CI still fails on them, unless the PR has the
  [`codeguard-allow-judge-errors` label](using-codeguard.md#merge-a-pr-despite-a-judge-error).
- [`ci_only` rules](configuration.md#rule-package-keys) don't run at Stop. They still run
  in CI.
