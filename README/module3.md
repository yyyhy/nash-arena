# 模块三：基于 MCP 的游戏引擎插件规范 (Game Engine Plugins)

## 1. 模块定位
将具体的桌游逻辑映射为 MCP 的核心能力。任何新游戏只需继承 `BaseMCPGame`，实现对应的基元方法即可。

## 2. 核心基类 `BaseMCPGame` 设计

开发者编写新游戏（如《德州扑克》）需要实现以下方法：

### 2.1 规则注册 (Prompt Generation)
```python
def get_mcp_prompt(self) -> dict:
    """定义游戏的 System Prompt，约束 LLM 的人设"""
    return {
        "name": "play_texas_holdem",
        "description": "开始一局德州扑克游戏",
        "messages": [
            {"role": "user", "content": "你是一个只懂概率的扑克机器。你的目标是赢筹码。"}
        ]
    }