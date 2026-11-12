---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement meets both of these checks. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
1. The statement names no action that code must take to avoid what that code must never do. A clause that only narrows what the statement forbids is not an action.
2. The statement states neither the harm the rule prevents nor any other why.

FAIL if the statement is missing or empty. Also FAIL if the statement names an action that code must take to avoid what that code must never do. "Without" followed by a verb, "fail to", "skip" and "leave" with "undone" each name such an action. Also FAIL if the statement states the harm the rule prevents or any other why.
