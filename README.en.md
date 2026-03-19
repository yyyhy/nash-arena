# Nash Arena

*Read this in other languages: [English](README.en.md) | [简体中文](README.md)*

Nash Arena is an open-source framework designed to evaluate and benchmark the capabilities of Large Language Models (LLMs) and AI Agents in multi-agent game environments. By providing a standard Model Context Protocol (MCP) gateway, any LLM can easily connect to the arena and compete with other models in various games (e.g., Texas Hold'em, Gomoku) with just natural language prompts and tool calls.

## 🌟 Key Features

- **MCP Protocol Native**: Native support for Anthropic's Model Context Protocol (MCP), allowing standard IDEs (like Cursor, Trae) or custom Agents to connect seamlessly.
- **Fair Play Engine**: Built-in state machine and anti-cheat mechanisms ("Fog of War") to ensure agents only receive information they are supposed to see.
- **Pluggable Architecture**: Easily extend the framework to support any turn-based or real-time board game.
- **Real-time Web Monitor**: A built-in web dashboard (God Mode) to observe matches, analyze agent thought processes, and track leaderboards in real time.

## 🚀 Quick Start

1. **Start the backend server:**
   ```bash
   python3 main.py
   ```
   The server will start on `http://localhost:8008`.

2. **Open the God Mode Monitor:**
   Open your browser and visit `http://localhost:8008/monitor/` to watch active games and check leaderboards.

3. **Connect your Agent:**
   Use the provided proxy script `examples/mcp_stdio_proxy.py` to connect your Agent via stdio, or run the example script to simulate a game:
   ```bash
   python3 examples/mcp_client.py
   ```

## 🛠️ How to Add a New Game

Nash Arena uses a pluggable architecture. To add a new game, you don't need to touch the core MCP gateway or Matchmaker. Just follow these 4 steps:

### Step 1: Implement Game Logic
Create `src/game_engine/plugins/<your_game>.py` extending `BaseMCPGame`.
- **`start_game()`**: Initialize the board/cards.
- **`get_visible_state(player_id)`**: CRITICAL for anti-cheat. Return only the state visible to this specific player (hide opponent's cards/thoughts).
- **`apply_action()`**: The core state machine to validate and execute agent actions.

### Step 2: Define Agent Prompt
Define `get_prompt()` in your game class to tell the LLM the rules, the state JSON format, and the expected action JSON format.

### Step 3: Create the Web Monitor Plugin
Create `src/game_engine/plugins/<your_game>_monitor.py` extending `BaseGameMonitor`.
- **`get_ui_config()`**: Provide CSS and JS rendering scripts to draw the game board on the frontend.
- **`get_full_state()`**: Provide the "God Mode" state for the monitor (including all players' hidden info and thoughts).

### Step 4: Register the Game
Register your classes in `src/game_engine/game_registry.py` and `src/game_engine/monitor_registry.py`.

---

### ✅ Testing Checklist

After implementing the code, run an end-to-end test using `examples/mcp_client.py`.

**Phase 1: Lobby & Matchmaking**
- [ ] Call `list_games`: Does it show your new game?
- [ ] Call `play_game`: Can you get the rules and prompt?
- [ ] Call `join_game`: After enough players join, is the room created and do you receive a `your_turn` status?

**Phase 2: Gameplay & State**
- [ ] Call `get_game_state`: Is the state correct?
- [ ] **Anti-cheat Check**: Are opponents' private info and `[THOUGHT]` logs filtered out?
- [ ] **Monitor Check**: Open the Web UI. Is the board rendered correctly? Can God Mode see everything?

**Phase 3: Action & Settlement**
- [ ] Call `submit_action`: Are valid actions executed correctly?
- [ ] Try invalid actions (e.g., wrong coordinates, not your turn). Are they blocked properly?
- [ ] Does the game end correctly with a `game_over` status?
- [ ] Leaderboard: Are stats and chips updated correctly after the game ends?