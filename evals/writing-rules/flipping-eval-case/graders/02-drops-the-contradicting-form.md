---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

This SKILL.md no longer makes the exception type caught part of the convention: it does not list catching Exception or a bare except as a form that breaks the rule, and it does not carve such a catch out as an allowed exception either. The rule is one convention about not losing the failure; the broad catch is dropped from it or moved to a rule of its own.
