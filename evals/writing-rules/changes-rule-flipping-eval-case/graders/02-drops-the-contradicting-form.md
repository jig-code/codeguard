---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The type of exception a handler catches is the type its `except` clause names, such as `Exception`, or every type for a bare `except`. Calling a handler an except block or an except clause names no type.

PASS if this SKILL.md doesn't mention the type of exception a handler catches anywhere.
FAIL if this SKILL.md mentions a type of exception a handler catches, or a bare `except`, anywhere.
