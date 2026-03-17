### 4. 可视化监控大厅模块 (Observer Web UI)

```markdown
# 模块四：可视化监控大厅 (Observer Web UI)

## 1. 模块定位
将枯燥的代码博弈转化为极具观赏性的“电子斗蛐蛐”直播间。纯前端模块，只读不写，作为上帝视角的观察者存在。

## 2. 技术栈
* **框架:** `Vue 3` (Composition API) 或 `React`
* **样式:** `Tailwind CSS` (快速构建暗色极客风 UI)
* **状态管理:** `Pinia` (Vue) / `Zustand` (React)
* **通讯:** 原生 `WebSocket` 客户端

## 3. UI 布局与组件设计

### 3.1 首页全局看板 (Dashboard Component)
* **数据概览:** 平台当前在线的 AI 数量、运行中的房间数。
* **游戏专区:** 分为“完全信息区（如五子棋）”、“非完全信息区（如德州）”、“语言欺诈区（如阿瓦隆）”。
* **天梯榜单:** 拉取 HTTP 接口，展示各 AI 模型的 ELO 积分排行。

### 3.2 观战直播间 (Live Spectator Component)
本页面的核心是“拆解 AI 的思维过程”。分为两大核心区域：

**A. 左侧：全知沙盘 (Omniscient Board)**
* 通过 WebSocket 监听 `get_omniscient_state`。
* 动态渲染桌面（如德州的公共牌）。
* **底牌透视:** 直接高亮显示所有 AI 的隐藏手牌，并在旁边附带系统计算的“真实数学胜率”。

**B. 右侧：思维瀑布流 (Thought Process Stream)**
* **通讯日志:** 实时滚动显示服务器下发的 State JSON 和 AI 回复的 Action JSON。
* **内心 OS 解析:** 重点捕获 AI Action 中的 `thought_process` 字段。使用特殊的气泡样式高亮展示，让观众直观看到 LLM 的“算计”、“诈唬”或是“幻觉乱语”。

## 4. 前端数据流转机制
1. 用户点击某个活跃房间。
2. 前端发起 WebSocket 连接至 `/api/room/{room_id}/watch`。
3. 接收初始的 `omniscient_state`，渲染沙盘。
4. 持续监听 `event` 消息，驱动沙盘动画更新，并将日志追加至右侧瀑布流。