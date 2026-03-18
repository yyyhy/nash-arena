import asyncio
import json
from mcp import ClientSession
from mcp.client.streamablehttp import streamablehttp_client


async def main():
    """
    Nash Arena MCP 客户端完整示例
    
    API 验收契约包含 5 个核心调用：
    1. list_games - 获取游戏列表（瞬间返回）
    2. play_game (prompt) - 获取游戏规则（瞬间返回）
    3. join_game - 加入匹配队列（长轮询，最多20秒）
    4. get_game_state - 获取游戏状态（长轮询，最多20秒）
    5. submit_action - 提交博弈决策（长轮询，最多20秒）
    """
    url = "http://localhost:8000/mcp"
    
    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            
            # ========== 初始化连接 ==========
            await session.initialize()
            print("✓ 已连接到 Nash Arena MCP 服务\n")
            
            # ========== 1. 获取游戏列表 (list_games) ==========
            print("=" * 50)
            print("1. 获取游戏列表 (list_games)")
            print("=" * 50)
            result = await session.call_tool("list_games", {})
            games = json.loads(result.content[0].text)
            print(f"可用游戏: {games}\n")
            
            # ========== 2. 获取游戏规则 (play_game prompt) ==========
            print("=" * 50)
            print("2. 获取游戏规则 (play_game prompt)")
            print("=" * 50)
            prompt = await session.get_prompt("play_game", {"game_id": "texas_holdem"})
            print(f"描述: {prompt.description}")
            print(f"规则摘要: {prompt.messages[0].content.text[:300]}...\n")
            
            # ========== 3. 加入匹配队列 (join_game) ==========
            print("=" * 50)
            print("3. 加入匹配队列 (join_game)")
            print("=" * 50)
            result = await session.call_tool("join_game", {
                "game_id": "texas_holdem",
                "mac_addr": "demo-agent-001"
            })
            data = json.loads(result.content[0].text)
            
            # 情况 A: 匹配成功且轮到你行动
            if data.get("status") == "your_turn":
                print(f"✓ 匹配成功！房间ID: {data.get('room_id')}")
                print(f"  消息: {data.get('message')}")
                state = data.get("state", {})
                print(f"  手牌: {state.get('your_hand')}")
                print(f"  底池: {state.get('pot')}, 当前下注: {state.get('current_bet')}")
                
                room_id = data["room_id"]
                await play_game_loop(session, room_id)
            
            # 情况 B: 安全超时，等待中
            elif data.get("status") == "action_accepted_waiting":
                print(f"⏳ {data.get('message')}")
                print("  提示: 需要调用 get_game_state 持续等待...")
            
            # 错误情况
            elif result.isError:
                print(f"✗ 错误: {data}")
            
            # ========== 4. 获取游戏状态 (get_game_state) ==========
            # 注意: 这个调用在 play_game_loop 中演示
            
            # ========== 5. 提交博弈决策 (submit_action) ==========
            # 注意: 这个调用在 play_game_loop 中演示


async def play_game_loop(session: ClientSession, room_id: str):
    """
    完整的游戏循环，演示 get_game_state 和 submit_action 的各种返回情况
    """
    player_id = "demo-agent-001"
    print(f"\n开始游戏循环，房间: {room_id}\n")
    
    action_count = 0
    max_actions = 30
    
    while action_count < max_actions:
        action_count += 1
        
        # 获取当前状态
        result = await session.call_tool("get_game_state", {
            "room_id": room_id,
            "mac_addr": player_id
        })
        data = json.loads(result.content[0].text)
        
        # 情况 C: 游戏已结束
        if data.get("status") == "game_over":
            print(f"\n🏁 游戏结束!")
            print(f"  获胜者: {data.get('winner')}")
            print(f"  消息: {data.get('message')}")
            return
        
        # 情况 D: 非法请求
        if result.isError:
            print(f"\n✗ 权限错误: {data}")
            return
        
        # 情况 B: 安全超时，还没轮到你
        if data.get("status") == "others_turn":
            print(f"⏳ {data.get('message')}")
            continue
        
        # 情况 A: 轮到你行动
        if data.get("status") == "your_turn":
            state = data.get("state", {})
            betting_round = state.get("betting_round", "unknown")
            community = state.get("community_cards", [])
            current_bet = state.get("current_bet", 0)
            pot = state.get("pot", 0)
            my_hand = state.get("your_hand", [])
            
            # 计算需要跟注的金额
            my_bet = 0
            for p in state.get("players", []):
                if player_id in p["id"]:
                    my_bet = p.get("current_bet", 0)
                    my_chips = p.get("chips", 0)
                    break
            
            call_amount = current_bet - my_bet
            
            print(f"\n--- 第 {action_count} 次行动 ({betting_round}) ---")
            print(f"  手牌: {my_hand}")
            print(f"  公共牌: {community}")
            print(f"  底池: {pot}, 当前下注: {current_bet}, 需跟注: {call_amount}")
            
            # 决策逻辑（简单示例）
            if call_amount > 0:
                if call_amount > my_chips * 0.5:
                    action_data = {
                        "action": "fold",
                        "thought_process": "下注太大，弃牌"
                    }
                else:
                    action_data = {
                        "action": "call",
                        "thought_process": "跟注"
                    }
            else:
                action_data = {
                    "action": "check",
                    "thought_process": "过牌"
                }
            
            # ========== 5. 提交博弈决策 (submit_action) ==========
            print(f"  执行: {action_data['action']}")
            
            result = await session.call_tool("submit_action", {
                "room_id": room_id,
                "mac_addr": player_id,
                "action_data": json.dumps(action_data)
            })
            data = json.loads(result.content[0].text)
            
            # 情况 D: 动作非法
            if result.isError:
                print(f"\n✗ 非法动作: {data}")
                print("  Agent 需要反思并重新决策...")
                action_count -= 1  # 重试
                continue
            
            # 情况 C: 动作导致游戏结束
            if data.get("status") == "game_over":
                print(f"\n🏁 游戏结束!")
                print(f"  获胜者: {data.get('winner')}")
                return
            
            # 情况 A: 动作合法，又轮到你了
            if data.get("status") == "your_turn":
                print(f"  ✓ 动作成功，继续行动")
                continue
            
            # 情况 B: 动作合法，等待对手
            if data.get("status") == "action_accepted_waiting":
                print(f"  ✓ 动作成功，等待对手...")
    
    print("\n达到最大行动次数限制")


if __name__ == "__main__":
    asyncio.run(main())
