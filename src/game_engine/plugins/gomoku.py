from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from ..base_game import BaseMCPGame, GamePhase, Player, GameAction


class BoardPiece(str, Enum):
    EMPTY = "empty"
    BLACK = "black"
    WHITE = "white"


class Gomoku(BaseMCPGame):
    game_id: str = "gomoku"
    name: str = "五子棋"
    min_players: int = 2
    max_players: int = 2

    def __init__(self, room_id: str):
        super().__init__(room_id)
        # 15x15 board is standard for Gomoku
        self.board_size = 15
        self.board: List[List[BoardPiece]] = [
            [BoardPiece.EMPTY for _ in range(self.board_size)]
            for _ in range(self.board_size)
        ]
        self.current_player_index = 0
        self.player_colors: Dict[str, BoardPiece] = {}

    def add_player(self, player_id: str) -> bool:
        if len(self.players) >= self.max_players:
            return False
        if any(p.id == player_id for p in self.players):
            return False
        self.players.append(Player(id=player_id, chips=0))
        return True

    def start_game(self) -> bool:
        if len(self.players) != self.min_players:
            return False
        self.phase = GamePhase.IN_PROGRESS
        
        # First player is Black (goes first), second is White
        self.player_colors[self.players[0].id] = BoardPiece.BLACK
        self.player_colors[self.players[1].id] = BoardPiece.WHITE
        self.current_player_index = 0
        
        self.history.append("Game started. Black goes first.")
        return True

    def get_current_player(self) -> Optional[str]:
        if self.phase != GamePhase.IN_PROGRESS:
            return None
        return self.players[self.current_player_index].id

    def is_player_turn(self, player_id: str) -> bool:
        return self.get_current_player() == player_id

    def apply_action(self, player_id: str, action: GameAction) -> Dict[str, Any]:
        if self.phase != GamePhase.IN_PROGRESS:
            return {"success": False, "error": "游戏未在进行中"}
        if not self.is_player_turn(player_id):
            return {"success": False, "error": "现在不是你的回合"}

        if action.action != "place":
            return {"success": False, "error": "无效的动作，五子棋只能执行 'place' 动作"}

        # Action amount is not used, we need coordinates
        # Expecting thought_process to optionally contain logic, but we need x, y
        # We will parse action.amount as a single integer encoding: y * board_size + x
        # Alternatively, we could update GameAction to take kwargs, but to stick to the contract, 
        # let's use amount = row * 15 + col
        try:
            # 兼容前端或 Agent 传来的浮点数
            amount_int = int(action.amount)
            row = amount_int // self.board_size
            col = amount_int % self.board_size
        except Exception:
            return {"success": False, "error": f"坐标解析失败: amount={action.amount}"}

        if row < 0 or row >= self.board_size or col < 0 or col >= self.board_size:
            return {"success": False, "error": f"坐标 ({row}, {col}) 超出棋盘范围 (0-14)"}

        if self.board[row][col] != BoardPiece.EMPTY:
            return {"success": False, "error": f"坐标 ({row}, {col}) 已经有棋子了"}

        color = self.player_colors[player_id]
        self.board[row][col] = color
        
        color_name = "Black" if color == BoardPiece.BLACK else "White"
        self.history.append(f"{player_id} ({color_name}) placed at ({row}, {col})")
        if action.thought_process:
            self.history.append(f"[THOUGHT] {player_id}: {action.thought_process}")

        if self._check_win(row, col, color):
            self.phase = GamePhase.FINISHED
            self.winner = player_id
            self.history.append(f"Game Over. {player_id} wins!")
        elif self._check_draw():
            self.phase = GamePhase.FINISHED
            self.winner = "Draw"
            self.history.append("Game Over. It's a draw!")
        else:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

        return {"success": True}

    def _check_win(self, row: int, col: int, color: BoardPiece) -> bool:
        directions = [
            (0, 1),   # Horizontal
            (1, 0),   # Vertical
            (1, 1),   # Diagonal right-down
            (1, -1)   # Diagonal left-down
        ]
        
        for dr, dc in directions:
            count = 1
            # Check one way
            r, c = row + dr, col + dc
            while 0 <= r < self.board_size and 0 <= c < self.board_size and self.board[r][c] == color:
                count += 1
                r += dr
                c += dc
            # Check opposite way
            r, c = row - dr, col - dc
            while 0 <= r < self.board_size and 0 <= c < self.board_size and self.board[r][c] == color:
                count += 1
                r -= dr
                c -= dc
                
            if count >= 5:
                return True
        return False

    def _check_draw(self) -> bool:
        for r in range(self.board_size):
            for c in range(self.board_size):
                if self.board[r][c] == BoardPiece.EMPTY:
                    return False
        return True

    def get_visible_state(self, player_id: str) -> Dict[str, Any]:
        # 战争迷雾：过滤掉对手的思考过程
        visible_history = []
        for h in self.history:
            if h.startswith("[THOUGHT]"):
                if h.startswith(f"[THOUGHT] {player_id}:"):
                    visible_history.append(f"(思考: {h.split(': ', 1)[1]})")
            elif h.startswith("(思考:"):
                # 如果历史记录中已经混入了不带 ID 的普通思考记录，直接丢弃
                continue
            else:
                visible_history.append(h)
                
        players_state = []
        for p in self.players:
            players_state.append({
                "id": p.id,
                "color": self.player_colors.get(p.id, BoardPiece.EMPTY).value
            })

        # Serialize board to simple 2D list of strings
        board_state = [[cell.value if isinstance(cell, BoardPiece) else cell for cell in row] for row in self.board]

        return {
            "board_size": self.board_size,
            "board": board_state,
            "players": players_state,
            "current_player": self.get_current_player(),
            "history": visible_history,
        }

    def get_results(self) -> Dict[str, Dict]:
        results = {}
        for p in self.players:
            results[p.id] = {"net_chips": 0}
            
        if self.winner and self.winner != "Draw":
            results[self.winner]["net_chips"] = 10  # Win +10 points
            loser = next((p.id for p in self.players if p.id != self.winner), None)
            if loser:
                results[loser]["net_chips"] = -10 # Lose -10 points
                
        return results

    @classmethod
    def get_prompt(cls) -> Dict[str, Any]:
        return {
            "description": "五子棋规则与动作规范",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": (
                            "你是一个五子棋（Gomoku）AI玩家。游戏在15x15的棋盘上进行，黑子先手。\n"
                            "目标是让自己的5个棋子在横、竖或斜方向上连成一线。\n"
                            "状态格式说明：\n"
                            "- `board`: 15x15的二维数组，值为 'empty', 'black', 'white'\n"
                            "- `players`: 包含玩家ID和颜色的列表\n"
                            "- `current_player`: 当前轮到行动的玩家ID\n"
                            "- `history`: 包含对局的动作历史，你只能看到自己的历史思考过程，看不到对手的思考过程，这就是所谓的“战争迷雾”。\n"
                            "动作规范：\n"
                            "为了落子，你需要返回 JSON 格式的动作。\n"
                            "动作类型 `action` 必须是 'place'。\n"
                            "`amount` 字段用于传递坐标，计算公式为：amount = 行(row) * 15 + 列(col)。\n"
                            "例如，想在 第7行第7列(中心点) 落子，amount = 7 * 15 + 7 = 112。\n"
                            "请在 `thought_process` 中简要说明你为什么选择这个坐标（如防守、进攻等）。"
                        )
                    }
                }
            ]
        }
