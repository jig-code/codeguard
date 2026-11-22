---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

PASS if the statement states what the code that the statement covers must never do. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement states what code must do instead of what that code must never do. Also FAIL if the statement tells its reader what to do, such as a sentence that starts with "Flag", "Report" or "Check", instead of stating what code must never do.
