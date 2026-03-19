# Nash Arena

*Read this in other languages: [English](README.en.md) | [简体中文](README.md)*

Nash Arena 是一个开源框架，旨在通过多智能体博弈环境评估和基准测试大型语言模型（LLM）及 AI Agent 的能力。它提供了一个标准的 Model Context Protocol (MCP) 网关，任何 LLM 只需通过自然语言提示和工具调用，即可轻松接入竞技场并在各种游戏（如德州扑克、五子棋）中与其他模型同台竞技。

## 🌟 核心特性

- **原生支持 MCP 协议**：基于 Anthropic 的 Model Context Protocol (MCP) 标准，标准 IDE（如 Cursor、Trae）或自定义 Agent 均可无缝接入。
- **公平博弈引擎**：内置严格的状态机与防作弊机制（战争迷雾），确保大模型只能获取其视角的合法信息。
- **插件化架构**：极简的扩展设计，轻松支持德州扑克、五子棋、斗地主等任意回合制或实时博弈游戏。
- **实时可视化监控**：自带 Web 前端面板（上帝视角），可实时观战、洞察 Agent 心理（思考过程），并提供战绩排行榜。

## 🚀 快速开始

1. **启动后端服务：**
   ```bash
   python3 main.py
   ```
   服务将运行在 `http://localhost:8008`。

2. **打开上帝视角监控：**
   在浏览器中访问 `http://localhost:8008/monitor/`，即可实时观战或查看排行榜。

3. **连接你的 Agent：**
   将 `examples/mcp_stdio_proxy.py` 配置为标准 MCP 客户端的 command，或直接运行测试脚本模拟对局：
   ```bash
   python3 examples/mcp_client.py
   ```

## 🛠️ 如何开发一个新的棋牌玩法？

Nash Arena 采用了**插件化架构**。要增加一个新的游戏，你不需要修改核心网络通信（MCP Gateway）或匹配系统（Lobby Manager），只需完成以下四个步骤。

### 步骤一：实现游戏逻辑 (Game Plugin)
在 `src/game_engine/plugins/<your_game>.py` 下创建一个继承自 `BaseMCPGame` 的类。
- **`start_game(self)`**: 初始化游戏（如洗牌、分配颜色）。
- **`get_visible_state(self, player_id)`**: **防作弊核心**。严格过滤并返回该玩家有权看到的信息，隐藏对手的私密信息和思考过程（`[THOUGHT]`）。
- **`apply_action(self, player_id, action)`**: 核心状态机。校验并执行动作，推进回合。
- **`get_results(self)`**: 游戏结束时返回对局结算信息，用于更新战绩。

### 步骤二：定义 Agent Prompt (大模型提示词)
在你的游戏类中定义静态方法 `get_prompt()`。
通过该方法告诉 LLM：游戏规则是什么、当前局势的 JSON 格式代表什么、它需要输出怎样的 JSON 动作格式（如 `{'action': 'place', 'amount': 112, 'thought_process': '...'}`）。

### 步骤三：开发前端监控视图 (Monitor Plugin)
在 `src/game_engine/plugins/<your_game>_monitor.py` 下创建一个继承自 `BaseGameMonitor` 的监控类。
- **`get_ui_config(self)`**: 返回包含自定义 CSS (`custom_css`) 和 JS 渲染函数 (`render_script`) 的配置对象，告诉前端如何画出棋盘或牌桌。
- **`get_full_state(self, game_state)`**: 返回给监控面板看的“上帝视角”状态（所有信息全开）。

### 步骤四：注册你的游戏
在 `src/game_engine/game_registry.py` 和 `src/game_engine/monitor_registry.py` 中注册你编写的游戏逻辑类和监控视图类。

---

### ✅ 开发自测清单 (Checklist)

在完成代码开发后，请使用 `examples/mcp_client.py` 脚本进行一次端到端（E2E）模拟测试。

**阶段一：大厅与匹配**
- [ ] 调用 `list_games` 工具，列表中是否正确包含了你的新游戏？
- [ ] 调用 `play_game` 工具，是否能成功获取到你编写的规则和动作格式？
- [ ] 调用 `join_game` 工具加入队列，满员后是否能成功创建房间并收到 `your_turn` 状态？

**阶段二：对局与状态**
- [ ] 在游戏进行中调用 `get_game_state`，是否能正确返回当前局势？
- [ ] **防作弊验证**：仔细检查 JSON，是否严格过滤了对手的私密信息和 `[THOUGHT]` 思考过程？
- [ ] **前端验证**：打开 Web 监控页，UI 布局是否正常？上帝视角下是否能看到所有玩家的信息和思考过程？

**阶段三：动作执行与结算**
- [ ] 调用 `submit_action` 提交合法动作，游戏引擎是否正常处理并流转回合？
- [ ] 尝试提交非法动作（如违规坐标、未到回合），引擎是否能正确拦截并返回 `is_error: True`？
- [ ] 游戏结束时是否正确返回了 `game_over` 状态及胜负结果？
- [ ] 战绩验证：游戏结束后，排行榜能否正确记录玩家的胜负和筹码变化？
