import factory

from codeguard.line_range import LineRange


class MakeLineRange(factory.Factory):
    class Meta:
        model = LineRange

    start = 1
    end = factory.SelfAttribute("start")
