---
type: regex
target: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
pattern: '^\s*-\s*name:\s*["'']?(?:[Rr]eturn(?:s|ing)?|[Cc]all(?:s|ing)?|[Bb]uild(?:s|ing)?|[Aa]dd(?:s|ing)?|[Ee]dit(?:s|ing)?|[Ww]rap(?:s|ping)?|[Uu]npack(?:s|ing)?|[Dd]eclar(?:es|ing)|[Pp]ass(?:es|ing)?|[Uu]s(?:es|ing)|[Dd]efin(?:es|ing)|[Cc]hang(?:es|ing)|[Rr]emov(?:es|ing)|[Cc]reat(?:es|ing)|[Hh]and(?:s|ing)|[Ff]unction|[Mm]ethod|[Ss]ignature|[Aa]nnotated|[Uu]nannotated)\b'
flags: m
match: not_contains
weight: 1
---
