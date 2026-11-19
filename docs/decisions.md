# Decisions

Architectural, design and development decisions for codeguard that an agent working on it
would otherwise have to ask a maintainer about. Each record states the decision as plain
statements, and a Why when the decision came with a reason. A decision that replaces an
earlier one replaces the record. The current design is in [architecture](architecture.md).

## 1. codeguard doesn't run inside Claude Code's sandbox

- codeguard has no support for running inside Claude Code's sandbox, and no hook is added to build its environment there.

Why: it was only needed for the old testing approach, and under the testing guide nothing needs codeguard inside the sandbox.

## 2. An internal error is visible and never stops all work

- An internal error is visible and never stops all work.
- Locally, judge errors go to the developer and never to the agent, and rule errors still block every stop.
- In CI a judge error fails the review unless the per-PR label bypasses it.

Why: a broken hook would stop all work, and the agent can't fix judge errors.

## 3. Low-confidence findings go to the user, not the agent

- Low-confidence findings go to the user and not to the agent.

Why: sending them to the agent continues the turn, so they would act as a block.

## 4. Each rule is judged in its own request

- Each rule is judged in its own judge request. Several rules never go into one request.

## 5. The judge decides what it reads

- The judge prompt describes the context and the tools. The judge decides from the rule what to read.
- The prompt never tells the judge what to read.

## 6. The judge never proposes fixes

- The judge reports violations only.

Why: fix notes stalled the rule fixes.

## 7. Confidence is the judge's assessment of its own accuracy

- Confidence is the judge's assessment of how accurate its verdict is. Reading other code never lowers it.

Why: confidence is about how certain the verdict is after reading whatever was needed.

## 8. No orchestrating agent runs a review

- No orchestrating agent runs a review.

Why: an orchestrator picks what to spawn.

## 9. Which judge runs is configuration

- The `claude` CLI is for local work. CI never uses a subscription or a CLI tool.
- Which judge runs is configuration, never code that knows the surface.

Why: the effort to switch models should be minimal, and one or two config values should swap the judge for the whole system.

## 10. Only the judge's settings come from the environment

- Only the judge's settings come from the environment. Every other setting comes from the committed config.

Why: codeguard has no template language of its own and no shell-style fallback code.

## 11. A model is named once and its provider is never inferred

- A model is named once.
- A provider is never inferred from a model name.
- A codeguard variable names no provider.

Why: a provider is a configuration detail that names shouldn't leak.

## 12. codeguard owns the environment variables its judges use

- The judges use variables that codeguard owns, never the provider's own environment variables.

Why: otherwise a user can't give codeguard different credentials from the provider's own tools.

## 13. Only the current Gemini model is supported

- codeguard supports only the current Gemini model.

Why: the current model is more reliable and cheaper, and older ones needn't be supported.

## 14. A timed-out judge request is never re-sent

- A judge request that times out is not re-sent.

Why: re-sending blocks CI for minutes, and calls that regularly take over 60 seconds mean something is wrong.

## 15. codeguard doesn't enforce that a skill is loaded

- codeguard doesn't enforce that a skill is loaded.
- Prevention is a future enhancement.

Why: enforcing a skill load is out of scope and not important.

## 16. The judge is sent a standard unified diff with function context

- The judge is sent a change as a standard unified diff with function context, never an excerpt codeguard builds itself.

Why: a custom excerpt reinvents diffs, and context with the change is how GitHub reviews work.

## 17. A violation names a range of lines

- A violation names a range of start and end lines.

Why: architecture rules are often violated by more than one line.

## 18. codeguard keeps private rules for dogfooding

- codeguard keeps private rules for dogfooding, though it ships no public rules.

## 19. Evals run on pull requests, not on pushes to main

- Evals run only on pull requests, not on pushes to main.

Why: re-running them after a merge spends model calls the pull request already spent.

## 20. The writing-rules skill only writes the rule

- The writing-rules skill holds only how to write the rule.
- It holds no running of tests or evals, and no examples.

Why: the skill writes the rule, and the evals verify the rule follows the skill.

## 21. Duplicated skill-eval graders stay copies

- Each skill-eval case keeps its own copy of a duplicated grader.
- A CI check compares the copies.

Why: the eval tool has no shared graders.

## 22. An advisory rule check is not a pydantic validator

- A fact about a rule lives on the rule type.
- A thin validation reads it and applies warn, fail or off.
- An advisory rule check is not a pydantic validator.

Why: a validator only passes or fails, so it can't warn.
