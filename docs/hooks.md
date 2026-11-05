# What the hooks check


When an agent or subagent stops, the hook runs `codeguard review` in its working
directory: the uncommitted and untracked files, whoever changed them and however. Start
the session in the repository's directory and make changes from there. Claude Code reads a
project's hooks only from the directory a session starts in, and a cloud session over several
repositories starts above them, where no repository's hooks run. It runs the codeguard
the plugin ships, not one on your PATH. Claude Code and Codex get the same behaviour.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed. When the agent can't fix one, interrupt it
  and fix the rule.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed `claude` call or the time
  limit). The hook passes `--judge-errors-as-warnings`, since the agent can't fix those;
  CI still fails on them unless the PR has the `codeguard-allow-judge-errors` label.
- Rules the config marks `ci_only` don't run: the hook passes `--skip-ci-only`. CI
  doesn't, so they still run there ([Rules](configuration.md#rules)).
- If the review crashes or uv can't build codeguard's environment, you see why, and the
  stop goes through.

In Claude Code, a second hook guards the rules themselves. Before an `Edit` or `Write` to
a rule file (a skill, pattern rule, gate, binding, rule test or rule eval, under
`.codeguard/` or a package ruleset's directory), it checks the session's transcript for
the `writing-rules` skill: a Skill call naming it, or a Read of its `SKILL.md`. Until the
session has loaded it, the edit is denied with a message telling the agent to load it. A
transcript the hook can't read lets the edit through.

The judge gets the code the change touched: each changed function or method, with its
decorators; each changed statement outside them, whole, with the header and decorators of
the class it's in; for a changed `elif`, `else`, `except` or `finally` line, just that
clause, with the `try` block an `except` guards; each class whose header changed, whole;
each changed comment or docstring line alone; and, for each of the rule's
triggers, the whole of each node of that kind around a changed line of code, so the judge
sees the code that made the rule apply. Removed lines are sent with the code the change
kept around them, the same way: the function or method they were in, the header of their
class, the rest of a statement they were part of, or the header of the statement whose
block they were in (for a removed `except`, its `try` and the block it guarded), never the
code beside them. A renamed file is compared with the file it was renamed from. Unless
a class's header changed, its other members aren't sent, though the judge can read them.
What is sent is what the judge has to read to decide; anything it only might need, it
reads itself.
Lines carry the file's line numbers; added and changed lines are marked `+`, and the
lines git's diff shows the change removed are marked `-`. A new file is sent whole but
for its blank lines outside a function or method; every file with `--all` is sent whole,
all of it marked changed. The judge reads the rest of the file, or any other file in the
repository, with its read-only tools.

A review reports only violations a changed or removed line is part of, on that line. What the line
held before doesn't matter: editing a line that already broke a rule reports it, so code
a change touches is left better than it was found. Untouched code isn't reported, even in
the function or class around the change: adding a line to a method doesn't report the
method's name, and renaming a variable doesn't report the class's design. A changed line
that breaks a rule together with the code around it is reported, such as a method that
gives its class another responsibility. Other functions and classes in the file, and the
other blocks of a statement around the change, such as the `except` of a `try` whose
body changed, are read as context but never reported. A verdict is cached until the changed code, the
rest of the file, the rule, the model, or a file the judge loaded changes. A loaded file
is one the judge read, or one its searches returned: a file a grep matched or a glob
listed. A file a search would only start returning later doesn't count.

The judge gives a reason with every verdict, pass or fail: one sentence saying what in
the changed code keeps the rule or breaks it. It is context for whoever reads a
rule eval, which prints it for every case ([The rule eval](rule-packages.md#the-rule-eval)); a review prints each
violation's message.

The judge rates its confidence in each violation on a fixed scale, and the model can
answer with no other value:

| Confidence | What it says |
|---|---|
| 1.0 | The judge is certain: what the code does is what the rule forbids, and nothing in the working directory points to an exception the rule allows. |
| 0.9 | The code breaks the rule as written, but the verdict rests on a reading of the rule's terms a reviewer could contest. |
| 0.7 | The code probably breaks the rule, but something in the working directory points to an exception it allows. |
| 0.5 | The code is as likely to follow the rule as to break it. |

An error below the
threshold is reported as a warning, with its confidence, and doesn't block. The
threshold defaults to 0.9; set it in `.codeguard/config.yaml`:

```yaml
confidence_threshold: 0.8
```

A judged diagnostic prints its confidence, so a warning shows how far it fell short:

```
app/orders.py:12: warning no-pre-derived-arguments: The call passes both lines and the context they come from. (confidence 0.70) [3f1c9a2b7d40]
```

A review stops judging after 5 minutes. Each rule and file it didn't judge gets a
`judge_error` diagnostic at the rule's severity, so an unchecked `error` rule fails the
review. A failed judge call does the same.
The GitHub Action stops the review 2 minutes after the limit, in case it hangs. Change the
limit in `.codeguard/config.yaml`:

```yaml
review_time_limit_minutes: 10
```

In a review, each judge rule is judged with its binding's provider and model, else the
project's default, else the package's, and with none the `claude` CLI with no
`--model`, so the CLI's own default; see [Configure the judge](configuration.md#configure-the-judge).
