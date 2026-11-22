---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

PASS if the text is one sentence. The text is everything under this rule file's `#` title and before its first `##` section, leaving out the title.
FAIL if the text is missing or empty. Also FAIL if the text runs to a second sentence. Also FAIL if the text is a list.
