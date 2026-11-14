import pytest

from codeguard.config import language_of, named_languages


class TestLanguages:
    @pytest.mark.parametrize(
        ("file", "language"),
        [("orders.py", "python"), ("app/view.tsx", "typescript"), ("README.md", None)],
    )
    def test_a_file_language_is_its_extension(self, file, language):
        assert language_of(file) == language

    def test_paths_name_the_languages_of_their_extensions(self):
        assert named_languages(("src/**/*.py", "**/*.[jt]s", "docs/**")) == {
            "python",
            "javascript",
            "typescript",
        }
