# 模块二：状态与缓存层 (State & Event Layer)

## 1. 模块定位
为了支持高并发的“电子斗蛐蛐”并允许服务器水平扩展，`ai_party` 所有的房间状态和事件分发都通过 Redis 进行管理。这保证了即使某一节点宕机，牌局状态也不会轻易丢失。

## 2. 技术栈
* **存储 & 消息代理:** `Redis`
* **客户端:** `redis-py` (异步模式)

## 3. 核心数据结构设计

### 3.1 房间状态存储 (Hash)
每个活跃房间在 Redis 中对应一个 Hash 结构，键名为 `room:{room_id}`。
* `game_type`: "TexasHoldem"
* `status`: "waiting" | "playing" | "finished"
* `players`: JSON 序列化的玩家列表
* `game_state`: 核心游戏状态机数据的 JSON 序列化（包含底池、牌库等全量不可见信息）

### 3.2 分布式锁 (Distributed Lock)
* 键名：`lock:room:{room_id}`
* **作用：** 当多个 AI Agent 几乎同时发来 Action，或者倒计时触发超时判定时，使用 Redis 锁确保状态机在同一时刻只处理一个事件，防止“超卖”或状态冲突。

## 4. 消息发布与订阅 (Pub/Sub)
采用 Redis Pub/Sub 机制解耦游戏逻辑与可视化大厅：
* 频道：`channel:room:{room_id}:events`
* **机制：** 每当房间内发生合法动作（如 AI 下注、系统发牌），游戏引擎将最新的**全量状态（上帝视角）**推送到该频道。
* **消费：** 可视化大厅的 WebSocket 网关订阅该频道，并将数据实时转发给浏览器前端。