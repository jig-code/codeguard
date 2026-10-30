---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

Every case name in this rule eval gives the reason its code breaks or keeps the rule, not only what the code does. A name gives the reason when it says what goes wrong because of the code, or whether the code has the thing the rule forbids (here, a created flag returned beside the result), or why the judge never sees it. A name that only describes the code, such as "returns a dict" or "calls get_or_create", gives no reason.
