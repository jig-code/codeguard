---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if this SKILL.md states its convention as one declarative sentence in words a reviewer would use, followed at most by one sentence that fixes the meaning of a term in it a reader could take two ways, and that sentence decides each piece of code itself.
FAIL if the convention is a question, is spread over several sentences that each add a requirement, uses a term nobody would use in a code review, or points at a list of code shapes instead of deciding them.
