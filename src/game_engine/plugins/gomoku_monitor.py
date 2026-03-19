from typing import Any, Dict
from ..base_monitor import BaseGameMonitor, MonitorEvent, MonitorEventType

class GomokuMonitor(BaseGameMonitor):
    game_id: str = "gomoku"
    
    def get_full_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        # 五子棋是完全信息博弈，上帝视角和普通视角相同
        return game_state
        
    def get_public_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        # 五子棋没有隐藏信息
        return game_state
        
    def format_event(self, event: MonitorEvent) -> Dict[str, Any]:
        return {
            "type": event.event_type.value,
            "timestamp": event.timestamp,
            "data": event.data
        }
        
    def get_ui_config(self) -> Dict[str, Any]:
        return {
            "layout": "board",
            "theme": "wood",
            "custom_css": """
                .gomoku-board {
                    display: grid;
                    grid-template-columns: repeat(15, 30px);
                    grid-template-rows: repeat(15, 30px);
                    gap: 1px;
                    background-color: #dcb35c;
                    padding: 10px;
                    border-radius: 4px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    margin: 0 auto;
                    width: max-content;
                }
                .gomoku-cell {
                    width: 30px;
                    height: 30px;
                    background-color: #e6c27a;
                    position: relative;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .gomoku-cell::before {
                    content: '';
                    position: absolute;
                    top: 50%;
                    left: 0;
                    right: 0;
                    height: 1px;
                    background-color: #000;
                    z-index: 1;
                }
                .gomoku-cell::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    bottom: 0;
                    left: 50%;
                    width: 1px;
                    background-color: #000;
                    z-index: 1;
                }
                .gomoku-piece {
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    z-index: 2;
                    box-shadow: 1px 1px 3px rgba(0,0,0,0.5);
                }
                .piece-black {
                    background: radial-gradient(circle at 30% 30%, #666, #000);
                }
                .piece-white {
                    background: radial-gradient(circle at 30% 30%, #fff, #ccc);
                }
                .gomoku-players {
                    display: flex;
                    justify-content: center;
                    gap: 40px;
                    margin-bottom: 20px;
                }
                .player-badge {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 16px;
                    background: var(--bg-secondary);
                    border-radius: 20px;
                    border: 1px solid var(--border-color);
                }
                .player-badge.active {
                    border-color: var(--accent-gold);
                    box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
                }
                .badge-color {
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                }
            """,
            "render_script": """
                return function(state) {
                    const board = state.board || [];
                    const players = state.players || [];
                    const currentPlayer = state.current_player;
                    
                    let playersHtml = '<div class="gomoku-players">';
                    players.forEach(p => {
                        const isTurn = p.id === currentPlayer;
                        const badgeClass = p.color === 'black' ? 'piece-black' : 'piece-white';
                        playersHtml += `
                            <div class="player-badge ${isTurn ? 'active' : ''}">
                                <div class="badge-color ${badgeClass}"></div>
                                <span style="font-weight: bold;">${p.id}</span>
                                <span style="color: var(--text-muted); font-size: 12px;">(${p.color})</span>
                            </div>
                        `;
                    });
                    playersHtml += '</div>';

                    let boardHtml = '<div class="gomoku-board">';
                    for (let r = 0; r < 15; r++) {
                        for (let c = 0; c < 15; c++) {
                            // 为了确保坐标不产生冲突，比如 (1, 1) 和 (11, 1) 都能被匹配到 `placed at (1, 1)`，
                            // 我们必须使用正则进行精确匹配
                            let cell = 'empty';
                            const history = state.history || [];
                            // 正则匹配: 确保括号内就是我们想要的行和列，并且以 ) 结尾或逗号分隔
                            const targetPattern = `placed at (${r}, ${c})`;
                            for (let i = 0; i < history.length; i++) {
                                const h = history[i];
                                // 去除可能存在的 HTML 标签，因为在前端可能会被包裹在 <span> 里
                                const cleanH = h.replace(/<[^>]*>?/gm, '');
                                if (cleanH.includes(targetPattern)) {
                                    if (cleanH.includes('(Black)')) cell = 'black';
                                    if (cleanH.includes('(White)')) cell = 'white';
                                }
                            }
                            
                            let pieceHtml = '';
                            if (cell === 'black') {
                                pieceHtml = '<div class="gomoku-piece piece-black"></div>';
                            } else if (cell === 'white') {
                                pieceHtml = '<div class="gomoku-piece piece-white"></div>';
                            }
                            
                            // 渲染坐标提示 (optional, simple title attribute for debugging)
                            boardHtml += `<div class="gomoku-cell" title="(${r}, ${c})">${pieceHtml}</div>`;
                        }
                    }
                    boardHtml += '</div>';

                    return `
                        <div style="display: flex; flex-direction: column; align-items: center;">
                            ${playersHtml}
                            ${boardHtml}
                        </div>
                    `;
                }
            """
        }
