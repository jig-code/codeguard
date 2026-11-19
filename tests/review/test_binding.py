from codeguard.config import JudgeChoice, JudgeProvider
from codeguard.review import Binding, Bindings, Severity

RULE_NAME = "responsibility-placement"
JUDGE_RULE_FILE = f"rules/judge/{RULE_NAME}.md"


class TestBinding:
    def test_files_matching_its_paths_are_kept(self, make_binding):
        binding = make_binding(paths=("app/**/*.py",))

        files = binding.files(["app/a.py", "app/models/b.py", "scripts/c.py"])

        assert files == ["app/a.py", "app/models/b.py"]

    def test_files_matching_its_exclude_paths_are_left_out(self, make_binding):
        binding = make_binding(paths=("**/*.py",), exclude_paths=("**/test_*.py",))

        files = binding.files(["app/a.py", "app/test_a.py", "app/b.rb"])

        assert files == ["app/a.py"]

    def test_from_config_builds_the_binding_its_config_describes(
        self, directory, make_binding, make_binding_config, make_ruleset, make_judge_rule
    ):
        directory.write(JUDGE_RULE_FILE, make_judge_rule().text)
        judge = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="gpt-6-luna")
        config = make_binding_config(
            paths=("app/**",),
            exclude_paths=("tests/**",),
            severity=Severity.WARNING,
            triggers=frozenset({"fixture"}),
        )

        binding = Binding.from_config(RULE_NAME, config, make_ruleset(root=directory.root), judge)

        assert binding == make_binding(
            paths=("app/**",),
            exclude_paths=("tests/**",),
            severity=Severity.WARNING,
            triggers=frozenset({"fixture"}),
            judge=judge,
        )


class TestBindings:
    def test_from_rulesets_builds_each_binding_of_a_packaged_ruleset(
        self, directory, make_binding, make_ruleset, make_judge_rule
    ):
        directory.write(JUDGE_RULE_FILE, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(root=directory.root, name="example/python", package_judge=package)

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (make_binding(rule=f"example/python/{RULE_NAME}", judge=project),)

    def test_judge_override_judges_every_binding(
        self, directory, make_binding, make_ruleset, make_judge_rule
    ):
        directory.write(JUDGE_RULE_FILE, make_judge_rule().text)
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=directory.root)], JudgeChoice(), override
        )

        assert bindings == (make_binding(judge=override),)
