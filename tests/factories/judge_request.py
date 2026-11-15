import factory

from codeguard.review import JudgeRequest
from factories.skill import MakeSkill


class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    skill = factory.SubFactory(MakeSkill)
    file = "a.py"
    changes = "+     1\tprint(1)\n"
