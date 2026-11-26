---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement, and read the `## Why` section only for the harm it names. A limit is a part of the statement that leaves some code out of what it forbids.
PASS if every limit in the statement leaves out only harmless code, by the harm that the `## Why` section names. A statement with no limit passes.
FAIL if the statement or the `## Why` section is missing or empty. Also FAIL if a limit in the statement leaves out code that does the harm that the `## Why` section names.
