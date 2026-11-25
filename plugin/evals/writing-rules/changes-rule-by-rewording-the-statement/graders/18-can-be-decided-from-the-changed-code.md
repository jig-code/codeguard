---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if whether code keeps or breaks the statement can be decided from the code a change adds or edits, the function, class and module around that code, and the definitions of the names that code uses. Also PASS if the statement is about something staying unique or consistent across the repository.
FAIL if the statement is missing or empty. Also FAIL if deciding whether code keeps or breaks the statement needs other code in the repository, and the statement is not about something staying unique or consistent across the repository.
