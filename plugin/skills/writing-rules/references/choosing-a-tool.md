# Choosing a tool

codeguard adds the checks a project's static analysis tools can't do. Decide by what
decides a violation, not by how the convention is worded.

Write no codeguard rule for a convention that a static analysis tool can check, because
that tool gives the same answer every run. This holds even if the check needs a setting
or a custom rule, or the project doesn't run the tool. Say that the convention isn't
codeguard's to check.

A pattern rule is for a shape in one file that those tools can't express.

A judge rule is only for what needs judgment, never for what syntax, types or a search of
the repository decide. A judge rule is decided from the changed code, so it can only
guess what a search would find.
