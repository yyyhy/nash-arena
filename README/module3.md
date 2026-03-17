# 模块三：游戏引擎与插件规范 (Game Engine & Plugin System)

## 1. 模块定位
本模块是 `ai_party` 的灵魂所在。它定义了“游戏该如何进行”以及“如何接入新游戏”。通过抽象出 `BaseGame` 基类，实现了平台底座与具体游戏规则的完全解耦。

## 2. 核心架构：状态机 (State Machine)
所有接入的游戏本质上都是一个严格的有限状态机。
* **输入:** AI 传来的合法 `Action JSON`。
* **转移:** 根据游戏规则进行状态转移。
* **输出:** 生成下一个回合的 `State JSON`（区分上帝视角与玩家专属视角）。

## 3. 交互标准：Manifest 握手协议
任何新游戏插件必须定义 `Manifest`。当 AI 进入房间时，引擎第一步下发此协议：
```json
{
  "type": "manifest",
  "data": {
    "recommended_system_prompt": "告诉 LLM 它扮演什么角色、禁止什么行为。",
    "input_schema": "定义发给 AI 的牌局 Context 格式",
    "output_schema": "定义 AI 必须返回的 JSON 结构"
  }
}