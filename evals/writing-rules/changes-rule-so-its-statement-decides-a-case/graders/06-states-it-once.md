---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

PASS if the statement names what it forbids once. A phrase that spells out the forbidden thing in other words names the forbidden thing again, even where it follows directly. A clause that names what code does instead of the forbidden thing does not name the forbidden thing again. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement names what it forbids a second time, in other words or in the negative.
