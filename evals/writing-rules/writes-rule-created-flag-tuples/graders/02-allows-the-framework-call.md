---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`.

PASS if the convention's statement doesn't make a call to a framework's own get-or-create API, such as Django's get_or_create, a violation in code that returns only the object, whether that code reads the created flag the call returns or ignores it.
FAIL if the convention's statement makes code that returns only the object a violation for calling a framework's own get-or-create API, for reading the created flag that call returns, or for ignoring it.
