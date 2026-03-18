from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class GamePhase(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass
class Player:
    id: str
    chips: int = 1000
    status: str = "active"
    current_bet: int = 0
    hand: List[str] = field(default_factory=list)
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False

    def to_dict(self, hide_hand: bool = False) -> Dict:
        return {
            "id": self.id,
            "chips": self.chips,
            "status": self.status,
            "current_bet": self.current_bet,
            "hand": [] if hide_hand else self.hand,
            "is_dealer": self.is_dealer,
            "is_small_blind": self.is_small_blind,
            "is_big_blind": self.is_big_blind,
        }


@dataclass
class GameAction:
    action: str
    amount: int = 0
    thought_process: str = ""


class BaseMCPGame(ABC):
    game_id: str = "base_game"
    name: str = "Base Game"
    min_players: int = 2
    max_players: int = 6

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[Player] = []
        self.phase = GamePhase.WAITING
        self.history: List[str] = []
        self.winner: Optional[str] = None

    @abstractmethod
    def add_player(self, player_id: str) -> bool:
        pass

    @abstractmethod
    def start_game(self) -> bool:
        pass

    @abstractmethod
    def apply_action(self, player_id: str, action: GameAction) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_visible_state(self, player_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_current_player(self) -> Optional[str]:
        pass

    @abstractmethod
    def is_player_turn(self, player_id: str) -> bool:
        pass

    @classmethod
    def get_prompt(cls) -> Dict[str, Any]:
        return {
            "description": f"{cls.name}博弈规则与动作规范",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": f"你是一个{cls.name}玩家。你的目标是获胜。\n"
                        f"最少玩家数: {cls.min_players}, 最多玩家数: {cls.max_players}",
                    },
                }
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "room_id": self.room_id,
            "phase": self.phase.value,
            "players": [p.to_dict() for p in self.players],
            "history": self.history,
            "winner": self.winner,
        }
