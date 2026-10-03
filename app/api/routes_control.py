from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_game_service, get_provider_health
from app.models.control import ControlMode
from app.models.event import GameEvent
from app.models.game import GameState
from app.services.game_service import ControlModeError, GameService, NothingToUndoError
from app.services.provider_sync import ProviderHealth

# Rotas async: rodam no mesmo event loop da sincronização, sem concorrência entre threads.
router = APIRouter(prefix="/api/control")

Service = Annotated[GameService, Depends(get_game_service)]
Health = Annotated[ProviderHealth, Depends(get_provider_health)]


class ModeChange(BaseModel):
    mode: ControlMode


def control_status(service: GameService, health: ProviderHealth) -> dict[str, Any]:
    return {
        "mode": service.control_mode,
        "can_undo": service.can_undo,
        "provider": {
            "healthy": health.healthy,
            "last_success_at": health.last_success_at,
            "last_error": health.last_error,
            "last_error_at": health.last_error_at,
        },
    }


def run_manual(action) -> None:
    try:
        action()
    except (ControlModeError, NothingToUndoError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except ValueError as error:  # inclui ValidationError do Pydantic
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("")
async def get_control(service: Service, health: Health) -> dict[str, Any]:
    return control_status(service, health)


@router.put("/mode")
async def change_mode(change: ModeChange, service: Service, health: Health) -> dict[str, Any]:
    service.set_control_mode(change.mode)
    return control_status(service, health)


@router.put("/game")
async def edit_game(state: GameState, service: Service) -> GameState:
    run_manual(lambda: service.apply_manual(state))
    return service.state


@router.post("/events")
async def register_event(event: GameEvent, service: Service) -> GameState:
    run_manual(lambda: service.announce_manual(event))
    return service.state


@router.post("/undo")
async def undo(service: Service) -> GameState:
    run_manual(service.undo)
    return service.state


@router.post("/flip-field")
async def flip_field(service: Service) -> GameState:
    """Inverte a Field Direction, para quando o lado pré-definido não bate com o jogo."""
    state = service.state
    flipped = "right" if state.opening_field_direction == "left" else "left"
    run_manual(lambda: service.apply_manual(state.with_changes(opening_field_direction=flipped)))
    return service.state
