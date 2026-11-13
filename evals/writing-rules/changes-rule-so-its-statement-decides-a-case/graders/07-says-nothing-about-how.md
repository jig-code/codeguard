---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement has no clause beside what it forbids that names how code avoids the forbidden thing. A clause that only narrows what the statement forbids does not name how. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if the statement has a clause beside what it forbids that names how code avoids the forbidden thing.
