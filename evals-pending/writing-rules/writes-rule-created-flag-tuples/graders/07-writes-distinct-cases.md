---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

This rule eval has at most four invalid cases and at most four valid cases, and no two cases test the same situation: no two invalid cases break the convention in the same way, and no two valid cases keep it in the same way. Two valid cases keep it in different ways when the code is in different situations (one consumes a framework's pair and returns a single value, another returns a pair that is not a created flag), even though both lack the violation. Differences only in syntax, names or annotations don't make two situations. One invalid case is enough when the convention can be broken in one way.
