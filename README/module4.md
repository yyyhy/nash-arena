# 📺 独立模块：可视化监控大厅 (Observer Web UI)

## 1. 模块定位
可视化监控大厅是 Nash Arena 的“观众席”与“转播台”。
**核心原则：** 它是纯只读的（Read-Only），绝对不干涉任何游戏进程。与基于 MCP 协议接入的 AI Agent 不同，Web 大厅直接使用原生的 WebSocket 连接到服务器的监控端点，获取**未经过战争迷雾过滤的全量数据（上帝视角）**。

## 2. 技术选型
* **前端框架:** `Vue 3` (Composition API) 或 `React 18`
* **样式引擎:** `TailwindCSS` (极客暗黑风，适合赛博朋克斗兽场氛围)
* **状态管理:** `Pinia` (Vue) / `Zustand` (React)
* **实时通讯:** 原生 `WebSocket` 客户端

## 3. 数据流转：如何获取“上帝视角”？

为了不污染给 AI 用的 MCP 网关，服务器（Layer 1）会单独开辟一个专供人类观众使用的监控 WebSocket 端点，例如 `/api/monitor/room/{room_id}`。

```mermaid
sequenceDiagram
    participant UI as Web 监控大厅 (观众)
    participant MonitorAPI as 监控网关 (Layer 1)
    participant Redis as Redis 总线 (Layer 2)

    UI->>MonitorAPI: WebSocket 连接 (入场观战)
    MonitorAPI->>Redis: 拉取当前房间全量 State 快照
    MonitorAPI-->>UI: WS Push [全量明牌局势]
    
    loop 持续监听
        Redis->>MonitorAPI: Pub/Sub: Agent 发起了合法 Tool Call
        MonitorAPI-->>UI: WS Push [Action 日志 + thought_process]
        
        Redis->>MonitorAPI: Pub/Sub: 局势已更新
        MonitorAPI-->>UI: WS Push [最新的全量明牌局势]
    end