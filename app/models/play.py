from pydantic import BaseModel, ConfigDict, Field


class Play(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    yards: int | None = None
