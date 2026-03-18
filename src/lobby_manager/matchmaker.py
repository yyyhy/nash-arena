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
    last_seen: float = field(default_factory=time.time)


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
        self.matchmaking_timers: Dict[str, float] = {}

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
                return await self.get_game_state(room_id, player_id, timeout)

        queue = self.waiting_queues.get(game_id, [])
        now = time.time()
        
        # 清理超时的死连接玩家 (60秒未发请求)
        self.waiting_queues[game_id] = [wp for wp in queue if now - wp.last_seen < 60.0]
        queue = self.waiting_queues[game_id]

        existing_wp = next((wp for wp in queue if wp.player_id == player_id), None)
        if not existing_wp:
            queue.append(WaitingPlayer(player_id=player_id, game_id=game_id, joined_at=now, last_seen=now))
        else:
            existing_wp.last_seen = now

        # 更新匹配计时器
        if len(queue) >= game_class.min_players:
            if game_id not in self.matchmaking_timers:
                self.matchmaking_timers[game_id] = time.time()
        else:
            if game_id in self.matchmaking_timers:
                del self.matchmaking_timers[game_id]

        can_start = False
        if len(queue) >= game_class.max_players:
            can_start = True
        elif len(queue) >= game_class.min_players:
            timer_start = self.matchmaking_timers.get(game_id, time.time())
            if time.time() - timer_start >= 10.0:  # 匹配窗口时间：达到最少人数后等待10秒
                can_start = True

        if can_start:
            return await self._try_start_game(game_id, player_id, timeout)

        return await self._wait_for_match(game_id, player_id, timeout)

    async def _try_start_game(self, game_id: str, player_id: str, timeout: float) -> Dict:
        queue = self.waiting_queues.get(game_id, [])
        game_class = GameRegistry.get_game_class(game_id)

        if len(queue) < game_class.min_players:
            if player_id in self.player_rooms:
                room_id = self.player_rooms[player_id]
                room = self.rooms.get(room_id)
                if room and room.game.phase == GamePhase.IN_PROGRESS:
                    return await self.get_game_state(room_id, player_id, timeout)
            return await self._wait_for_match(game_id, player_id, timeout)

        players_to_start = queue[:game_class.max_players]
        self.waiting_queues[game_id] = queue[game_class.max_players:]
        
        if game_id in self.matchmaking_timers:
            del self.matchmaking_timers[game_id]

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
            else:
                # 显式地唤醒其他不在当前回合的玩家，让他们能够立即收到进入房间的消息
                room.player_turn_events[pid].set()
                room.player_turn_events[pid].clear()

        if player_id == current_player:
            return {
                "status": "your_turn",
                "room_id": room_id,
                "message": "匹配成功！游戏已开始，现在轮到你了。",
                "state": game.get_visible_state(player_id),
            }
        else:
            return await self.get_game_state(room_id, player_id, timeout)

    async def _wait_for_match(self, game_id: str, player_id: str, timeout: float) -> Dict:
        start_time = time.time()
        check_interval = 0.5
        MATCHMAKING_WAIT_TIME = 10.0

        while time.time() - start_time < timeout:
            now = time.time()
            queue = self.waiting_queues.get(game_id, [])
            existing_wp = next((wp for wp in queue if wp.player_id == player_id), None)
            if existing_wp:
                existing_wp.last_seen = now

            if player_id in self.player_rooms:
                room_id = self.player_rooms[player_id]
                room = self.rooms.get(room_id)
                if room and room.game.phase == GamePhase.IN_PROGRESS:
                    return await self.get_game_state(room_id, player_id, timeout - (time.time() - start_time))

            game_class = GameRegistry.get_game_class(game_id)
            
            if len(queue) >= game_class.min_players:
                if game_id not in self.matchmaking_timers:
                    self.matchmaking_timers[game_id] = time.time()
            else:
                if game_id in self.matchmaking_timers:
                    del self.matchmaking_timers[game_id]

            if queue:
                # 只有队列中的第一个人（房主）负责触发游戏开始，防止多人并发创建多个房间
                if queue[0].player_id == player_id:
                    if len(queue) >= game_class.max_players:
                        return await self._try_start_game(game_id, player_id, timeout - (time.time() - start_time))
                    elif len(queue) >= game_class.min_players:
                        timer_start = self.matchmaking_timers.get(game_id, time.time())
                        if time.time() - timer_start >= MATCHMAKING_WAIT_TIME:
                            return await self._try_start_game(game_id, player_id, timeout - (time.time() - start_time))

            await asyncio.sleep(check_interval)

        return {
            "status": "action_accepted_waiting",
            "message": "已加入队列，等待匹配中。如果你还未匹配成功，请继续调用 join_game 轮询；如果已匹配成功但未轮到你，请调用 get_game_state 持续关注局势。",
        }

    async def _wait_for_turn(self, room: Room, player_id: str, timeout: float) -> Dict:
        # 该方法已弃用，统一使用 get_game_state 内部的轮询逻辑
        return await self.get_game_state(room.room_id, player_id, timeout)

    async def get_game_state(self, room_id: str, player_id: str, timeout: float = 20.0) -> Dict:
        room = self.rooms.get(room_id)
        if not room:
            return {"status": "error", "message": "房间不存在", "is_error": True}

        if player_id not in room.players:
            return {"status": "error", "message": "你不是该房间的玩家", "is_error": True}

        # 使用短轮询模拟长轮询，每秒检查一次是否轮到自己
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 增加检查，如果房间已经被清理（不存在），退出
            if room_id not in self.rooms:
                return {"status": "error", "message": "房间已关闭或不存在", "is_error": True}
                
            if room.game.phase == GamePhase.FINISHED:
                return self._get_game_over_result(room, player_id)

            if room.game.is_player_turn(player_id):
                return {
                    "status": "your_turn",
                    "room_id": room.room_id,
                    "message": "轮到你了！",
                    "state": room.game.get_visible_state(player_id),
                }
            await asyncio.sleep(1.0)

        return {
            "status": "others_turn",
            "message": "其他玩家正在思考，请继续调用 get_game_state 等待。",
        }

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

        # 唤醒所有正在等待的玩家
        for pid in room.players:
            if pid in room.player_turn_events:
                room.player_turn_events[pid].set()

        # 这里不再使用 asyncio.Event 挂起，而是直接返回当前状态，让客户端发起 get_game_state
        if room.game.phase == GamePhase.FINISHED:
            return self._get_game_over_result(room, player_id)

        if room.game.is_player_turn(player_id):
             return {
                "status": "your_turn",
                "room_id": room.room_id,
                "message": "动作成功！现在又轮到你了。",
                "state": room.game.get_visible_state(player_id),
            }

        return {
            "status": "others_turn",
            "message": "动作成功！当前轮到其他人行动，请调用 get_game_state 持续关注局势。",
        }

    def _get_game_over_result(self, room: Room, player_id: str) -> Dict:
        winner = room.game.winner
        # 返回前清理内存中的房间信息（避免僵尸房间堆积）
        if room.room_id in self.rooms:
            # 延迟更长时间清理（比如 30 秒），以便在前端监控中能看到对局结束状态
            asyncio.create_task(self._cleanup_room_delayed(room.room_id, delay=30.0))
            
        return {
            "status": "game_over",
            "winner": winner,
            "message": f"游戏结束！获胜者: {winner}" if winner else "游戏结束！",
            "final_state": room.game.get_visible_state(player_id),
        }

    async def _cleanup_room_delayed(self, room_id: str, delay: float):
        await asyncio.sleep(delay)
        if room_id in self.rooms:
            room = self.rooms[room_id]
            for pid in room.players:
                if pid in self.player_rooms:
                    del self.player_rooms[pid]
            del self.rooms[room_id]

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)
