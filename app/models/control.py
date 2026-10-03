from enum import StrEnum


class ControlMode(StrEnum):
    """Quem pode alterar o Game State. Ver docs/adr/0002."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
