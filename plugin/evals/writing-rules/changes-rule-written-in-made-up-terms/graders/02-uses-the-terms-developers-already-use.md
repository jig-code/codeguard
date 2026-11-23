---
type: llm
focus: { source: file, path: .codeguard/rules/judge/package-public-interface.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if every term in the statement is one developers commonly use for the thing it names.
FAIL if the statement is missing or empty. Also FAIL if the statement names something with a term it made up, or with a word in a sense developers wouldn't recognize.
