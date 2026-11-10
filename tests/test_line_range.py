import pytest
from pydantic import ValidationError

from codeguard.line_range import LineRange


class TestLineRange:
    def test_end_before_start_is_invalid(self):
        with pytest.raises(ValidationError):
            LineRange(start=3, end=2)

    def test_holds_its_first_and_last_line_and_those_between(self, make_line_range):
        lines = make_line_range(start=2, end=4)

        assert [line for line in range(1, 6) if line in lines] == [2, 3, 4]

    def test_str_of_one_line_is_its_line(self, make_line_range):
        assert str(make_line_range(start=9, end=9)) == "9"

    def test_str_of_several_lines_is_its_first_and_last_line(self, make_line_range):
        assert str(make_line_range(start=9, end=11)) == "9-11"

    def test_described_names_one_line_or_several(self, make_line_range):
        assert [make_line_range(start=9, end=end).described for end in (9, 11)] == [
            "line 9",
            "lines 9-11",
        ]
