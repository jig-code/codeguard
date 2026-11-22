---
type: llm
focus: { source: file, path: .codeguard/rule-evals/exception-handling.yaml }
weight: 1
---

The agent was asked for a codeguard rule, and this is the rule eval it wrote. Each case has a `name` and, under `expected_output`, an `outcome` that holds the case's verdict.
This check reads only the `name` lines.
PASS if each case's name says only what the case's code does or the situation the case tests.
FAIL if the file is missing or empty. Also FAIL if a case's name holds the case's outcome, or says whether the case's code keeps or breaks the rule.
