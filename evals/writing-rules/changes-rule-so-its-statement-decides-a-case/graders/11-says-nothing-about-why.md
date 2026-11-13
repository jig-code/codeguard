---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if, beside what the statement forbids, no clause gives a reason for the convention or a consequence of breaking it. A clause that names who the forbidden thing affects is part of what the statement forbids, not a why. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if a clause gives a reason for the convention, such as a "because" or "so that" clause. Also FAIL if a clause names what goes wrong when code breaks the convention.
