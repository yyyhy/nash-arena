# 🧠 Layer 3: 游戏引擎内核 (The Pure Core)

## 1. 模块定位
Layer 3 是万物皆可斗的“插件区”。它由一个极其轻量的基础接口类和无数个具体的游戏插件组成。

**核心原则：** 绝对纯粹的 Python 状态机。**不允许**导入任何网络库（如 `httpx`, `websockets`）或数据库连接库（如 `redis`）。它的所有方法都是纯函数或同步方法：输入旧状态和动作，输出新状态。这种设计让单元测试变得极其容易。

## 2. 核心架构：`BaseMCPGame` 基类

所有游戏插件（如 `TexasHoldemPlugin`, `AvalonPlugin`）必须继承此抽象基类，并实现以下 5 个核心方法：

### 2.1 元数据与协议定义
* `get_meta() -> dict`:
  * 返回游戏的基本信息（名称、最小/最大人数、介绍）。供 Layer 1 的 `prompts/list` 使用。
* `get_mcp_prompt() -> dict`:
  * 返回该游戏的系统人设（System Prompt）和动作要求。

### 2.2 状态机流转
* `get_initial_state(players: list[str]) -> dict`:
  * 游戏开始时的初始化操作（例如生成一副牌、洗牌、发底牌）。返回全知视角的初始状态字典。
* `apply_action(state: dict, player_id: str, action: dict) -> dict`:
  * **核心推演逻辑。**
  * 校验 `player_id` 此时是否有权行动，以及 `action` 携带的参数是否合法（防幻觉沙盒）。
  * 如果非法，主动 `raise ValueError("非法原因")`，Layer 1 会捕获并返回给 Agent 纠错。
  * 如果合法，修改 `state` 字典（如扣减筹码、发公共牌、转移行动权给下一个人），并返回更新后的 `state`。
* `is_game_over(state: dict) -> bool | dict`:
  * 检查当前状态是否达到胜利条件。如果结束，返回结算明细（赢家是谁、积分变动）。

### 2.3 上下文隔离 (战争迷雾)
* `filter_visible_state(state: dict, player_id: str) -> dict`:
  * 安全防线。接收全局大状态，深拷贝后，**强行剔除或掩码**对手的底牌和私有资源。
  * 确保 Layer 1 吐给 Agent 的 Resource JSON 中绝对没有作弊的可能。

## 3. 插件开发示例 (Developer Experience)
得益于这种极简设计，社区贡献一个新桌游（如井字棋 Tic-Tac-Toe）只需要不到 100 行代码，无需关心服务器是怎么运作的，只需关注九宫格的数组校验逻辑即可。