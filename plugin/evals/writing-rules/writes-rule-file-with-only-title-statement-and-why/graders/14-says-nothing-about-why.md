---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Judge only the statement: leave out the title and the `## Why` section.
PASS if, beside what the statement forbids, no clause gives a reason for the convention or a consequence of breaking the rule. A clause that names who the forbidden thing affects is part of what the statement forbids, not a reason.
FAIL if the statement is missing or empty. Also FAIL if a clause gives a reason for the convention. Also FAIL if a clause names what goes wrong when code breaks the rule.
