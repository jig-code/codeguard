---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`.

PASS if the convention's statement doesn't make a call to a framework's own get-or-create API, such as Django's get_or_create, a violation, whether the calling code uses the created flag that call returns or discards it.
FAIL if not: for example the statement flags any call that returns a created flag, or flags code for unpacking the flag a framework call returns.
