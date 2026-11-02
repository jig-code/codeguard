---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

Every case in this rule eval holds its one point and no other code a reviewer could question. Any other code that might be a defect is a second defect, such as a parse that raises on input it should handle or a function named as a check that writes. If any line besides a case's point might be a defect, even arguably, the eval fails: when unsure, fail. A helper a case calls without defining it is not a second defect.
