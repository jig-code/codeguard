---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

The convention is: code never swallows an exception.
The case to look for is the one for a handler that logs the error and re-raises it.
PASS if this rule eval has no such case. Also PASS if a reader of that case alone can see whether its code keeps or breaks that convention.
FAIL if this rule eval is missing or empty. Also FAIL if a reader of that case alone could judge its code either way against that convention.
