---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

No case in this rule eval has a second defect besides its one point. A second defect is code that:

- fails on input it's meant to handle, such as an unchecked split or index, or a parse that raises;
- does something its name doesn't say, such as a get_, find_, load_ or is_ function that creates or writes, an ensure_ function that never creates, or a retry that can repeat a side effect;
- returns a value its name or annotation contradicts.

Nothing else is a second defect: not a missing annotation, an unused helper, a comment's wording, a lookup that raises when the row is missing, or a race between a lookup and a create. A helper a case calls without defining it is not a second defect.
