# 模块二：状态与缓存层 (State & Event Layer)

## 1. 模块定位
支持高并发的核心。Redis 不仅要保存游戏的全量状态机，还要负责触发 MCP Server 的 SSE 通知推送。

## 2. 核心设计

### 2.1 游戏资源池 (Resource State)
以 Hash 结构存储房间数据，键名为 `room:{room_id}`。
这部分数据是**上帝视角的全量数据**。当某个 Agent 请求 `resources/read` 时，MCP Server 会从 Redis 取出全量数据，经过 `GamePlugin` 的战争迷雾过滤后，再返回给对应 Agent。

### 2.2 事件发布/订阅 (Pub/Sub)
* 频道：`channel:room:{room_id}:events`
* 当状态机发生流转（如某个 AI 下注成功），引擎向该频道发布事件。
* **MCP 网关监听：** 网关监听到事件后，向房间内的所有 Agent 客户端广播 SSE 通知（告知它们 `game://{room_id}/state` 这个 Resource 已经更新，可以来拉取最新数据了）。
* **Web UI 监听：** 可视化大厅直接监听此频道的全量数据，用于渲染前端动画。