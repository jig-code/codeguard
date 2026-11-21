---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if every clause of the statement describes what the code that the statement forbids itself does. A clause that names who that code affects, or how that code behaves, is part of what the statement forbids. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if a clause says why the convention exists. Also FAIL if a clause names an outcome that follows once the forbidden code has run.
