from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time


class MonitorEventType(str, Enum):
    GAME_CREATED = "game_created"
    GAME_STARTED = "game_started"
    PLAYER_JOINED = "player_joined"
    PLAYER_ACTION = "player_action"
    ROUND_CHANGED = "round_changed"
    GAME_ENDED = "game_ended"


@dataclass
class MonitorEvent:
    event_type: MonitorEventType
    room_id: str
    game_id: str
    timestamp: float
    data: Dict[str, Any]


class BaseGameMonitor(ABC):
    game_id: str = "base"
    
    @abstractmethod
    def get_full_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_public_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def format_event(self, event: MonitorEvent) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_ui_config(self) -> Dict[str, Any]:
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "monitor_type": self.__class__.__name__,
        }
    
    @staticmethod
    def create_event(
        event_type: MonitorEventType,
        room_id: str,
        game_id: str,
        data: Dict[str, Any]
    ) -> MonitorEvent:
        return MonitorEvent(
            event_type=event_type,
            room_id=room_id,
            game_id=game_id,
            timestamp=time.time(),
            data=data
        )
