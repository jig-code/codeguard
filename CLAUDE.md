# codeguard

[README.md](README.md) introduces codeguard and links its docs by reader;
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) explains how to work on codeguard.

## Design

Before changing the judge (its template, its prompt, its tools or what it's given), the
review pipeline, or anything an invariant covers, read
[docs/architecture.md](docs/architecture.md) and check the change against it. A change
that conflicts with it needs the maintainers' approval before it's made.

## Testing

Before testing any change, follow [docs/testing.md](docs/testing.md).

- Run only the tests the change's row names. Never write a script, a copy of the
  repository or a workaround to test a change some other way.
- If a change fits no row, or a listed test can't run, say so and propose a change to
  the guide; don't change the guide without approval.

## Python

Before writing, editing or reviewing any `.py` file, tests included, load the
`python-code-quality` skill
([.claude/skills/python-code-quality/SKILL.md](.claude/skills/python-code-quality/SKILL.md)).

## Rules

Before writing or editing the writing-rules skill or its evals, read
[docs/skill-evals.md](docs/skill-evals.md); every change traces to an item
in it.

Before adding or changing a rule, follow
[plugin/skills/writing-rules/SKILL.md](plugin/skills/writing-rules/SKILL.md). Whenever a rule eval, an
LLM test or a judged review fails, flips between runs or reports a warning, follow the
Rule failures bullet in [docs/architecture.md](docs/architecture.md#testing-a-rule) and
[docs/testing.md](docs/testing.md). This covers the LLM
tests' fixtures in `evals/judge`, every rule package, and judged reviews of codeguard's
own code.
