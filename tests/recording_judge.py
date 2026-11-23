from dataclasses import dataclass, field
from pathlib import Path

from codeguard.config import JudgeModel
from codeguard.review import Deadline, JudgeError, Judgement, JudgeRequest, Verdict


@dataclass(frozen=True)
class RecordingJudge:
    verdict: Verdict = Verdict(reason="The code keeps the convention.", violations=())
    identity: str = "recording"
    loaded_files: tuple[str, ...] = ()
    received: list[JudgeRequest] = field(default_factory=list)

    def judge(self, request: JudgeRequest) -> Judgement:
        self.received.append(request)
        return Judgement(self.verdict, self.loaded_files)


@dataclass(frozen=True)
class FailingJudge:
    error: str = "gemini failed with 502: upstream request failed"
    identity: str = "failing"

    def judge(self, request: JudgeRequest) -> Judgement:
        raise JudgeError(self.error)


@dataclass(frozen=True)
class SequencedJudge:
    verdicts: list[Verdict]
    identity: str = "sequenced"

    def judge(self, request: JudgeRequest) -> Judgement:
        return Judgement(self.verdicts.pop(0))


@dataclass(frozen=True)
class JudgeCreation:
    root: Path
    model: JudgeModel
    deadline: Deadline | None = None


@dataclass(frozen=True)
class RecordingJudges:
    judge: RecordingJudge | FailingJudge | SequencedJudge
    created: list[JudgeCreation] = field(default_factory=list)

    def __call__(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> RecordingJudge | FailingJudge | SequencedJudge:
        self.created.append(JudgeCreation(root, model, deadline))
        return self.judge
