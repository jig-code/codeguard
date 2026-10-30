---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

No case in this rule eval has a second defect besides its one point. A second defect is code that:

- parses text and fails on text that isn't in the expected form, such as an unchecked split or index of its parts;
- does something its name doesn't say, such as a get_, find_, load_ or is_ function that creates or writes, an ensure_ function that never creates, or a retry that can repeat a side effect;
- returns a value its name or annotation contradicts, such as a function named for a width that returns two bounds.

Nothing else is a second defect: not a missing annotation, an unused helper, a comment's wording, a lookup that raises when the row is missing, a call that raises on an empty collection, a race between a lookup and a create, or a name the case uses without importing or defining it.
