---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

The convention is: code never swallows an exception.
PASS if this rule eval has no case for a handler that logs the error and re-raises it. Also PASS if this rule eval keeps the case for a handler that logs the error and re-raises it, and a reader of that case alone can see whether its code keeps or breaks that convention.
FAIL if this rule eval is missing or empty. Also FAIL if this rule eval keeps the case for a handler that logs the error and re-raises it, and a reasonable reviewer could judge that case's code either way against that convention.
