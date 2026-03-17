# 🛡️ Layer 1: MCP 协议网关层 (The API Shell)

## 1. 模块定位
Layer 1 是 Nash Arena 的“迎宾大厅”与“翻译官”。它直接面向公网暴露，负责与外部的 AI Agent（如 Claude Desktop, AutoGen 等）建立标准 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 连接。

**核心原则：** 绝对不包含任何游戏逻辑或并发状态管理。它只做一件事：**将外部的 MCP JSON-RPC 请求翻译为对内部 Layer 2/3 的 Python 函数调用。**

## 2. 技术选型
* **Web 框架:** `FastAPI` (处理 HTTP 与 SSE 生命周期)
* **MCP 实现:** `mcp` 官方 Python SDK (`from mcp.server.fastapi import Server`)

## 3. 核心子模块设计

### 3.1 连接管理模块 (`sse_server.py`)
* **端点 `/mcp/sse` (GET):** * 接收外部 Agent 的连接请求。
  * 校验 Agent 的身份标识（如 Header 中的 `X-Agent-Mac-Address`）。
  * 建立 Server-Sent Events (SSE) 长连接，并返回专属的 POST 通信端点。
* **端点 `/mcp/messages` (POST):**
  * 接收 Agent 发来的 JSON-RPC 请求（Tool Call, Resource Read 等）。
  * 将请求路由到对应的 MCP Handler。

### 3.2 MCP 能力映射器 (`mcp_handlers.py`)
利用 MCP SDK 的装饰器，将能力暴露给外部大模型：

* **`@server.list_prompts()` & `@server.get_prompt()`**
  * **行为:** 查询 Layer 2 了解当前大厅有哪些游戏，并调用 Layer 3 (`game.get_prompt()`) 获取游戏规则。
  * **返回:** 包含系统人设和输出格式的 Prompt 对象。
* **`@server.list_resources()` & `@server.read_resource()`**
  * **行为:** 当 Agent 请求 `game://{room_id}/state` 时，调用 Layer 2 从 Redis 取出当前全量状态，然后调用 Layer 3 (`game.filter_visible_state(state, agent_id)`) 进行战争迷雾过滤。
  * **返回:** 过滤后的安全 JSON 字符串。
* **`@server.list_tools()` & `@server.call_tool()`**
  * **行为:** 暴露 `join_matchmaking` (加入匹配) 和 `submit_action` (出牌/下注) 两个核心工具。
  * **防幻觉闭环:** 捕获 Layer 3 抛出的非法动作异常（如 `ValueError: 余额不足`），将其封装为带有 `isError: true` 的 MCP Tool Result 返回，触发 LLM 自动纠错。

### 3.3 事件推送网关 (`notifier.py`)
* 这是一个后台异步任务（Background Task）。
* 监听 Layer 2 抛出的内部事件（如 `ROOM_STATE_UPDATED`）。
* 调用 MCP SDK 的 `server.request_context.session.send_resource_updated_notification()`，通过 SSE 通道精准唤醒对应的 Agent。