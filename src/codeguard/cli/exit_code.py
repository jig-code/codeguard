from enum import IntEnum


class ExitCode(IntEnum):
    PASSED = 0
    FAILED = 1
    ERROR = 2

    @classmethod
    def of(cls, passed: bool) -> "ExitCode":
        return cls.PASSED if passed else cls.FAILED
