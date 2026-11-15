from codeguard.config import (
    JudgeChoice,
    JudgeProvider,
    RuleOverride,
    RulesetConfig,
    RulesetLoader,
)
from codeguard.review import Binding, Bindings, Severity

RULE_NAME = "responsibility-placement"


def write_judge_rule(tmp_path, text: str) -> None:
    (tmp_path / "rules/judge").mkdir(parents=True)
    (tmp_path / f"rules/judge/{RULE_NAME}.md").write_text(text)


class TestBinding:
    def test_files_matching_its_paths_are_kept(self, make_binding):
        binding = make_binding(paths=("app/**/*.py",))

        files = binding.files(["app/a.py", "app/models/b.py", "scripts/c.py"])

        assert files == ["app/a.py", "app/models/b.py"]

    def test_files_matching_its_exclude_paths_are_left_out(self, make_binding):
        binding = make_binding(paths=("**/*.py",), exclude_paths=("**/test_*.py",))

        files = binding.files(["app/a.py", "app/test_a.py", "app/b.rb"])

        assert files == ["app/a.py"]

    def test_from_config_has_its_exclude_paths(
        self, make_binding, make_binding_config, make_judge_rule
    ):
        config = make_binding_config(exclude_paths=("tests/**",))

        binding = Binding.from_config(RULE_NAME, config, make_judge_rule(), JudgeChoice())

        assert binding == make_binding(exclude_paths=("tests/**",))

    def test_preset_binding_matches_every_file(self, make_binding):
        binding = make_binding()

        files = binding.files(["a.py", "app/b.rb"])

        assert files == ["a.py", "app/b.rb"]

    def test_from_config_has_its_severity(self, make_binding, make_binding_config, make_judge_rule):
        config = make_binding_config(severity=Severity.WARNING)

        binding = Binding.from_config(RULE_NAME, config, make_judge_rule(), JudgeChoice())

        assert binding == make_binding(severity=Severity.WARNING)

    def test_from_config_has_its_judge(self, make_binding, make_binding_config, make_judge_rule):
        judge = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="gpt-6-luna")

        binding = Binding.from_config(RULE_NAME, make_binding_config(), make_judge_rule(), judge)

        assert binding == make_binding(judge=judge)


class TestBindings:
    def test_from_rulesets_builds_each_binding(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)

        bindings = Bindings.from_rulesets([make_ruleset(root=tmp_path)])

        assert bindings == (make_binding(),)

    def test_packaged_binding_is_named_by_its_ruleset(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)

        bindings = Bindings.from_rulesets([make_ruleset(root=tmp_path, name="example/python")])

        assert bindings == (make_binding(rule=f"example/python/{RULE_NAME}"),)

    def test_excluded_binding_is_dropped(self, tmp_path, make_ruleset, make_judge_rule):
        write_judge_rule(tmp_path, make_judge_rule().text)
        selection = RulesetConfig(exclude=(RULE_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_binding_left_out_of_include_is_dropped(self, tmp_path, make_ruleset, make_judge_rule):
        write_judge_rule(tmp_path, make_judge_rule().text)
        selection = RulesetConfig(include=("another-rule",))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_included_binding_is_kept(self, tmp_path, make_binding, make_ruleset, make_judge_rule):
        write_judge_rule(tmp_path, make_judge_rule().text)
        selection = RulesetConfig(include=(RULE_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, name="example/python", selection=selection)]
        )

        assert bindings == (make_binding(rule=f"example/python/{RULE_NAME}"),)

    def test_override_replaces_the_binding_fields(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        override = RuleOverride(paths=("app/**",), severity=Severity.WARNING)
        selection = RulesetConfig(rules={RULE_NAME: override})

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, name="example/python", selection=selection)]
        )

        assert bindings == (
            make_binding(
                rule=f"example/python/{RULE_NAME}",
                paths=("app/**",),
                severity=Severity.WARNING,
            ),
        )

    def test_override_replaces_the_excluded_paths(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        selection = RulesetConfig(rules={RULE_NAME: RuleOverride(exclude_paths=())})
        ruleset = make_ruleset(
            root=tmp_path, binding__exclude_paths=("tests/**",), selection=selection
        )

        assert Bindings.from_rulesets([ruleset]) == (make_binding(),)


class TestBindingsJudge:
    def test_package_default_judges_its_rules(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.BEDROCK, model="package-model")

        bindings = Bindings.from_rulesets([make_ruleset(root=tmp_path, package_judge=package)])

        assert bindings == (make_binding(judge=package),)

    def test_project_default_wins_over_the_package_default(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, package_judge=package)], project
        )

        assert bindings == (make_binding(judge=project),)

    def test_binding_wins_over_the_project_default(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            root=tmp_path,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.GEMINI, model="bound-model")),
        )

    def test_provider_and_model_each_come_from_the_first_level_naming_it(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        package = JudgeChoice(model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK)
        ruleset = make_ruleset(root=tmp_path, binding__model="bound-model", package_judge=package)

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.BEDROCK, model="bound-model")),
        )

    def test_project_model_runs_on_the_package_provider(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, package_judge=package)], project
        )

        assert bindings == (
            make_binding(
                judge=JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="project-model")
            ),
        )

    def test_override_naming_a_provider_replaces_every_level(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        write_judge_rule(tmp_path, make_judge_rule().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            root=tmp_path,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        bindings = Bindings.from_rulesets([ruleset], project, override)

        assert bindings == (make_binding(judge=override),)


class TestBindingsJudgeRule:
    def test_rule_file_text_reaches_the_judge_unparsed(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        text = f"---\nname: {RULE_NAME}\n---\n{make_judge_rule().text}"
        write_judge_rule(tmp_path, text)

        bindings = Bindings.from_rulesets([make_ruleset(root=tmp_path)])

        assert bindings == (make_binding(judge_rule__text=text),)

    def test_skill_file_reaches_the_judge_without_its_frontmatter(
        self, tmp_path, make_binding, make_ruleset, make_judge_rule
    ):
        skill = tmp_path / "skills" / RULE_NAME
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {RULE_NAME}\n---\n{make_judge_rule().text}")

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=tmp_path, binding__rule=None, binding__skill=skill)]
        )

        assert bindings == (make_binding(),)

    def test_ruleset_may_bind_rule_files_and_skill_directories_together(
        self, tmp_path, make_binding, make_judge_rule
    ):
        naming = make_judge_rule(name="naming", text="# Naming\n\nNames say what a value is.\n")
        write_judge_rule(tmp_path / "python", make_judge_rule().text)
        (tmp_path / "python/skills/naming").mkdir(parents=True)
        (tmp_path / "python/skills/naming/SKILL.md").write_text(
            f"---\nname: naming\n---\n{naming.text}"
        )
        (tmp_path / "python/bindings").mkdir()
        (tmp_path / "python/bindings/naming.yaml").write_text(
            'skill: python/skills/naming\npaths: ["**"]\n'
        )
        (tmp_path / "python/bindings/placement.yaml").write_text(
            f'rule: {RULE_NAME}\npaths: ["**"]\n'
        )
        ruleset = RulesetLoader(repo=tmp_path, root=tmp_path / "python").load()

        bindings = Bindings.from_rulesets([ruleset])

        assert bindings == (make_binding(judge_rule=naming), make_binding())
