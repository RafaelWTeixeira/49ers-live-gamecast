from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_game_service
from app.models.game import GameState
from app.services.game_service import GameService

router = APIRouter(prefix="/api")


@router.get("/game")
def get_game(service: Annotated[GameService, Depends(get_game_service)]) -> GameState:
    return service.state
