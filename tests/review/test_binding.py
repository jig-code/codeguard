from codeguard.config import (
    JudgeChoice,
    JudgeProvider,
    RuleOverride,
    RulesetConfig,
    RulesetLoader,
)
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

    def test_from_config_has_its_exclude_paths(
        self, git_repo, make_binding, make_binding_config, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        config = make_binding_config(exclude_paths=("tests/**",))

        binding = Binding.from_config(
            RULE_NAME, config, make_ruleset(root=git_repo.root), JudgeChoice()
        )

        assert binding == make_binding(exclude_paths=("tests/**",))

    def test_preset_binding_matches_every_file(self, make_binding):
        binding = make_binding()

        files = binding.files(["a.py", "app/b.rb"])

        assert files == ["a.py", "app/b.rb"]

    def test_from_config_builds_the_binding_its_config_describes(
        self, git_repo, make_binding, make_binding_config, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        config = make_binding_config(severity=Severity.WARNING)

        binding = Binding.from_config(
            RULE_NAME, config, make_ruleset(root=git_repo.root), JudgeChoice()
        )

        assert binding == make_binding(severity=Severity.WARNING)

    def test_from_config_has_its_judge(
        self, git_repo, make_binding, make_binding_config, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        judge = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="gpt-6-luna")

        binding = Binding.from_config(
            RULE_NAME, make_binding_config(), make_ruleset(root=git_repo.root), judge
        )

        assert binding == make_binding(judge=judge)


class TestBindings:
    def test_from_rulesets_builds_each_binding(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)

        bindings = Bindings.from_rulesets([make_ruleset(root=git_repo.root)])

        assert bindings == (make_binding(),)

    def test_packaged_binding_is_named_by_its_ruleset(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)

        bindings = Bindings.from_rulesets([make_ruleset(root=git_repo.root, name="example/python")])

        assert bindings == (make_binding(rule=f"example/python/{RULE_NAME}"),)

    def test_excluded_binding_is_dropped(self, git_repo, make_ruleset, make_judge_rule):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        selection = RulesetConfig(exclude=(RULE_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_binding_left_out_of_include_is_dropped(self, git_repo, make_ruleset, make_judge_rule):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        selection = RulesetConfig(include=("another-rule",))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_included_binding_is_kept(self, git_repo, make_binding, make_ruleset, make_judge_rule):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        selection = RulesetConfig(include=(RULE_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, name="example/python", selection=selection)]
        )

        assert bindings == (make_binding(rule=f"example/python/{RULE_NAME}"),)

    def test_override_replaces_the_binding_fields(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        override = RuleOverride(paths=("app/**",), severity=Severity.WARNING)
        selection = RulesetConfig(rules={RULE_NAME: override})

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, name="example/python", selection=selection)]
        )

        assert bindings == (
            make_binding(
                rule=f"example/python/{RULE_NAME}",
                paths=("app/**",),
                severity=Severity.WARNING,
            ),
        )

    def test_override_replaces_the_excluded_paths(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        selection = RulesetConfig(rules={RULE_NAME: RuleOverride(exclude_paths=())})
        ruleset = make_ruleset(
            root=git_repo.root, binding__exclude_paths=("tests/**",), selection=selection
        )

        assert Bindings.from_rulesets([ruleset]) == (make_binding(),)


class TestBindingsJudge:
    def test_package_default_judges_its_rules(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.BEDROCK, model="package-model")

        bindings = Bindings.from_rulesets([make_ruleset(root=git_repo.root, package_judge=package)])

        assert bindings == (make_binding(judge=package),)

    def test_project_default_wins_over_the_package_default(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, package_judge=package)], project
        )

        assert bindings == (make_binding(judge=project),)

    def test_binding_wins_over_the_project_default(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            root=git_repo.root,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.GEMINI, model="bound-model")),
        )

    def test_provider_and_model_each_come_from_the_first_level_naming_it(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        package = JudgeChoice(model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK)
        ruleset = make_ruleset(
            root=git_repo.root, binding__model="bound-model", package_judge=package
        )

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.BEDROCK, model="bound-model")),
        )

    def test_project_model_runs_on_the_package_provider(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, package_judge=package)], project
        )

        assert bindings == (
            make_binding(
                judge=JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="project-model")
            ),
        )

    def test_override_naming_a_provider_replaces_every_level(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        git_repo.write(JUDGE_RULE_FILE, make_judge_rule().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            root=git_repo.root,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        bindings = Bindings.from_rulesets([ruleset], project, override)

        assert bindings == (make_binding(judge=override),)


class TestBindingsJudgeRule:
    def test_rule_file_text_reaches_the_judge_unparsed(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        text = f"---\nname: {RULE_NAME}\n---\n{make_judge_rule().text}"
        git_repo.write(JUDGE_RULE_FILE, text)

        bindings = Bindings.from_rulesets([make_ruleset(root=git_repo.root)])

        assert bindings == (make_binding(judge_rule__text=text),)

    def test_skill_file_reaches_the_judge_without_its_frontmatter(
        self, git_repo, make_binding, make_ruleset, make_judge_rule
    ):
        skill = git_repo.root / "skills" / RULE_NAME
        git_repo.write(
            f"skills/{RULE_NAME}/SKILL.md", f"---\nname: {RULE_NAME}\n---\n{make_judge_rule().text}"
        )

        bindings = Bindings.from_rulesets(
            [make_ruleset(root=git_repo.root, binding__rule=None, binding__skill=skill)]
        )

        assert bindings == (make_binding(),)

    def test_ruleset_may_bind_rule_files_and_skill_directories_together(
        self, git_repo, make_binding, make_judge_rule
    ):
        naming = make_judge_rule(name="naming", text="# Naming\n\nNames say what a value is.\n")
        git_repo.write(f"python/{JUDGE_RULE_FILE}", make_judge_rule().text)
        git_repo.write("python/skills/naming/SKILL.md", f"---\nname: naming\n---\n{naming.text}")
        git_repo.write(
            "python/bindings/naming.yaml", 'skill: python/skills/naming\npaths: ["**"]\n'
        )
        git_repo.write("python/bindings/placement.yaml", f'rule: {RULE_NAME}\npaths: ["**"]\n')
        ruleset = RulesetLoader(repo=git_repo.root, root=git_repo.root / "python").load()

        bindings = Bindings.from_rulesets([ruleset])

        assert bindings == (make_binding(judge_rule=naming), make_binding())
