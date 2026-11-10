---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The caught-type form is a handler that catches `Exception` or is a bare `except`.

PASS if this SKILL.md doesn't keep the caught-type form as a violation beside its statement, and has no clause saying the rule ignores the type of exception a handler catches.
FAIL if this SKILL.md keeps the caught-type form as a violation beside its statement, in a list, a section or its Why, or has a clause saying the rule ignores the type of exception a handler catches.
