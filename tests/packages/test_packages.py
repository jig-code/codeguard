import pytest
from git_repo import GitRepo
from packaging.version import Version
from rules_package import write_package

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    ConfigError,
    JudgeChoice,
    JudgeProvider,
    PathPackageConfig,
    RuleOverride,
    Ruleset,
    RulesetConfig,
    Severity,
)
from codeguard.packages import GitFetch, Packages

AST_GREP = Version("0.45.3")
CODEGUARD = Version("0.2.0")


@pytest.fixture
def package(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    repo = GitRepo.init(tmp_path_factory.mktemp("package").resolve())
    write_package(repo)
    repo.commit("Add rules")
    return repo


@pytest.fixture
def fetch(tmp_path) -> GitFetch:
    return GitFetch(tmp_path / "cache")


class TestPackages:
    def test_opted_in_ruleset_is_named_by_package_and_ruleset(self, repo, package, fetch):
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        rulesets = Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        skill = package.root / "python/skills/responsibility-placement"
        assert rulesets == (
            Ruleset(
                name="example/python",
                root=package.root / "python",
                bindings=BindingsConfig(
                    {
                        "responsibility-placement.yaml": BindingConfig(
                            triggers=frozenset({"any"}), skill=skill, paths=("**/*.py",)
                        )
                    }
                ),
            ),
        )

    def test_ruleset_has_the_package_judge_default(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml",
            "name: example\nrulesets: [python]\njudge:\n  provider: bedrock\n  model: a-model\n",
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        (ruleset,) = Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert ruleset.package_judge == JudgeChoice(provider=JudgeProvider.BEDROCK, model="a-model")

    def test_package_judge_default_with_another_key_is_an_error(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml",
            "name: example\nrulesets: [python]\njudge:\n  calls_at_once: 1\n",
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{package.root}/codeguard-package.yaml is invalid:\n"
            "  judge.calls_at_once: Extra inputs are not permitted"
        )

    def test_relative_path_package_is_under_the_working_tree(self, repo, fetch):
        write_package(repo, "rules/")
        config = PathPackageConfig(path="rules", rulesets={"python": RulesetConfig()})

        (ruleset,) = Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert ruleset.root == repo.root / "rules" / "python"

    def test_ruleset_the_package_lacks_is_an_error(self, repo, package, fetch):
        config = PathPackageConfig(path=package.root, rulesets={"ruby": RulesetConfig()})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  packages.0.rulesets: example has no ruleset ruby"
        )

    def test_ast_grep_outside_the_package_range_is_an_error(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml", "name: example\nrulesets: [python]\nast-grep: '>=0.46'\n"
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  packages.0: example supports ast-grep >=0.46, not 0.45.3"
        )

    def test_ast_grep_inside_the_package_range_loads(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml",
            "name: example\nrulesets: [python]\nast-grep: '>=0.45,<0.46'\n",
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        rulesets = Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert [ruleset.name for ruleset in rulesets] == ["example/python"]

    def test_codeguard_outside_the_package_range_is_an_error(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml", "name: example\nrulesets: [python]\ncodeguard: '>=0.3'\n"
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  packages.0: example needs codeguard >=0.3, not 0.2.0; upgrade codeguard"
        )

    def test_codeguard_inside_the_package_range_loads(self, repo, package, fetch):
        package.write(
            "codeguard-package.yaml", "name: example\nrulesets: [python]\ncodeguard: '>=0.2'\n"
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": RulesetConfig()})

        rulesets = Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert [ruleset.name for ruleset in rulesets] == ["example/python"]

    def test_unknown_rule_is_an_error(self, repo, package, fetch):
        selection = RulesetConfig(
            exclude=("no-prnt",), rules={"no-print": RuleOverride(severity=Severity.WARNING)}
        )
        config = PathPackageConfig(path=package.root, rulesets={"python": selection})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  packages.0.rulesets.python: unknown rule no-prnt"
        )

    def test_unknown_included_rule_is_an_error(self, repo, package, fetch):
        config = PathPackageConfig(
            path=package.root, rulesets={"python": RulesetConfig(include=("no-prnt",))}
        )

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  packages.0.rulesets.python: unknown rule no-prnt"
        )

    def test_directory_without_a_manifest_is_an_error(self, repo, tmp_path, fetch):
        config = PathPackageConfig(path=tmp_path, rulesets={"python": RulesetConfig()})

        with pytest.raises(ConfigError) as error:
            Packages(repo.root, fetch, AST_GREP, CODEGUARD).rulesets([config])

        assert str(error.value) == f"{tmp_path} has no codeguard-package.yaml"
