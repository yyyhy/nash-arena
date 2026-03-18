import json
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..lobby_manager.matchmaker import Matchmaker
from ..web_observer.monitor_api import router as monitor_router, init_monitor_api


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
