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
directory: the uncommitted and untracked files, whoever changed them and however. Start
the session in the repository's directory and make changes from there. Claude Code reads a
project's hooks only from the directory a session starts in, and a cloud session over several
repositories starts above them, where no repository's hooks run. The hook runs the codeguard
the plugin ships, not one on your PATH. Claude Code and Codex get the same behaviour.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed. When the agent can't fix one, interrupt it
  and fix the rule.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed `claude` call or the time
  limit). The hook passes `--judge-errors-as-warnings`, since the agent can't fix those;
  CI still fails on them ([judge errors in CI](add-codeguard.md#ci)).
- The hook passes `--skip-ci-only`, so [`ci_only` rules](configuration.md#rule-package-keys) don't
  run.
- If the review crashes or uv can't build codeguard's environment, you see why, and the
  stop goes through.

In Claude Code, a second hook guards the rules themselves. Before an `Edit` or `Write` to
a rule file (a skill, pattern rule, gate, binding, rule test or rule eval, under
`.codeguard/` or a package ruleset's directory), it checks the session's transcript for
the `writing-rules` skill: a Skill call naming it, or a Read of its `SKILL.md`. Until the
session has loaded it, the edit is denied with a message telling the agent to load it. A
transcript the hook can't read lets the edit through.
