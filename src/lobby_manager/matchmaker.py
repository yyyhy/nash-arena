import asyncio
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import time

from ..game_engine.game_registry import GameRegistry
from ..game_engine.base_game import BaseMCPGame, GamePhase


@dataclass
class WaitingPlayer:
    player_id: str
    game_id: str
    joined_at: float = field(default_factory=time.time)


@dataclass
class Room:
    room_id: str
    game_id: str
    game: BaseMCPGame
    players: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    
    player_turn_events: Dict[str, asyncio.Event] = field(default_factory=dict)
    game_over_event: asyncio.Event = field(default_factory=asyncio.Event)


class Matchmaker:
    def __init__(self):
        self.waiting_queues: Dict[str, List[WaitingPlayer]] = {}
        self.rooms: Dict[str, Room] = {}
        self.player_rooms: Dict[str, str] = {}

    def list_games(self) -> List[Dict]:
        return GameRegistry.list_games()

    def get_game_prompt(self, game_id: str) -> Optional[Dict]:
        game_class = GameRegistry.get_game_class(game_id)
        if game_class:
            return game_class.get_prompt()
        return None

    async def join_game(self, game_id: str, player_id: str, timeout: float = 20.0) -> Dict:
        game_class = GameRegistry.get_game_class(game_id)
        if not game_class:
            return {"status": "error", "message": f"未知游戏: {game_id}"}

        if player_id in self.player_rooms:
            room_id = self.player_rooms[player_id]
            room = self.rooms.get(room_id)
            if room and room.game.phase == GamePhase.IN_PROGRESS:
                return await self._wait_for_turn(room, player_id, timeout)

        if game_id not in self.waiting_queues:
            self.waiting_queues[game_id] = []

        queue = self.waiting_queues[game_id]
        queue.append(WaitingPlayer(player_id=player_id, game_id=game_id))

        if len(queue) >= game_class.min_players:
            return await self._try_start_game(game_id, player_id, timeout)

        return await self._wait_for_match(game_id, player_id, timeout)

    async def _try_start_game(self, game_id: str, player_id: str, timeout: float) -> Dict:
        queue = self.waiting_queues.get(game_id, [])
        game_class = GameRegistry.get_game_class(game_id)

        if len(queue) < game_class.min_players:
            return {"status": "waiting", "message": "等待更多玩家..."}

        players_to_start = queue[:game_class.max_players]
        self.waiting_queues[game_id] = queue[game_class.max_players:]

        room_id = f"room_{uuid.uuid4().hex[:8]}"
        game = game_class(room_id)

        for wp in players_to_start:
            game.add_player(wp.player_id)

        game.start_game()

        room = Room(
            room_id=room_id,
            game_id=game_id,
            game=game,
            players=set(wp.player_id for wp in players_to_start),
        )

        for pid in room.players:
            room.player_turn_events[pid] = asyncio.Event()
            self.player_rooms[pid] = room_id

        self.rooms[room_id] = room

        current_player = game.get_current_player()
        for pid in room.players:
            if pid == current_player:
                room.player_turn_events[pid].set()

        if player_id == current_player:
            return {
                "status": "your_turn",
                "room_id": room_id,
                "message": "匹配成功！游戏已开始，现在轮到你了。",
                "state": game.get_visible_state(player_id),
            }
        else:
            return await self._wait_for_turn(room, player_id, timeout)

    async def _wait_for_match(self, game_id: str, player_id: str, timeout: float) -> Dict:
        start_time = time.time()
        check_interval = 0.5

        while time.time() - start_time < timeout:
            if player_id in self.player_rooms:
                room_id = self.player_rooms[player_id]
                room = self.rooms.get(room_id)
                if room and room.game.phase == GamePhase.IN_PROGRESS:
                    return await self._wait_for_turn(room, player_id, timeout - (time.time() - start_time))

            queue = self.waiting_queues.get(game_id, [])
            game_class = GameRegistry.get_game_class(game_id)
            if len(queue) >= game_class.min_players:
                return await self._try_start_game(game_id, player_id, timeout - (time.time() - start_time))

            await asyncio.sleep(check_interval)

        queue = self.waiting_queues.get(game_id, [])
        self.waiting_queues[game_id] = [wp for wp in queue if wp.player_id != player_id]

        return {
            "status": "action_accepted_waiting",
            "message": "已加入队列，等待匹配中。请调用 get_game_state 工具持续关注局势。",
        }

    async def _wait_for_turn(self, room: Room, player_id: str, timeout: float) -> Dict:
        if room.game.phase == GamePhase.FINISHED:
            return self._get_game_over_result(room, player_id)

        if room.game.is_player_turn(player_id):
            return {
                "status": "your_turn",
                "room_id": room.room_id,
                "message": "轮到你了！",
                "state": room.game.get_visible_state(player_id),
            }

        if player_id not in room.player_turn_events:
            room.player_turn_events[player_id] = asyncio.Event()

        event = room.player_turn_events[player_id]
        event.clear()

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return {
                "status": "others_turn",
                "message": "其他玩家正在思考，请继续调用 get_game_state 等待。",
            }

        if room.game.phase == GamePhase.FINISHED:
            return self._get_game_over_result(room, player_id)

        if room.game.is_player_turn(player_id):
            return {
                "status": "your_turn",
                "room_id": room.room_id,
                "message": "轮到你了！",
                "state": room.game.get_visible_state(player_id),
            }

        return {
            "status": "others_turn",
            "message": "其他玩家正在思考，请继续调用 get_game_state 等待。",
        }

    async def get_game_state(self, room_id: str, player_id: str, timeout: float = 20.0) -> Dict:
        room = self.rooms.get(room_id)
        if not room:
            return {"status": "error", "message": "房间不存在", "is_error": True}

        if player_id not in room.players:
            return {"status": "error", "message": "你不是该房间的玩家", "is_error": True}

        return await self._wait_for_turn(room, player_id, timeout)

    async def submit_action(self, room_id: str, player_id: str, action_data: str, timeout: float = 20.0) -> Dict:
        room = self.rooms.get(room_id)
        if not room:
            return {"status": "error", "message": "房间不存在", "is_error": True}

        if player_id not in room.players:
            return {"status": "error", "message": "你不是该房间的玩家", "is_error": True}

        import json
        from ..game_engine.base_game import GameAction

        try:
            action_dict = json.loads(action_data)
            action = GameAction(
                action=action_dict.get("action", ""),
                amount=action_dict.get("amount", 0),
                thought_process=action_dict.get("thought_process", ""),
            )
        except json.JSONDecodeError:
            return {"status": "error", "message": "action_data 格式错误，必须是有效JSON", "is_error": True}

        result = room.game.apply_action(player_id, action)

        if not result.get("success"):
            return {"status": "error", "message": result.get("error", "动作执行失败"), "is_error": True}

        for pid in room.players:
            if pid in room.player_turn_events:
                room.player_turn_events[pid].set()
                room.player_turn_events[pid].clear()

        if room.game.phase == GamePhase.FINISHED:
            return self._get_game_over_result(room, player_id)

        current_player = room.game.get_current_player()
        if current_player and current_player in room.player_turn_events:
            room.player_turn_events[current_player].set()

        return await self._wait_for_turn(room, player_id, timeout)

    def _get_game_over_result(self, room: Room, player_id: str) -> Dict:
        winner = room.game.winner
        return {
            "status": "game_over",
            "winner": winner,
            "message": f"游戏结束！获胜者: {winner}" if winner else "游戏结束！",
            "final_state": room.game.get_visible_state(player_id),
        }

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)
