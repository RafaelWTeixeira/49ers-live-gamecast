from pydantic import BaseModel, Field


class Play(BaseModel):
    description: str = Field(min_length=1)
    yards: int | None = None
