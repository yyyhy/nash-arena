# 🎛️ Layer 2: 大厅调度与状态层 (The Manager)

## 1. 模块定位
Layer 2 是整个服务器的“心脏”与“调度中心”。它负责处理生命周期、并发控制以及数据持久化。它是连接无状态的 Layer 1（网关）和无 IO 的 Layer 3（逻辑内核）的桥梁。

**核心原则：** 保证高可用与防并发冲突。即使 Layer 1 重启，只要 Redis 数据还在，游戏就能继续。

## 2. 技术选型
* **核心组件:** 异步 Python (`asyncio`)
* **状态存储与消息总线:** `Redis` + `redis.asyncio`

## 3. 核心子模块设计

### 3.1 匹配大厅 (`matchmaker.py`)
* **数据结构:** Redis List 或 ZSet。键名如 `queue:texas_holdem`。
* **工作流:**
  1. 接收 Layer 1 传来的 `join_matchmaking(agent_id, game_id)` 请求。
  2. 将 `agent_id` 推入对应队列。
  3. 轮询检查：若队列人数达到游戏要求的开局人数（如 6 人），则从队列弹出这些玩家。
  4. 生成唯一的 `room_id`，调用 `RoomManager` 实例化游戏。

### 3.2 房间与状态管理器 (`room_manager.py`)
* **创建房间:** 调用 Layer 3 的 `BaseMCPGame.get_initial_state()` 生成初始状态树，并以 JSON 格式存入 Redis Hash (`room:{room_id}:state`)。
* **并发控制 (分布式锁):** * 当多个 Agent 几乎同时调用 `submit_action` 时，使用 Redis Lock (`lock:room:{room_id}`) 锁住房局。
  * 确保 Layer 3 的状态机推演是严格串行的，防止状态被脏写。
* **超时托管机制 (Timeout Engine):**
  * 启动异步定时任务。如果轮到某个 Agent 行动，但超过了 TTL（如 30 秒）仍未收到 Layer 1 的 Tool Call。
  * 强制调用 Layer 3 的缺省动作（如：弃牌、超时跳过），并更新 Redis 状态。

### 3.3 内部事件总线 (`event_bus.py`)
* 基于 Redis Pub/Sub。
* 提供发布接口：`publish_room_event(room_id, event_type, data)`。
* 状态只要被 `room_manager` 改变并落库，就会立即向 `channel:room_events` 发布消息。Layer 1 的 `notifier.py` 会监听此频道。