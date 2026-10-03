from pydantic import BaseModel, Field

HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"


class Team(BaseModel):
    abbr: str = Field(min_length=2, max_length=3)
    name: str = Field(min_length=1)
    score: int = Field(default=0, ge=0)
    primary_color: str = Field(pattern=HEX_COLOR)
    secondary_color: str = Field(pattern=HEX_COLOR)
