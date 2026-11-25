---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if whether code keeps or breaks the statement can be decided from the code a change adds or edits, the function, class and module around that code, and the definitions of the names that code uses. Also PASS if the statement is about something staying unique or consistent across the repository. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if deciding whether code keeps or breaks the statement needs other code in the repository, and the statement is not about something staying unique or consistent across the repository.
