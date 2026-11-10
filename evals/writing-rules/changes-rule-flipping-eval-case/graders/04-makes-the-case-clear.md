---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

The case this grader is about is the one the prompt names, whose handler logs the exception and then re-raises it, whatever the case is named now.

PASS if that case is gone from this rule eval, or it is still there and a reader of the case alone sees, beyond argument, why its code gets the outcome the case expects.
FAIL if that case is still in this rule eval and a reader of the case alone could argue that its code gets an outcome other than the one the case expects.
