---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement gives no why. A why is a reason or a harm that the statement gives for the convention. What the statement forbids is not a why. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if the statement gives a reason for the convention. Also FAIL if the statement gives a harm that the convention prevents.
