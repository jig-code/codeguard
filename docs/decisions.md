# Decisions

Standing answers to questions about working on codeguard that would otherwise go to a
maintainer. Each record states the decision as plain statements, and a Why when the
decision came with a reason. A decision that replaces an earlier one replaces the record.
The current design is in [architecture](architecture.md).

## 1. codeguard doesn't run inside Claude Code's sandbox

- codeguard has no support for running inside Claude Code's sandbox, and no hook is added to build its environment there.

Why: it was only needed because of the old testing approach, and under the testing guide nothing needs codeguard to run inside the sandbox.

## 2. A requirement a codeguard rule enforces lives in that rule

- A requirement that a codeguard rule enforces on codeguard lives in that rule.
- `docs/architecture.md` names the rule instead of restating the requirement.

Why: a requirement lives in one place, so the rule and the doc can't drift.
