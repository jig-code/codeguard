from pydantic import BaseModel, ConfigDict


class PatternRule(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    metadata: dict[str, object] | None = None

    @property
    def says_why(self) -> bool:
        why = (self.metadata or {}).get("why")
        return isinstance(why, str) and bool(why.strip())
