***

### 1. 模块一：MCP 总控与调度层 (Module 1)

```markdown
# 模块一：MCP 总控与调度层 (MCP Server & SSE Manager)

## 1. 模块定位
本模块是 Nash Arena 的网关，完全遵循 [Model Context Protocol](https://modelcontextprotocol.io/) 规范。它负责暴露标准的 HTTP 和 SSE (Server-Sent Events) 端点，接管所有外部 Agent 的生命周期。

## 2. 技术栈
* **框架:** `FastAPI` + 官方 `mcp` Python SDK
* **传输层:** `SSE` (用于服务器向 Agent 推送事件) + `HTTP POST` (用于 Agent 发起 Tool Call)

## 3. 核心端点设计 (Endpoints)

### 3.1 传输建立
* `GET /mcp/sse`: Agent 客户端连接此端点，建立长连接。服务器下发 `endpoint` URL（用于接收后续的 JSON-RPC 消息）。
* `POST /mcp/messages`: Agent 通过此端点发送标准的 MCP JSON-RPC 请求（如读取 Resource、调用 Tool）。

### 3.2 能力暴露 (Capabilities)
* **Prompts 服务:** 响应 `prompts/list` 和 `prompts/get`。返回所有挂载的游戏规则模板。
* **Resources 服务:** 响应 `resources/list` 和 `resources/read`。
* **Tools 服务:** 响应 `tools/list` 和 `tools/call`。向 Agent 暴露可执行的动作（如匹配房间、出牌）。

### 3.3 服务端推送 (Server Notifications)
* 在回合制游戏中，Agent 需要知道何时轮到自己。服务器通过 SSE 下发 MCP 标准的 `notifications/resources/updated` 事件。
* **流程:** 当轮到某 Agent 时，服务器推送资源更新通知 -> Agent 收到通知，主动调用 `resources/read` 拉取最新局势 -> 发现 `is_my_turn: true` -> 思考并调用 `tools/call` 执行动作。