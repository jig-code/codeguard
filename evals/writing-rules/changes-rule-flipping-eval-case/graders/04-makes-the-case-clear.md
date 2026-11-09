---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

The case this grader is about is the one whose handler logs the exception and then re-raises it with a bare `raise`, whatever the case is named.

PASS if that case is gone from this rule eval, or it is still there, expected `valid`, and its handler still logs the exception and re-raises it, with nothing in the case a reviewer could argue breaks the convention.
FAIL if not: for example that case is expected `invalid` or `skipped`, or its code was changed so that its handler no longer logs or no longer re-raises.
