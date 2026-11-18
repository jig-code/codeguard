# Decisions

The standing choices about codeguard that govern future work and that the code and docs don't
show on their own. Each record states the decision as plain statements, and a Why when the
decision came with a reason. A decision that replaces an earlier one replaces the record. The
current design is in [architecture](architecture.md).

## 1. codeguard has no sandbox support

- codeguard has no hook that builds it to run inside Claude Code's sandbox.

Why: it was only needed because of the old testing approach, and under the testing guide nothing needs codeguard to run inside the sandbox.

## 2. Evals run on pull requests, not on pushes to main

- Evals gate pull requests. They do not run again on pushes to main.

Why: re-running them after a merge spends model calls on what the pull request already judged.

## 3. The judge gets a standard unified diff

- The judge is sent the change as a git unified diff with function context, never an excerpt codeguard builds itself.

Why: a custom excerpt reinvents diffs, and function context appears with the change as it does in a GitHub review.

## 4. Gemini runs on Standard PayGo credits, 10 calls at once

- The default for Gemini calls at once is 10.
- Priority PayGo, a custom tier and Provisioned Throughput through sales are ruled out. Gemini stays only if Standard PayGo on credits gives acceptable throughput, and otherwise another provider is used.

Why: 10 keeps the peak inside the documented 500K tokens-per-minute tier, which matters on credits-only Standard PayGo.

## 5. codeguard runs claude through the Agent SDK

- codeguard runs `claude` through the Agent SDK instead of parsing `stream-json`.
- The Agent SDK only runs `claude`. Agent SDK tools and the Messages API stay rejected for searches.

Why: `stream-json` isn't documented as stable.

## 6. codeguard keeps private rules for dogfooding

- codeguard ships no public rules, but it keeps private rules for dogfooding. The first is a rule that enforces the architecture's judge contract against the judge prompt.
- This bends the invariant that the framework has no rules built in. The exception is recorded as a decision when the work starts.

## 7. A requirement a codeguard rule enforces lives in that rule

- A requirement that a codeguard rule enforces on codeguard lives in that rule.
- `docs/architecture.md` names the rule instead of restating the requirement.

Why: a requirement lives in one place, so the rule and the doc can't drift.
