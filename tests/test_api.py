import asyncio
import json
import httpx

BASE_URL = "http://localhost:8000"


async def test_api():
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print("=" * 60)
        print("测试 1: 初始化 MCP")
        print("=" * 60)
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("测试 2: 获取工具列表")
        print("=" * 60)
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        })
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("测试 3: 获取游戏列表 (list_games)")
        print("=" * 60)
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_games",
                "arguments": {}
            },
            "id": 3
        })
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("测试 4: 获取游戏规则 (prompts/get)")
        print("=" * 60)
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "params": {
                "name": "play_game",
                "arguments": {"game_id": "texas_holdem"}
            },
            "id": 4
        })
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("测试 5: 两个玩家加入游戏并开始对局")
        print("=" * 60)
        
        async def player_session(player_id: str):
            async with httpx.AsyncClient(timeout=30.0) as p_client:
                print(f"\n[{player_id}] 加入游戏...")
                response = await p_client.post(f"{BASE_URL}/mcp", json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "join_game",
                        "arguments": {
                            "game_id": "texas_holdem",
                            "mac_addr": player_id
                        }
                    },
                    "id": 100
                })
                result = response.json()
                print(f"[{player_id}] join_game 响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
                return result
        
        task1 = asyncio.create_task(player_session("Player_A"))
        await asyncio.sleep(0.5)
        task2 = asyncio.create_task(player_session("Player_B"))
        
        result1 = await task1
        result2 = await task2
        
        result1_data = json.loads(result1["result"]["content"][0]["text"])
        result2_data = json.loads(result2["result"]["content"][0]["text"])
        
        your_turn_player = None
        room_id = None
        if result1_data.get("status") == "your_turn":
            your_turn_player = "Player_A"
            room_id = result1_data.get("room_id")
        elif result2_data.get("status") == "your_turn":
            your_turn_player = "Player_B"
            room_id = result2_data.get("room_id")
        
        print(f"\n轮到玩家: {your_turn_player}, 房间ID: {room_id}")
        
        if your_turn_player and room_id:
            print("\n" + "=" * 60)
            print(f"测试 6: 玩家 {your_turn_player} 执行动作")
            print("=" * 60)
            
            async with httpx.AsyncClient(timeout=30.0) as p_client:
                response = await p_client.post(f"{BASE_URL}/mcp", json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "submit_action",
                        "arguments": {
                            "room_id": room_id,
                            "mac_addr": your_turn_player,
                            "action_data": json.dumps({
                                "action": "call",
                                "thought_process": "测试调用"
                            })
                        }
                    },
                    "id": 200
                })
                result = response.json()
                print(f"submit_action 响应: {json.dumps(result, indent=2, ensure_ascii=False)[:800]}...")


if __name__ == "__main__":
    asyncio.run(test_api())
