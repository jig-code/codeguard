---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement has no clause beside what it forbids that names how code avoids the forbidden thing. A clause that only narrows what the statement forbids does not name how.
FAIL if the statement is missing or empty. Also FAIL if the statement has a clause beside what it forbids that names how code avoids the forbidden thing.
