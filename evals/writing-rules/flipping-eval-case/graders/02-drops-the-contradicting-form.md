---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if this SKILL.md no longer mentions the type of exception a handler catches, such as a broad `except Exception` or a bare `except`, either as a shape that breaks the convention or as one allowed to keep it.
FAIL if the SKILL.md still names a caught exception type as a violation, or carves one out as an allowed exception to the convention.
