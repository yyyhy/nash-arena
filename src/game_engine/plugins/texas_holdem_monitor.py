from typing import Any, Dict, List
from ..base_monitor import BaseGameMonitor, MonitorEvent, MonitorEventType


class TexasHoldemMonitor(BaseGameMonitor):
    game_id = "texas_holdem"
    
    def get_full_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "room_id": game_state.get("room_id"),
            "phase": game_state.get("phase"),
            "betting_round": game_state.get("betting_round"),
            "pot": game_state.get("pot"),
            "current_bet": game_state.get("current_bet"),
            "dealer_position": game_state.get("dealer_position"),
            "small_blind": game_state.get("small_blind"),
            "big_blind": game_state.get("big_blind"),
            "community_cards": game_state.get("community_cards", []),
            "players": [
                {
                    "id": p.get("id"),
                    "chips": p.get("chips"),
                    "current_bet": p.get("current_bet"),
                    "status": p.get("status"),
                    "hand": p.get("hand", []),
                    "is_dealer": p.get("is_dealer", False),
                    "is_small_blind": p.get("is_small_blind", False),
                    "is_big_blind": p.get("is_big_blind", False),
                }
                for p in game_state.get("players", [])
            ],
            "history": game_state.get("history", []),
            "winner": game_state.get("winner"),
        }
    
    def get_public_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "room_id": game_state.get("room_id"),
            "phase": game_state.get("phase"),
            "betting_round": game_state.get("betting_round"),
            "pot": game_state.get("pot"),
            "current_bet": game_state.get("current_bet"),
            "dealer_position": game_state.get("dealer_position"),
            "small_blind": game_state.get("small_blind"),
            "big_blind": game_state.get("big_blind"),
            "community_cards": game_state.get("community_cards", []),
            "players": [
                {
                    "id": p.get("id"),
                    "chips": p.get("chips"),
                    "current_bet": p.get("current_bet"),
                    "status": p.get("status"),
                    "hand": [],
                    "is_dealer": p.get("is_dealer", False),
                    "is_small_blind": p.get("is_small_blind", False),
                    "is_big_blind": p.get("is_big_blind", False),
                }
                for p in game_state.get("players", [])
            ],
            "history": game_state.get("history", []),
            "winner": game_state.get("winner"),
        }
    
    def format_event(self, event: MonitorEvent) -> Dict[str, Any]:
        base = {
            "event_type": event.event_type.value,
            "room_id": event.room_id,
            "game_id": event.game_id,
            "timestamp": event.timestamp,
        }
        
        if event.event_type == MonitorEventType.PLAYER_ACTION:
            action_data = event.data
            base["player_id"] = action_data.get("player_id")
            base["action"] = action_data.get("action")
            base["amount"] = action_data.get("amount")
            base["thought_process"] = action_data.get("thought_process")
        
        elif event.event_type == MonitorEventType.ROUND_CHANGED:
            base["new_round"] = event.data.get("new_round")
            base["community_cards"] = event.data.get("community_cards", [])
        
        elif event.event_type == MonitorEventType.GAME_ENDED:
            base["winner"] = event.data.get("winner")
            base["final_pot"] = event.data.get("final_pot")
        
        return base
    
    def get_ui_config(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "display_name": "德州扑克",
            "layout": "poker_table",
            "components": [
                {
                    "name": "poker_table",
                    "type": "poker_table",
                    "position": "center",
                },
                {
                    "name": "community_cards",
                    "type": "card_row",
                    "position": "center_top",
                },
                {
                    "name": "pot_display",
                    "type": "chip_stack",
                    "position": "center",
                },
                {
                    "name": "player_seats",
                    "type": "player_ring",
                    "position": "around_table",
                    "max_players": 6,
                },
                {
                    "name": "action_history",
                    "type": "timeline",
                    "position": "bottom",
                },
            ],
            "card_style": {
                "back_color": "#1a472a",
                "front_style": "classic",
                "suit_colors": {
                    "H": "#e74c3c",
                    "D": "#e74c3c",
                    "C": "#2c3e50",
                    "S": "#2c3e50",
                },
            },
            "chip_colors": {
                "10": "#3498db",
                "25": "#27ae60",
                "50": "#e74c3c",
                "100": "#9b59b6",
            },
        }
