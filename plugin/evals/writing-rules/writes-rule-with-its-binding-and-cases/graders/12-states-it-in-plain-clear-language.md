---
type: llm
focus: { source: file, path: .codeguard/rules/judge/exception-handling.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if every phrase in the statement has one meaning, and every word is one developers commonly use.
FAIL if a phrase in the statement has more than one possible meaning. Also FAIL if a word or pronoun could refer to more than one thing, or if the statement uses a word developers don't commonly use.
