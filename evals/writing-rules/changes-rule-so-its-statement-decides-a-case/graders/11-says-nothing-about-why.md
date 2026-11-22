---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if, beside what the statement forbids, no clause gives a reason for the convention or a consequence of breaking it. A clause that names who the forbidden thing affects is part of what the statement forbids, not a why.
FAIL if the statement is missing or empty. Also FAIL if a clause gives a reason for the convention, such as a "because" or "so that" clause. Also FAIL if a clause names what goes wrong when code breaks the convention.
