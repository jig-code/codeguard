---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

No case in this rule eval has a second defect, in its `before` or its `after` code, besides its one point. A second defect is code that:

- parses text and fails on text that isn't in the expected form, such as an unchecked split or index of its parts;
- does something its name doesn't say: a function named for reading, such as get_, find_, load_ or is_, that creates or writes; a function whose name says it creates, such as ensure_ or one named "or create" or "or add", that never creates; or a retry that can repeat a side effect;
- returns a value its name or annotation contradicts, such as a function named for a range that returns one number.

Nothing else is a second defect: not a missing annotation, an unused helper, a comment's wording, a lookup that raises when the row is missing, a call that raises on an empty collection, a race between a lookup and a create, a name the case uses without importing or defining it, or a function named for creating, such as register_ or issue_, that returns the existing object when there is one.
