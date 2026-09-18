import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from helpers import functions_from

APP = Path(__file__).resolve().parents[1] / "Travel_Planner_Agent"
MESSAGE = lambda **kwargs: SimpleNamespace(**kwargs)
ORDER = ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"]


class TravelRegressions(unittest.TestCase):
    def agents(self, replies):
        ns = functions_from(APP / "agents.py", json=json, AIMessage=MESSAGE)
        sequence = iter(replies)
        ns["_llm_text"] = lambda *args: next(sequence)
        return ns

    def test_valid_request_reaches_supervisor_prompt(self):
        ns = self.agents(['{"allowed": true}', '{"selected_agents": ["itinerary_agent"], "trip_constraints": {}, "reasoning": "Plan"}'])
        with contextlib.redirect_stdout(io.StringIO()):
            result = ns["supervisor_agent"]({"user_query": "Plan a trip to Tokyo"})
        self.assertFalse(result["blocked"])
        self.assertEqual(result["selected_agents"], ["itinerary_agent"])

    def test_denied_or_malformed_guardrail_ends_workflow(self):
        routes = functions_from(APP / "graph.py", AGENT_ORDER=ORDER)
        for reply in ['{"allowed": false}', 'not JSON', '{"allowed": "false"}']:
            with self.subTest(reply=reply):
                ns = self.agents([reply])
                with contextlib.redirect_stdout(io.StringIO()):
                    result = ns["supervisor_agent"]({"user_query": "not a trip"})
                self.assertEqual(routes["route_from_supervisor"](result), "__end__")

    def test_approval_requires_explicit_true(self):
        for response in [{"approved": False}, {}, "approve", {"approved": "true"}]:
            ns = self.agents([])
            ns["interrupt"] = lambda *args: response
            self.assertFalse(ns["human_approval_agent"]({})["approved"])

    def test_flight_message_is_appended_once(self):
        ns = self.agents(["flight guidance"])
        ns.update(search_flights=lambda q: "no live data", get_airports=lambda d: {}, get_airlines=lambda: {})
        with contextlib.redirect_stdout(io.StringIO()):
            result = ns["flight_agent"]({"messages": [MESSAGE(content="old")]})
        self.assertEqual(len(result["messages"]), 1)

    def test_graph_has_memory_and_reapproval_route(self):
        class Graph:
            def __init__(self, state): self.routes = {}
            def add_node(self, *args): pass
            def add_edge(self, *args): pass
            def add_conditional_edges(self, node, fn, mapping): self.routes[node] = fn
            def compile(self, **kwargs): self.checkpointer = kwargs.get("checkpointer"); return self
        ns = functions_from(APP / "graph.py", StateGraph=Graph, TravelState=dict,
            MemorySaver=lambda: "memory", DATABASE_URL=None, START="start", END="end",
            AGENT_ORDER=ORDER, ROUTE_MAP={})
        for name in ORDER + ["supervisor_agent", "human_approval_agent", "final_response_agent"]:
            ns[name] = lambda state: state
        graph = ns["build_graph"]()
        self.assertEqual(graph.checkpointer, "memory")
        self.assertEqual(graph.routes["human_approval"]({"approved": False}), "itinerary_agent")
        self.assertEqual(graph.routes["human_approval"]({"approved": True}), "final_response")


if __name__ == "__main__": unittest.main()
