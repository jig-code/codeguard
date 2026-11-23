# Choosing a tool

codeguard adds the checks a project's static analysis tools can't do. Decide by what
decides a violation, not by how the convention is worded.

If a static analysis tool other than codeguard can check the convention, directly,
through its configuration or with a custom rule, the convention isn't codeguard's,
whether or not the project runs that tool. Such a tool gives the same answer every run,
costs nothing and runs in the editor. A tool setting that closes a way around the tool
counts too. Write no rule, and say that the convention isn't codeguard's to check.

A pattern rule is for a shape in one file that those tools can't express.

A judge rule is only for what needs judgment, never for what syntax, types or a search of
the repository decide. A judge rule is decided from the changed code, so it can only
guess what a search would find.
