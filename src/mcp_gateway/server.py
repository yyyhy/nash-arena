import json
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..lobby_manager.matchmaker import Matchmaker
from ..web_observer.monitor_api import router as monitor_router, init_monitor_api
# from ..data_storage.stats_api import router as stats_router


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[int] = None


class MCPTool:
    def __init__(self, name: str, description: str, input_schema: Dict):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MCPPrompt:
    def __init__(self, name: str, description: str, arguments: List[Dict]):
        self.name = name
        self.description = description
        self.arguments = arguments


class MCPGateway:
    def __init__(self):
        self.app = FastAPI(title="Nash Arena")
        self.matchmaker = Matchmaker()
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        init_monitor_api(self.matchmaker)
        self.app.include_router(monitor_router)
        # self.app.include_router(stats_router)
        
        self._setup_routes()
        self._setup_tools()
        self._setup_prompts()

    def _setup_tools(self):
        self.tools = {
            "list_games": MCPTool(
                name="list_games",
                description="获取当前大厅可用的游戏列表",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            "join_game": MCPTool(
                name="join_game",
                description="加入游戏匹配队列。这是一个长轮询接口，会阻塞等待直到匹配成功且轮到你行动，或超时返回。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "string", "description": "要加入的游戏ID"},
                        "mac_addr": {"type": "string", "description": "玩家唯一标识符"},
                    },
                    "required": ["game_id", "mac_addr"],
                },
            ),
            "get_game_state": MCPTool(
                name="get_game_state",
                description="获取当前游戏状态。这是一个长轮询接口，会阻塞等待直到轮到你行动或游戏结束。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string", "description": "房间ID"},
                        "mac_addr": {"type": "string", "description": "玩家唯一标识符"},
                    },
                    "required": ["room_id", "mac_addr"],
                },
            ),
            "submit_action": MCPTool(
                name="submit_action",
                description="提交博弈决策。这是一个长轮询接口，执行动作后会等待下一次轮到你或游戏结束。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string", "description": "房间ID"},
                        "mac_addr": {"type": "string", "description": "玩家唯一标识符"},
                        "action_data": {
                            "type": "string",
                            "description": "动作数据JSON字符串，包含action, amount(可选), thought_process",
                        },
                    },
                    "required": ["room_id", "mac_addr", "action_data"],
                },
            ),
            "get_player_stats": MCPTool(
                name="get_player_stats",
                description="获取玩家的战绩统计。返回胜率、总场次、净赢筹码等统计数据。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "mac_addr": {"type": "string", "description": "玩家唯一标识符"},
                        "game_id": {"type": "string", "description": "游戏ID（可选，不填则返回所有游戏的统计）"},
                    },
                    "required": ["mac_addr"],
                },
            ),
            "get_player_records": MCPTool(
                name="get_player_records",
                description="获取玩家的历史对局记录。返回最近的对局详情列表。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "mac_addr": {"type": "string", "description": "玩家唯一标识符"},
                        "game_id": {"type": "string", "description": "游戏ID（可选，不填则返回所有游戏的记录）"},
                        "limit": {"type": "integer", "description": "返回记录数量限制，默认50", "default": 50},
                        "offset": {"type": "integer", "description": "分页偏移量，默认0", "default": 0},
                    },
                    "required": ["mac_addr"],
                },
            ),
            "get_leaderboard": MCPTool(
                name="get_leaderboard",
                description="获取游戏排行榜。按胜场、胜率或净赢筹码排序。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "string", "description": "游戏ID"},
                        "sort_by": {"type": "string", "description": "排序方式：wins(胜场)、win_rate(胜率)、net_chips(净赢筹码)", "default": "wins"},
                        "limit": {"type": "integer", "description": "返回数量限制，默认10", "default": 10},
                    },
                    "required": ["game_id"],
                },
            ),
        }

    def _setup_prompts(self):
        self.prompts = {
            "play_game": MCPPrompt(
                name="play_game",
                description="获取指定游戏的规则、系统提示词和输出规范",
                arguments=[
                    {
                        "name": "game_id",
                        "description": "游戏ID",
                        "required": True,
                    }
                ],
            ),
        }

    def _setup_routes(self):
        @self.app.post("/mcp")
        async def handle_mcp_request(request: Request):
            body = await request.json()
            return await self._handle_jsonrpc(body)

        @self.app.get("/mcp/tools")
        async def list_tools():
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                    for tool in self.tools.values()
                ]
            }

        @self.app.get("/mcp/prompts")
        async def list_prompts():
            return {
                "prompts": [
                    {
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments,
                    }
                    for prompt in self.prompts.values()
                ]
            }

    async def _handle_jsonrpc(self, request: Dict) -> JSONResponse:
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "prompts/list":
                result = await self._handle_prompts_list()
            elif method == "prompts/get":
                result = await self._handle_prompts_get(params)
            elif method == "initialize":
                result = await self._handle_initialize()
            else:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                        "id": request_id,
                    }
                )

            return JSONResponse({"jsonrpc": "2.0", "result": result, "id": request_id})

        except Exception as e:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request_id,
                }
            )

    async def _handle_initialize(self) -> Dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": "nash-arena",
                "version": "1.0.0",
            },
        }

    async def _handle_tools_list(self) -> Dict:
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
                for tool in self.tools.values()
            ]
        }

    async def _handle_prompts_list(self) -> Dict:
        return {
            "prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments,
                }
                for prompt in self.prompts.values()
            ]
        }

    async def _handle_tools_call(self, params: Dict) -> Dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "list_games":
            return await self._tool_list_games()
        elif tool_name == "join_game":
            return await self._tool_join_game(arguments)
        elif tool_name == "get_game_state":
            return await self._tool_get_game_state(arguments)
        elif tool_name == "submit_action":
            return await self._tool_submit_action(arguments)
        elif tool_name == "get_player_stats":
            return await self._tool_get_player_stats(arguments)
        elif tool_name == "get_player_records":
            return await self._tool_get_player_records(arguments)
        elif tool_name == "get_leaderboard":
            return await self._tool_get_leaderboard(arguments)
        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }

    async def _handle_prompts_get(self, params: Dict) -> Dict:
        prompt_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if prompt_name == "play_game":
            game_id = arguments.get("game_id", "")
            prompt_data = self.matchmaker.get_game_prompt(game_id)
            if prompt_data:
                return prompt_data
            return {
                "description": "游戏不存在",
                "messages": [
                    {
                        "role": "system",
                        "content": {"type": "text", "text": f"未找到游戏: {game_id}"},
                    }
                ],
            }
        else:
            return {
                "description": "Prompt not found",
                "messages": [
                    {
                        "role": "system",
                        "content": {"type": "text", "text": f"Unknown prompt: {prompt_name}"},
                    }
                ],
            }

    async def _tool_list_games(self) -> Dict:
        games = self.matchmaker.list_games()
        return {
            "content": [{"type": "text", "text": json.dumps(games, ensure_ascii=False)}],
            "isError": False,
        }

    async def _tool_join_game(self, arguments: Dict) -> Dict:
        game_id = arguments.get("game_id", "")
        mac_addr = arguments.get("mac_addr", "")

        result = await self.matchmaker.join_game(game_id, mac_addr)

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": result.get("is_error", False),
        }

    async def _tool_get_game_state(self, arguments: Dict) -> Dict:
        room_id = arguments.get("room_id", "")
        mac_addr = arguments.get("mac_addr", "")

        result = await self.matchmaker.get_game_state(room_id, mac_addr)

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": result.get("is_error", False),
        }

    async def _tool_submit_action(self, arguments: Dict) -> Dict:
        room_id = arguments.get("room_id", "")
        mac_addr = arguments.get("mac_addr", "")
        action_data = arguments.get("action_data", "{}")

        result = await self.matchmaker.submit_action(room_id, mac_addr, action_data)

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": result.get("is_error", False),
        }

    async def _tool_get_player_stats(self, arguments: Dict) -> Dict:
        mac_addr = arguments.get("mac_addr", "")
        game_id = arguments.get("game_id")

        result = self.matchmaker.get_player_stats(mac_addr, game_id)

        if result is None:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "未找到该玩家的战绩数据"}, ensure_ascii=False)}],
                "isError": True,
            }

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": False,
        }

    async def _tool_get_player_records(self, arguments: Dict) -> Dict:
        mac_addr = arguments.get("mac_addr", "")
        game_id = arguments.get("game_id")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)

        result = self.matchmaker.get_player_records(mac_addr, game_id, limit, offset)

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": False,
        }

    async def _tool_get_leaderboard(self, arguments: Dict) -> Dict:
        game_id = arguments.get("game_id", "")
        sort_by = arguments.get("sort_by", "wins")
        limit = arguments.get("limit", 10)

        result = self.matchmaker.get_leaderboard(game_id, sort_by, limit)

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": False,
        }
