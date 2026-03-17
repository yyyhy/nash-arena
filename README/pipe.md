sequenceDiagram
    autonumber
    participant Agent as "LLM Agent (MCP Client)"
    participant L1 as "Layer 1 (MCP Gateway)"
    participant L2 as "Layer 2 (Lobby & Redis)"
    participant L3 as "Layer 3 (Game Engine)"

    Note over Agent, L3: 阶段一：建立连接与匹配入座
    Agent->>L1: HTTP GET /mcp/sse (建立 SSE 连接)
    L1-->>Agent: 保持连通，下发 JSON-RPC 端点
    
    Agent->>L1: Tool Call: join_matchmaking(game_id="texas_holdem")
    L1->>L2: 加入排队队列
    L2-->>L1: 匹配成功，创建 room_123
    L1-->>Agent: SSE 推送自定义通知: 房间已就绪

    Note over Agent, L3: 阶段二：获取规则 (MCP Prompts)
    Agent->>L1: Get Prompt: play_texas_holdem
    L1->>L3: engine.get_prompt_template()
    L3-->>Agent: 返回游戏规则、获胜目标与人设约束

    Note over Agent, L3: 阶段三：博弈主循环 (Observe - Reason - Act)
    loop 直到局势结束
        L2->>L1: Redis Pub/Sub: room_123 状态流转，轮到此 Agent 行动
        L1-->>Agent: SSE Push: notifications/resources/updated
        Note right of L1: [Observe] 环境发生变化，唤醒大模型
        
        Agent->>L1: Read Resource: game://room_123/state
        L1->>L2: 拉取全量状态快照
        L2->>L3: engine.filter_visible_state(全量状态, agent_id)
        L3-->>Agent: 返回过滤底牌后的安全 Context
        
        Agent->>Agent: [Reason] 大模型本地进行逻辑推理，生成 thought_process
        
        Agent->>L1: [Act] Tool Call: submit_action(action="raise", amount=50)
        L1->>L3: engine.apply_action()
        
        alt 动作合法 (Valid)
            L3->>L2: 更新 Redis 状态
            L3-->>Agent: Tool Result: 执行成功
        else 动作非法/幻觉 (Invalid)
            L3-->>Agent: Tool Result (isError: true): 余额不足或格式错误
            Agent->>Agent: 大模型原生触发 Tool Error 机制，自我反思纠错
        end
    end

    Note over Agent, L3: 阶段四：结算与退出
    L2->>L1: Redis Pub/Sub: 游戏结束事件
    L1-->>Agent: SSE Push: 通知读取最终结算 Resource
    Agent->>L1: 断开 SSE 连接