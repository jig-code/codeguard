# codeguard

[README.md](README.md) explains the CLI, rule packages and how to work on codeguard.

## Design

Before changing the judge (its template, its prompt, its tools or what it's given), the
review pipeline, or anything an invariant covers, read
[docs/architecture.md](docs/architecture.md) and check the change against it. A change
that conflicts with it needs Craig's decision first.

## Testing

Before testing any change, follow [docs/testing.md](docs/testing.md).

- Run only the checks the change's row names. Never write a script, a copy of the
  repository or a workaround to test a change some other way.
- If a change fits no row, or a listed check can't run, say so and propose a change to
  the guide; don't change the guide without approval.

## Rules

Before adding or changing a rule, and whenever a rule eval, an LLM test or a judged
review fails, flips between runs or reports a warning, follow
[skills/writing-rules/SKILL.md](skills/writing-rules/SKILL.md). This covers the LLM
tests' fixtures in `evals/judge`, every rule package, and judged reviews of codeguard's
own code.
