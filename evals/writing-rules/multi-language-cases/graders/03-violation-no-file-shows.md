---
type: llm
focus: { source: file, path: ".codeguard/rule-evals/derive-known-values.yaml" }
weight: 1
---

The rule eval has an invalid TypeScript case (file ending in .ts or .tsx) whose hand-written copy of the values uses a construct that neither SKILL.md nor typescript.md shows. SKILL.md shows a list, set, tuple, union type and the keys of a mapping; typescript.md shows a union type and a written-out array. So the copy is none of those, even wrapped in something else: an includes() check over a written-out array, a Set or z.enum built from a written-out array, or a Record keyed by a written-out union all count as shown. Constructs that qualify include the cases of a switch statement, a chain of === comparisons, or a regular expression listing the values.
