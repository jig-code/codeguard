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
