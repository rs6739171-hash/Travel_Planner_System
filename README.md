# 🧳 Real-World Multi-Agent Travel Planner

A production-style multi-agent travel planning system built with **LangGraph**, orchestrating specialist AI agents to research flights, hotels, weather, and budget constraints, then produce a human-reviewed, ready-to-book itinerary.

Unlike a single-prompt "AI trip planner," this system routes each request through 
a **supervisor agent** that dynamically decides which specialists are actually needed, calls live external APIs for real data, and includes a **human-in-the-loop approval step** before finalizing the plan — mirroring how a real agentic production system is designed.

---

## ✨ Key Features

- **Dynamic Supervisor Routing** – An LLM-based supervisor agent parses the user's request, extracts trip constraints (destination, origin, budget, duration, travel style), and decides *which* specialist agents are actually needed instead of always running the full pipeline.
- **Input Guardrails** – Every request first passes through a validation guardrail that rejects non-travel-related or malicious inputs before any agent work begins.
- **Multi-Agent Specialist Pipeline** – Independent agents for:
  - ✈️ **Flight Agent** – live flight data via AviationStack API
  - 🏨 **Hotel Agent** – real-time hotel/stay search via Tavily MCP server
  - 🌦️ **Weather Agent** – current conditions + forecast via OpenWeather API
  - 💰 **Budget Agent** – feasibility and cost-risk analysis across the whole plan
  - 🗓️ **Itinerary Agent** – synthesizes all specialist outputs into a structured day-by-day draft
- **Human-in-the-Loop Approval** – The graph pauses via LangGraph's `interrupt()` after the draft itinerary is generated, letting the user approve or send feedback for revision before a final plan is produced.
- **MCP (Model Context Protocol) Integration** – Uses `langchain-mcp-adapters` to connect to the Tavily MCP server for live web search, and exposes a custom FastMCP weather tool server.
- **Stateful, Resumable Conversations** – Built on LangGraph's `StateGraph` with **PostgreSQL checkpointing**, so sessions persist and can resume mid-approval across restarts.
- **Streamlit UI** – Interactive frontend to submit a travel request, watch each agent's output stream in, and approve/revise the itinerary in real time.

---

## 🏗️ Architecture


The graph is built with `langgraph.graph.StateGraph`, using **conditional edges** so the supervisor's agent selection actually changes the execution path at runtime — agents that aren't needed for a given query are skipped entirely.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (`StateGraph`, conditional routing, `interrupt()`) |
| LLM | OpenAI (via `langchain-openai`) |
| Agent Framework | LangChain Core |
| Live Data / Search | Tavily MCP Server, AviationStack API, OpenWeather API |
| Protocol | Model Context Protocol (MCP) — `langchain-mcp-adapters`, `FastMCP` |
| Persistence | PostgreSQL (`langgraph-checkpoint-postgres`) for session/thread checkpointing |
| Frontend | Streamlit |
| Package Management | `uv` |

---

## 📂 Project Structure
Travel_Planner_Agent/
  agents.py          - Supervisor + specialist agent definitions
  graph.py            - LangGraph StateGraph wiring & conditional routing
  mcp_client.py    - MCP client (Tavily) + external API integrations (flights, weather)
  config.py           - Environment config & LLM initialization
  state.py             - Shared TravelState schema
  frontend.py       - Streamlit UI
  requirements.txt
