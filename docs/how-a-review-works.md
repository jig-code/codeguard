# How a review works

A review checks the changed files against the project's rules: pattern rules first, then
the judge for each judge rule whose triggers the change touches. It runs when an agent
stops, in CI ([CI](add-codeguard.md#ci)), and when you run `codeguard review`
([CLI](cli.md)). [The review pipeline](review-pipeline.md) has the design.

## What the judge sees and reports

The judge gets the code the change touched, as [Judge input](judge-design.md#judge-input)
lists, and reads the rest of the file, or any other file in the repository, with its
read-only tools. A new file is sent whole but for its blank lines outside a function or
method; every file with `--all` is sent whole, all of it marked changed.

codeguard ignores added and removed blank lines, which change nothing in any language.
Other whitespace can change meaning, such as indentation in Python, so codeguard
leaves it to the formatter.

A review reports only violations a changed or removed line is part of, on that line. What
the line held before doesn't matter: editing a line that already broke a rule reports it,
so code a change touches is left better than it was found. Untouched code isn't reported,
even in the function or class around the change: adding a line to a method doesn't
report the method's name, and renaming a variable doesn't report the class's design. A
changed line that breaks a rule together with the code around it is reported, such as a
method that gives its class another responsibility. Other functions and classes in the
file, and the other blocks of a statement around the change, such as the `except` of a
`try` whose body changed, are read as context but never reported (the
[review-scope invariant](architecture.md#invariants)).

A verdict is reused until the changed code, the rest of the file, the rule, the model, or
a file the judge loaded changes ([Verdict cache](review-pipeline.md#verdict-cache)).

The judge gives a reason with every verdict, pass or fail: one sentence saying what in
the changed code keeps the rule or breaks it. A rule eval prints it for every case; a
review prints each violation's message.

The judge rates its confidence in each violation on a fixed scale
([Judge input](judge-design.md#judge-input)). An error below `confidence_threshold`
([Settings](configuration.md#settings)) is reported as a warning, with its confidence,
and doesn't block, so a warning shows how far it fell short:

```
app/orders.py:12: warning no-pre-derived-arguments: The call passes both lines and the context they come from. (confidence 0.70) [3f1c9a2b7d40]
```

A review stops judging after `review_time_limit_minutes`
([Settings](configuration.md#settings)). Each rule and file it didn't judge gets a
`judge_error` diagnostic at the rule's severity, as a failed judge call does, so an
unchecked `error` rule fails the review.

## The hooks

When an agent or subagent stops, the hook runs `codeguard review` in its working
directory: the uncommitted and untracked files, whoever changed them and however. The
hook runs the codeguard the plugin ships, not one on your PATH. Claude Code and Codex get
the same behaviour. [Troubleshooting](using-codeguard.md#troubleshooting) covers a hook
that doesn't run.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed judge call or the time limit).
  The hook passes `--judge-errors-as-warnings`, since the agent can't fix those; CI still
  fails on them, unless the PR has the
  [`codeguard-allow-judge-errors` label](using-codeguard.md#merge-a-pr-despite-a-judge-error).
- The hook passes `--skip-ci-only`, so [`ci_only` rules](configuration.md#rule-package-keys)
  don't run. CI doesn't, so they still run there.
