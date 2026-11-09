---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if this SKILL.md doesn't mention the type of exception a handler catches, such as a broad `except Exception` or a bare `except`, anywhere.
FAIL if it does: for example it names a caught exception type as a violation, carves one out as allowed, or mentions one in its Why.
