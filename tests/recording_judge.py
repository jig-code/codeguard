from dataclasses import dataclass, field
from pathlib import Path

from codeguard.config import JudgeModel
from codeguard.review import Judgement, JudgeProcessError, JudgeRequest, Verdict


@dataclass(frozen=True)
class RecordingJudge:
    verdict: Verdict = Verdict(violations=())
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
        raise JudgeProcessError(self.error)


@dataclass(frozen=True)
class JudgeCreation:
    root: Path
    model: JudgeModel


@dataclass(frozen=True)
class RecordingJudges:
    judge: RecordingJudge | FailingJudge
    created: list[JudgeCreation] = field(default_factory=list)

    def __call__(self, root: Path, model: JudgeModel) -> RecordingJudge | FailingJudge:
        self.created.append(JudgeCreation(root, model))
        return self.judge
