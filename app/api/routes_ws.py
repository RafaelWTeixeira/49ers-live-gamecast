import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.dependencies import get_game_service
from app.models.event import GameEvent
from app.models.game import GameState
from app.services.game_service import GameService

router = APIRouter()


def to_message(item: GameState | GameEvent) -> dict[str, Any]:
    if isinstance(item, GameEvent):
        return {"type": "GAME_EVENT", "event": item.model_dump(mode="json")}
    return {"type": "GAME_STATE", "game": item.model_dump(mode="json")}


@router.websocket("/ws/game")
async def game_updates(
    websocket: WebSocket, service: Annotated[GameService, Depends(get_game_service)]
) -> None:
    """Envia o Game State atual ao conectar e, depois, cada mudança e cada Game Event."""
    await websocket.accept()

    # O GameService pode ser atualizado de outra thread (rotas síncronas), daí o threadsafe.
    loop = asyncio.get_running_loop()
    outbox: asyncio.Queue[GameState | GameEvent] = asyncio.Queue()
    unsubscribe = service.subscribe(lambda item: loop.call_soon_threadsafe(outbox.put_nowait, item))

    async def send_updates() -> None:
        await websocket.send_json(to_message(service.state))
        while True:
            await websocket.send_json(to_message(await outbox.get()))

    sender = asyncio.create_task(send_updates())
    try:
        # O overlay não envia nada; ler serve para perceber a desconexão.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe()
        sender.cancel()
