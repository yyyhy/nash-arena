from typing import Dict, List, Type
from .base_game import BaseMCPGame
from .plugins.texas_holdem import TexasHoldemGame
from .plugins.gomoku import Gomoku


class GameRegistry:
    _games: Dict[str, Type[BaseMCPGame]] = {}

    @classmethod
    def register(cls, game_class: Type[BaseMCPGame]):
        cls._games[game_class.game_id] = game_class

    @classmethod
    def get_game_class(cls, game_id: str) -> Type[BaseMCPGame] | None:
        return cls._games.get(game_id)

    @classmethod
    def list_games(cls) -> List[Dict]:
        return [
            {
                "game_id": game_class.game_id,
                "name": game_class.name,
                "min_players": game_class.min_players,
                "max_players": game_class.max_players,
            }
            for game_class in cls._games.values()
        ]


GameRegistry.register(TexasHoldemGame)
GameRegistry.register(Gomoku)
