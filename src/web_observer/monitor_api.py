import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from ..game_engine.monitor_registry import MonitorRegistry


router = APIRouter(prefix="/monitor", tags=["monitor"])

matchmaker = None


def init_monitor_api(m):
    global matchmaker
    matchmaker = m


@router.get("/", response_class=HTMLResponse)
async def get_monitor_page():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Monitor page not found</h1>", status_code=404)


@router.get("/games")
async def list_monitors():
    return {"monitors": MonitorRegistry.list_monitors()}


@router.get("/rooms")
async def list_rooms():
    if not matchmaker:
        return {"rooms": []}
    
    rooms = []
    for room_id, room in matchmaker.rooms.items():
        game_state = room.game.to_dict()
        rooms.append({
            "room_id": room_id,
            "game_id": room.game_id,
            "phase": game_state.get("phase"),
            "players": list(room.players),
            "created_at": room.created_at,
        })
    
    return {"rooms": rooms}


@router.get("/room/{room_id}")
async def get_room_state(room_id: str, show_hands: bool = False):
    if not matchmaker:
        raise HTTPException(status_code=500, detail="Matchmaker not initialized")
    
    room = matchmaker.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    monitor = MonitorRegistry.get_monitor(room.game_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found for this game")
    
    game_state = room.game.to_dict()
    
    if show_hands:
        state = monitor.get_full_state(game_state)
    else:
        state = monitor.get_public_state(game_state)
    
    return {
        "room_id": room_id,
        "game_id": room.game_id,
        "monitor_type": monitor.__class__.__name__,
        "ui_config": monitor.get_ui_config(),
        "state": state,
    }


@router.get("/room/{room_id}/ui")
async def get_room_ui_config(room_id: str):
    if not matchmaker:
        raise HTTPException(status_code=500, detail="Matchmaker not initialized")
    
    room = matchmaker.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    monitor = MonitorRegistry.get_monitor(room.game_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found for this game")
    
    return {
        "room_id": room_id,
        "game_id": room.game_id,
        "ui_config": monitor.get_ui_config(),
    }
