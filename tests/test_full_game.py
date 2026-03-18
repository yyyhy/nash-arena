import asyncio
import json
import httpx

BASE_URL = "http://localhost:8008"


async def player_bot(player_id: str, client: httpx.AsyncClient):
    print(f"[{player_id}] 加入游戏...")
    response = await client.post(f"{BASE_URL}/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "join_game",
            "arguments": {
                "game_id": "texas_holdem",
                "mac_addr": player_id
            }
        },
        "id": 1
    })
    result = response.json()["result"]
    data = json.loads(result["content"][0]["text"])
    
    if data.get("status") == "your_turn":
        print(f"[{player_id}] 匹配成功，轮到我行动！")
        print(f"[{player_id}] 手牌: {data['state']['your_hand']}")
        print(f"[{player_id}] 底池: {data['state']['pot']}, 当前下注: {data['state']['current_bet']}")
        return data.get("room_id"), data
    else:
        print(f"[{player_id}] 等待中: {data.get('message')}")
        return data.get("room_id"), None


async def wait_for_turn(player_id: str, room_id: str, client: httpx.AsyncClient):
    print(f"[{player_id}] 等待轮次...")
    response = await client.post(f"{BASE_URL}/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_game_state",
            "arguments": {
                "room_id": room_id,
                "mac_addr": player_id
            }
        },
        "id": 2
    })
    result = response.json()["result"]
    data = json.loads(result["content"][0]["text"])
    
    if data.get("status") == "your_turn":
        print(f"[{player_id}] 轮到我行动！")
        print(f"[{player_id}] 手牌: {data['state']['your_hand']}")
        print(f"[{player_id}] 公共牌: {data['state']['community_cards']}")
        print(f"[{player_id}] 底池: {data['state']['pot']}, 当前下注: {data['state']['current_bet']}")
        return data
    elif data.get("status") == "game_over":
        print(f"[{player_id}] 游戏结束！获胜者: {data.get('winner')}")
        return data
    else:
        print(f"[{player_id}] 继续等待: {data.get('message')}")
        return None


async def make_action(player_id: str, room_id: str, action: str, amount: int, client: httpx.AsyncClient):
    print(f"[{player_id}] 执行动作: {action}" + (f" {amount}" if amount else ""))
    response = await client.post(f"{BASE_URL}/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "submit_action",
            "arguments": {
                "room_id": room_id,
                "mac_addr": player_id,
                "action_data": json.dumps({
                    "action": action,
                    "amount": amount,
                    "thought_process": f"{player_id} 的决策"
                })
            }
        },
        "id": 3
    })
    result = response.json()["result"]
    data = json.loads(result["content"][0]["text"])
    
    if data.get("status") == "your_turn":
        print(f"[{player_id}] 动作成功，又轮到我了！")
        return data
    elif data.get("status") == "game_over":
        print(f"[{player_id}] 游戏结束！获胜者: {data.get('winner')}")
        return data
    else:
        print(f"[{player_id}] 动作成功，等待对手: {data.get('message')}")
        return None


async def player_game_loop(player_id: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        room_id, initial_state = await player_bot(player_id, client)
        
        if not room_id:
            print(f"[{player_id}] 未获取到房间ID")
            return
        
        current_state = initial_state
        
        while True:
            if current_state and current_state.get("status") == "your_turn":
                state = current_state.get("state", {})
                current_bet = state.get("current_bet", 0)
                my_bet = 0
                for p in state.get("players", []):
                    if p["id"] == player_id:
                        my_bet = p.get("current_bet", 0)
                        break
                
                call_amount = current_bet - my_bet
                
                if call_amount == 0:
                    action, amount = "check", 0
                else:
                    action, amount = "call", 0
                
                current_state = await make_action(player_id, room_id, action, amount, client)
                
                if current_state and current_state.get("status") == "game_over":
                    break
            else:
                current_state = await wait_for_turn(player_id, room_id, client)
                
                if current_state and current_state.get("status") == "game_over":
                    break
            
            if current_state is None:
                break


async def main():
    print("=" * 60)
    print("完整游戏流程测试")
    print("=" * 60)
    
    task1 = asyncio.create_task(player_game_loop("Alice"))
    await asyncio.sleep(0.3)
    task2 = asyncio.create_task(player_game_loop("Bob"))
    
    await asyncio.gather(task1, task2)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
