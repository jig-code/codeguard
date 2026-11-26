---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if no clause in the statement lets code keep the rule when the rest of the statement forbids that code. A clause that only describes the forbidden code more precisely narrows what the statement forbids and exempts nothing.
FAIL if the statement is missing or empty. Also FAIL if the statement forbids some code and then a separate clause lets part of that code keep the rule.
