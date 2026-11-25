# Every rule

## What every rule must be

- Write every part of a rule in plain, clear words that a developer new to the project
  understands on the first read.
- Put a rule's files in the project's `.codeguard/` directory. A rule package is a
  repository with `codeguard-package.yaml`, and groups its rules in rulesets, one
  directory each. In a rule package, put the files in the ruleset's directory. 
  `judge-rules.md` and `pattern-rules.md` give each file's path inside `.codeguard/` or
  the ruleset's directory.
- Write one rule for each convention in the request.
- Before writing a rule, read the project's own rules and the rulesets that
  `.codeguard/config.yaml` opts into.
- Make sure that code that another rule requires keeps the new rule.
- Make sure that code that breaks another rule keeps the new rule. When code would break
  both rules, narrow one of them until that code keeps it, or merge the two rules.
- Make sure that idiomatic code, written the way the language and its libraries intend,
  keeps the rule. Code isn't idiomatic in the project just because a framework's own
  code does the same.
- Name a particular thing in the project only when the convention is about that one
  thing. For a convention about many, describe what they have in common.
- Give every rule a why: the harm the rule prevents, in one or two sentences, so that
  whoever later changes the project's code or design can tell whether the rule still
  holds.
- Set `severity: error` on a rule when codeguard must block the coding agent and fail
  CI on code that breaks it. With `severity: warning`, codeguard only reports that code
  to the user.
- To change a rule from a ruleset for this project, override or exclude it in
  `.codeguard/config.yaml`. Never copy it into `.codeguard/`.

## Cases

A case is a pattern rule's test case or a judge rule's eval case.

- Use made-up code and names, so that a case shows the convention rather than one class
  in the codebase. A public rule package never holds code copied from a private
  repository.
- Give idiomatic code a `valid` case.
- Give each eval case a `name` that says only the situation that it tests, unique
  within its file. State the expected outcome once: in an eval case's
  `expected_output`, or by the `valid` or `invalid` list that a test case is in.
- Before writing a case, say in one sentence what its code does. If another case already
  has that sentence, don't write the case. Two cases whose code breaks or keeps the rule
  in the same way are one case, however their syntax or names differ: keep the clearer
  one. Two `valid` cases differ only when their code keeps the rule in different
  situations.
- Make each case break the rule in one way at most: the way that it tests. Read every
  other line of the case as a reviewer would, and rewrite any line that is wrong for
  another reason.
