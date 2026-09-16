import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import atexit
import psycopg
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph


# pyrefly: ignore [missing-import]
from agents import (
    budget_agent,
    final_response_agent,
    flight_agent,
    hotel_agent,
    human_approval_agent,
    itinerary_agent,
    supervisor_agent,
    weather_agent,
)
# pyrefly: ignore [missing-import]
from config import DATABASE_URL
# pyrefly: ignore [missing-import]
from state import TravelState

AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]

ROUTE_MAP = {
    "__end__": END,
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
}


def _selected_agents(state: TravelState) -> list[str]:
    selected = state.get("selected_agents") or []
    return [agent for agent in AGENT_ORDER if agent in selected]  


def route_from_supervisor(state: TravelState) -> str:
    if state.get("blocked"):
        return "__end__"
    selected = _selected_agents(state)
    return selected[0] if selected else "itinerary_agent"



def route_after_agent(current_agent: str):
    def route(state: TravelState) -> str:
        selected = _selected_agents(state)
        current_index = AGENT_ORDER.index(current_agent)

        for next_agent in AGENT_ORDER[current_index + 1:]:
            if next_agent in selected:
                return next_agent

        return "itinerary_agent"

    return route




def build_graph():
    graph = StateGraph(TravelState)

    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("budget_agent", budget_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    graph.add_node("human_approval", human_approval_agent)
    graph.add_node("final_response", final_response_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, ROUTE_MAP)
    graph.add_conditional_edges("flight_agent", route_after_agent("flight_agent"), ROUTE_MAP)
    graph.add_conditional_edges("hotel_agent", route_after_agent("hotel_agent"), ROUTE_MAP)
    graph.add_conditional_edges("weather_agent", route_after_agent("weather_agent"), ROUTE_MAP)
    graph.add_conditional_edges("budget_agent", route_after_agent("budget_agent"), ROUTE_MAP)
    graph.add_edge("itinerary_agent", "human_approval")
    graph.add_conditional_edges(
        "human_approval",
        lambda state: "final_response" if state.get("approved") is True else "itinerary_agent",
        {"final_response": "final_response", "itinerary_agent": "itinerary_agent"},
    )
    graph.add_edge("final_response", END)

    if DATABASE_URL:
        pool = ConnectionPool(
            conninfo=DATABASE_URL, min_size=1, max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        atexit.register(pool.close)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        return graph.compile(checkpointer=checkpointer)

    return graph.compile(checkpointer=MemorySaver())


app = build_graph()
