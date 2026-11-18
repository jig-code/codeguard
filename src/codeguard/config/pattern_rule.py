from pydantic import BaseModel, ConfigDict


class PatternRuleMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    why: str | None = None


class PatternRule(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    metadata: PatternRuleMetadata | None = None

    @property
    def says_why(self) -> bool:
        return self.metadata is not None and bool(self.metadata.why and self.metadata.why.strip())
