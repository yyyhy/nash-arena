import asyncio
import json
import httpx

BASE_URL = "http://localhost:8000"


async def test_game():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("测试 API 验收契约")
        print("=" * 60)
        
        print("\n1. 初始化 MCP")
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
        print(f"✓ 初始化成功")
        
        print("\n2. 获取游戏列表 (list_games)")
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_games", "arguments": {}},
            "id": 2
        })
        games = json.loads(response.json()["result"]["content"][0]["text"])
        print(f"✓ 可用游戏: {games}")
        
        print("\n3. 获取游戏规则 (prompts/get)")
        response = await client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "params": {"name": "play_game", "arguments": {"game_id": "texas_holdem"}},
            "id": 3
        })
        prompt = response.json()["result"]
        print(f"✓ 规则描述: {prompt['description'][:50]}...")
        
        print("\n4. 两个玩家加入游戏")
        
        results = {}
        
        async def join_and_play(player_id: str):
            async with httpx.AsyncClient(timeout=30.0) as p_client:
                response = await p_client.post(f"{BASE_URL}/mcp", json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "join_game",
                        "arguments": {"game_id": "texas_holdem", "mac_addr": player_id}
                    },
                    "id": 10
                })
                result = json.loads(response.json()["result"]["content"][0]["text"])
                results[player_id] = result
                
                if result.get("status") == "your_turn":
                    state = result.get("state", {})
                    print(f"✓ [{player_id}] 匹配成功，轮到我行动！")
                    print(f"  手牌: {state.get('your_hand')}")
                    print(f"  玩家状态: {[(p['id'], p['current_bet'], p['status']) for p in state.get('players', [])]}")
                    print(f"  底池: {state.get('pot')}, 当前下注: {state.get('current_bet')}")
                    print(f"  庄家位置: {state.get('dealer_position')}")
                    
                    room_id = result["room_id"]
                    
                    action_count = 0
                    max_actions = 20
                    
                    while action_count < max_actions:
                        action_count += 1
                        state = result.get("state", {})
                        betting_round = state.get("betting_round", "unknown")
                        community = state.get("community_cards", [])
                        
                        my_bet = 0
                        for p in state.get("players", []):
                            if p["id"] == player_id:
                                my_bet = p.get("current_bet", 0)
                                break
                        
                        current_bet = state.get("current_bet", 0)
                        call_amount = current_bet - my_bet
                        
                        print(f"  [{player_id}] Action #{action_count}: {betting_round}, 公共牌: {community}, 需要call: {call_amount}")
                        
                        if call_amount > 0:
                            action_data = {"action": "call", "thought_process": "测试call"}
                        else:
                            action_data = {"action": "check", "thought_process": "测试check"}
                        
                        response = await p_client.post(f"{BASE_URL}/mcp", json={
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {
                                "name": "submit_action",
                                "arguments": {
                                    "room_id": room_id,
                                    "mac_addr": player_id,
                                    "action_data": json.dumps(action_data)
                                }
                            },
                            "id": 100 + action_count
                        })
                        result = json.loads(response.json()["result"]["content"][0]["text"])
                        
                        if result.get("status") == "game_over":
                            print(f"✓ [{player_id}] 游戏结束！获胜者: {result.get('winner')}")
                            return
                        
                        if result.get("status") == "your_turn":
                            continue
                        
                        if result.get("isError"):
                            print(f"✗ [{player_id}] 错误: {result.get('content', [{}])[0].get('text', 'unknown')}")
                            return
                        
                        print(f"  [{player_id}] 等待对手...")
                        
                        response = await p_client.post(f"{BASE_URL}/mcp", json={
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {
                                "name": "get_game_state",
                                "arguments": {"room_id": room_id, "mac_addr": player_id}
                            },
                            "id": 200 + action_count
                        })
                        result = json.loads(response.json()["result"]["content"][0]["text"])
                        
                        if result.get("status") == "game_over":
                            print(f"✓ [{player_id}] 游戏结束！获胜者: {result.get('winner')}")
                            return
                        
                        if result.get("status") == "your_turn":
                            continue
                            
                    print(f"✗ [{player_id}] 达到最大行动次数限制")
                else:
                    print(f"✓ [{player_id}] 等待中: {result.get('message', 'unknown')}")
        
        task1 = asyncio.create_task(join_and_play("Alice"))
        await asyncio.sleep(0.3)
        task2 = asyncio.create_task(join_and_play("Bob"))
        
        try:
            await asyncio.wait_for(asyncio.gather(task1, task2), timeout=25)
        except asyncio.TimeoutError:
            print("\n测试超时")
        
        print("\n" + "=" * 60)
        print("API 验收契约测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_game())
