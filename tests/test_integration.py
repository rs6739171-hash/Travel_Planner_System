import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

@unittest.skipUnless(importlib.util.find_spec("langgraph"), "Runtime dependencies are not installed")
class GraphIntegration(unittest.TestCase):
    def test_rejected_draft_is_revised_and_requires_approval_again(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Travel_Planner_Agent"))
        os.environ.pop("DATABASE_URL", None)
        import agents
        from graph import build_graph
        from langgraph.types import Command
        graph = build_graph()
        config = {"configurable": {"thread_id": "regression"}}
        answers = ['{"allowed": true}', '{"selected_agents":["itinerary_agent"],"trip_constraints":{}}', "Draft one", "Draft two", "Final plan"]
        with patch.object(agents, "_llm_text", side_effect=answers) as llm:
            first = graph.invoke({"user_query": "Plan a trip", "messages": []}, config)
            self.assertIn("__interrupt__", first)
            revised = graph.invoke(Command(resume={"approved": False, "feedback": "Revise it"}), config)
            self.assertIn("__interrupt__", revised)
            self.assertEqual(revised["itinerary"], "Draft two")
            self.assertFalse(revised.get("final_response"))
            final = graph.invoke(Command(resume={"approved": True}), config)
            self.assertEqual(final["final_response"], "Final plan")
            self.assertEqual(llm.call_count, 5)

    def test_denied_input_never_reaches_itinerary(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Travel_Planner_Agent"))
        import agents
        from graph import build_graph
        with patch.object(agents, "_llm_text", return_value='{"allowed":false,"reason":"Not travel"}') as llm:
            result = build_graph().invoke({"user_query":"Not travel", "messages": []}, {"configurable":{"thread_id":"denied"}})
            self.assertNotIn("__interrupt__", result)
            self.assertTrue(result["blocked"])
            self.assertEqual(llm.call_count, 1)
