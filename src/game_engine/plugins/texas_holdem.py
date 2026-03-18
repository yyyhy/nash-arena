import random
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

from ..base_game import BaseMCPGame, GameAction, GamePhase, Player


class BettingRound(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


SUITS = ["H", "D", "C", "S"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def create_deck() -> List[str]:
    deck = [f"{s}-{r}" for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck


def evaluate_hand(hand: List[str], community: List[str]) -> tuple:
    all_cards = hand + community
    if len(all_cards) < 5:
        return (0, [])
    
    ranks = {}
    suits = {}
    for card in all_cards:
        suit, rank = card.split("-")
        ranks[rank] = ranks.get(rank, 0) + 1
        suits[suit] = suits.get(suit, 0) + 1
    
    rank_values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    
    sorted_ranks = sorted([rank_values.get(r, 0) for r in ranks.keys()], reverse=True)
    
    is_flush = any(count >= 5 for count in suits.values())
    
    rank_counts = sorted(ranks.values(), reverse=True)
    
    if rank_counts[0] == 4:
        return (7, sorted_ranks)
    elif rank_counts[0] == 3 and rank_counts[1] >= 2:
        return (6, sorted_ranks)
    elif is_flush:
        return (5, sorted_ranks)
    elif rank_counts[0] == 3:
        return (3, sorted_ranks)
    elif rank_counts[0] == 2 and rank_counts[1] == 2:
        return (2, sorted_ranks)
    elif rank_counts[0] == 2:
        return (1, sorted_ranks)
    else:
        return (0, sorted_ranks)


class TexasHoldemGame(BaseMCPGame):
    game_id = "texas_holdem"
    name = "德州扑克"
    min_players = 2
    max_players = 6

    def __init__(self, room_id: str, small_blind: int = 10, big_blind: int = 20):
        super().__init__(room_id)
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck: List[str] = []
        self.community_cards: List[str] = []
        self.pot: int = 0
        self.current_bet: int = 0
        self.betting_round: BettingRound = BettingRound.PREFLOP
        self.dealer_position: int = 0
        self.current_player_index: int = 0
        self.last_raiser_index: int = -1
        self.actions_this_round: int = 0

    def add_player(self, player_id: str) -> bool:
        if len(self.players) >= self.max_players:
            return False
        if any(p.id == player_id for p in self.players):
            return False
        self.players.append(Player(id=player_id, chips=1000))
        return True

    def start_game(self) -> bool:
        if len(self.players) < self.min_players:
            return False
        
        self.phase = GamePhase.IN_PROGRESS
        self.deck = create_deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.betting_round = BettingRound.PREFLOP
        self.dealer_position = random.randint(0, len(self.players) - 1)
        self.history = []
        
        for p in self.players:
            p.hand = [self.deck.pop(), self.deck.pop()]
            p.status = "active"
            p.current_bet = 0
            p.is_dealer = False
            p.is_small_blind = False
            p.is_big_blind = False
        
        self.players[self.dealer_position].is_dealer = True
        
        sb_index = (self.dealer_position + 1) % len(self.players)
        bb_index = (self.dealer_position + 2) % len(self.players)
        
        sb_player = self.players[sb_index]
        sb_player.is_small_blind = True
        sb_amount = min(self.small_blind, sb_player.chips)
        sb_player.chips -= sb_amount
        sb_player.current_bet = sb_amount
        self.pot += sb_amount
        self.history.append(f"{sb_player.id} posts small blind {sb_amount}")
        
        bb_player = self.players[bb_index]
        bb_player.is_big_blind = True
        bb_amount = min(self.big_blind, bb_player.chips)
        bb_player.chips -= bb_amount
        bb_player.current_bet = bb_amount
        self.pot += bb_amount
        self.history.append(f"{bb_player.id} posts big blind {bb_amount}")
        
        self.current_bet = self.big_blind
        self.current_player_index = (bb_index + 1) % len(self.players)
        self.last_raiser_index = bb_index
        self.actions_this_round = 0
        
        return True

    def get_current_player(self) -> Optional[str]:
        if self.phase != GamePhase.IN_PROGRESS:
            return None
        
        for _ in range(len(self.players)):
            player = self.players[self.current_player_index]
            if player.status == "active":
                return player.id
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        return None

    def is_player_turn(self, player_id: str) -> bool:
        return self.get_current_player() == player_id

    def apply_action(self, player_id: str, action: GameAction) -> Dict[str, Any]:
        if self.phase != GamePhase.IN_PROGRESS:
            return {"success": False, "error": "游戏未开始或已结束"}
        
        if not self.is_player_turn(player_id):
            return {"success": False, "error": "现在不是你的回合"}
        
        player = self.players[self.current_player_index]
        
        if action.action == "fold":
            player.status = "folded"
            thought = f" (思考: {action.thought_process})" if action.thought_process else ""
            self.history.append(f"{player.id} folds{thought}")
            self._check_round_end()
            
        elif action.action == "check":
            if player.current_bet < self.current_bet:
                return {"success": False, "error": f"当前下注额为{self.current_bet}，无法check，请call或raise"}
            thought = f" (思考: {action.thought_process})" if action.thought_process else ""
            self.history.append(f"{player.id} checks{thought}")
            self.actions_this_round += 1
            self._advance_player()
            self._check_round_end()
            
        elif action.action == "call":
            call_amount = self.current_bet - player.current_bet
            if call_amount <= 0:
                return {"success": False, "error": "无需call，可以check"}
            if call_amount > player.chips:
                call_amount = player.chips
            player.chips -= call_amount
            player.current_bet += call_amount
            self.pot += call_amount
            thought = f" (思考: {action.thought_process})" if action.thought_process else ""
            self.history.append(f"{player.id} calls {call_amount}{thought}")
            self.actions_this_round += 1
            self._advance_player()
            self._check_round_end()
            
        elif action.action == "raise":
            if action.amount <= self.current_bet:
                return {"success": False, "error": f"加注金额必须大于当前下注额{self.current_bet}"}
            
            raise_amount = action.amount - player.current_bet
            if raise_amount > player.chips:
                return {"success": False, "error": f"筹码不足，你只有{player.chips}筹码"}
            
            player.chips -= raise_amount
            player.current_bet = action.amount
            self.pot += raise_amount
            self.current_bet = action.amount
            self.last_raiser_index = self.current_player_index
            self.actions_this_round = 1
            thought = f" (思考: {action.thought_process})" if action.thought_process else ""
            self.history.append(f"{player.id} raises to {action.amount}{thought}")
            self._advance_player()
            self._check_round_end()
            
        else:
            return {"success": False, "error": f"未知动作: {action.action}"}
        
        return {"success": True}

    def _advance_player(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        active_count = sum(1 for p in self.players if p.status == "active")
        if active_count <= 1:
            return
        
        start_index = self.current_player_index
        while True:
            player = self.players[self.current_player_index]
            if player.status == "active":
                break
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player_index == start_index:
                break

    def _check_round_end(self):
        active_players = [p for p in self.players if p.status == "active"]
        
        if len(active_players) <= 1:
            self._end_hand()
            return
        
        all_matched = all(p.current_bet == self.current_bet for p in active_players)
        
        if not all_matched:
            return
        
        if self.betting_round == BettingRound.PREFLOP:
            bb_index = (self.dealer_position + 2) % len(self.players)
            bb_player = self.players[bb_index]
            if bb_player.status == "active" and self.actions_this_round == 1:
                if self.current_player_index == bb_index:
                    return
        else:
            if self.actions_this_round < len(active_players):
                return
        
        self._next_betting_round()

    def _next_betting_round(self):
        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0
        self.actions_this_round = 0
        self.last_raiser_index = -1
        
        if self.betting_round == BettingRound.PREFLOP:
            self.betting_round = BettingRound.FLOP
            self.community_cards.extend([self.deck.pop(), self.deck.pop(), self.deck.pop()])
            self.history.append("--- FLOP ---")
        elif self.betting_round == BettingRound.FLOP:
            self.betting_round = BettingRound.TURN
            self.community_cards.append(self.deck.pop())
            self.history.append("--- TURN ---")
        elif self.betting_round == BettingRound.TURN:
            self.betting_round = BettingRound.RIVER
            self.community_cards.append(self.deck.pop())
            self.history.append("--- RIVER ---")
        elif self.betting_round == BettingRound.RIVER:
            self._showdown()
            return
        
        self.current_player_index = (self.dealer_position + 1) % len(self.players)
        self._advance_to_active_player()

    def _advance_to_active_player(self):
        for _ in range(len(self.players)):
            if self.players[self.current_player_index].status == "active":
                break
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def _showdown(self):
        self.betting_round = BettingRound.SHOWDOWN
        active_players = [p for p in self.players if p.status == "active"]
        
        best_hand = None
        winner = None
        
        for p in active_players:
            hand_value = evaluate_hand(p.hand, self.community_cards)
            if best_hand is None or hand_value > best_hand:
                best_hand = hand_value
                winner = p
        
        if winner:
            winner.chips += self.pot
            self.winner = winner.id
            self.history.append(f"--- SHOWDOWN: {winner.id} wins {self.pot} ---")
        
        self.phase = GamePhase.FINISHED

    def _end_hand(self):
        active_players = [p for p in self.players if p.status == "active"]
        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.pot
            self.winner = winner.id
            self.history.append(f"{winner.id} wins {self.pot} (others folded)")
        
        self.phase = GamePhase.FINISHED

    def _check_game_end(self):
        active_players = [p for p in self.players if p.status == "active"]
        if len(active_players) <= 1:
            self._end_hand()

    def get_visible_state(self, player_id: str) -> Dict[str, Any]:
        players_state = []
        for p in self.players:
            hide_hand = (p.id != player_id)
            players_state.append(p.to_dict(hide_hand=hide_hand))
        
        my_player = next((p for p in self.players if p.id == player_id), None)
        my_hand = my_player.hand if my_player else []
        
        return {
            "players": players_state,
            "blinds": {"small": self.small_blind, "big": self.big_blind},
            "dealer_position": self.dealer_position,
            "pot": self.pot,
            "community_cards": self.community_cards,
            "your_hand": my_hand,
            "current_bet": self.current_bet,
            "betting_round": self.betting_round.value,
            "history": self.history,
        }

    @classmethod
    def get_prompt(cls) -> Dict[str, Any]:
        return {
            "description": "德州扑克博弈规则与动作规范",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": """你是一个无情的德州扑克机器。你的目标是赢取筹码。

【局势理解规范】
服务器返回的 `state` 将包含以下关键信息，请在推理时充分利用：
- `players`: 当前桌上玩家列表及其筹码量(chips)、本轮下注额(current_bet)和状态(如 active, folded)。
- `blinds`: 当前的盲注级别 (例如 {"small": 10, "big": 20})。
- `dealer_position`: 庄家(Button)位索引。
- `pot`: 当前底池总额。
- `community_cards`: 桌面公共牌。
- `your_hand`: 你的底牌。
- `current_bet`: 当前轮的最高跟注额，你需要 call 这个数值或 raise。
- `betting_round`: 当前下注轮次 (preflop, flop, turn, river)。
- `history`: 游戏历史记录。

【动作输出规范】
调用 submit_action 工具时，action_data 必须是严格的 JSON 字符串：
{
  "action": "fold, call, raise 或 check",
  "amount": "整数 (仅 raise 必填，代表加注后的总下注额)",
  "thought_process": "你的心理活动，请结合位置、盲注比例及底池赔率进行分析"
}""",
                    },
                }
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "betting_round": self.betting_round.value,
            "community_cards": self.community_cards,
            "dealer_position": self.dealer_position,
            "current_player_index": self.current_player_index,
        })
        return base
