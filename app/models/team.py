from pydantic import BaseModel, ConfigDict, Field

HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"


class Team(BaseModel):
    model_config = ConfigDict(extra="forbid")

    abbr: str = Field(min_length=2, max_length=3)
    name: str = Field(min_length=1)
    score: int = Field(default=0, ge=0)
    primary_color: str = Field(pattern=HEX_COLOR)
    secondary_color: str = Field(pattern=HEX_COLOR)
