from typing import Dict, List, Type, Optional
from .base_monitor import BaseGameMonitor
from .plugins.texas_holdem_monitor import TexasHoldemMonitor


class MonitorRegistry:
    _monitors: Dict[str, Type[BaseGameMonitor]] = {}
    
    @classmethod
    def register(cls, monitor_class: Type[BaseGameMonitor]):
        cls._monitors[monitor_class.game_id] = monitor_class
    
    @classmethod
    def get_monitor(cls, game_id: str) -> Optional[BaseGameMonitor]:
        monitor_class = cls._monitors.get(game_id)
        if monitor_class:
            return monitor_class()
        return None
    
    @classmethod
    def list_monitors(cls) -> List[Dict]:
        return [
            {
                "game_id": game_id,
                "monitor_type": monitor_class.__name__,
                "ui_config": monitor_class().get_ui_config(),
            }
            for game_id, monitor_class in cls._monitors.items()
        ]


MonitorRegistry.register(TexasHoldemMonitor)
