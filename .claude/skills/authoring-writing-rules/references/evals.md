# Writing the skill's evals

The evals are the cases in `plugin/evals/writing-rules/`, which run with
`claude plugin eval`.
[Testing codeguard](../../../../docs/testing.md#the-skill-evals) says how and when to run
them. Each case asks an agent with the skill for a codeguard rule, and grades what the
agent does against what the skill tells it to do.

## Cases

Test only the skill, which covers only writing the rule. Never check whether a rule the
agent writes works, what verdict codeguard would give on any code, or whether its rule
tests or rule evals pass. When the agent declines a rule, never check what it says about
the other tool or whether it sets that tool up.

- Write a case the agent can finish with `Write` and `Edit` alone. The evals never give it
  `Bash`, so it never runs codeguard.
- Write the prompt as a person would ask for a rule, a new one or a fix to an existing
  one, and name the files the agent needs.
- Give each case one right answer that two reviewers reading the agent's output agree on.
- Target one instruction per case. An instruction that applies to every rule gets a case
  of its own, not a grader in every case.

## Graders

- Give every case result graders, and a `tool_used: Skill` grader that passes when the
  agent loads the writing-rules skill.
- Make the result graders check only the instruction the case targets.
- Make each result grader read one output and check one thing about it. The output is a
  file the agent wrote, whether the agent wrote any rule file, or, in a case that
  declines a rule, the agent's final reply.
- Check structure with a `regex` grader, whose pattern is short enough to verify at a
  glance. Split a structure that needs a longer pattern into several `regex` graders, each
  checking one part of it.
- Judge what prose says with an `llm` grader, since a pattern breaks on wording that does
  what the skill asks. Give it short text to read: a judge's verdict varies between runs,
  and varies more the longer the text.
- Write an `llm` grader's rubric as concrete `PASS if` and `FAIL if` conditions that hold
  everything the judge needs to decide. Make a `FAIL if` cover a missing or empty output,
  and leave the output's formatting out of the verdict.
- Give a grader no examples and no lists of words to match: an example narrows the judge
  to what it shows, and a list decides only the words it names.
- Before a new or changed `llm` grader counts, read its verdicts and the output it judged
  on a few runs. A small judge can mark a correct answer wrong.
- Never change a grader because of its verdicts in runs without the plugin.

## Names

Name cases and graders so the names alone say what each case tests:

- A case's directory is its expected outcome, then what only that case tests.
- Every case with the same outcome starts with the same outcome name.
- A grader's file is its number, then what the agent's output does.
