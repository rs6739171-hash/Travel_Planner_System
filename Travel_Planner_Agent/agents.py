import sys
import asyncio
import json
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

# pyrefly: ignore [missing-import]
from config import get_llm
# pyrefly: ignore [missing-import]
from mcp_client import (
    tavily_mcp_search,
    search_flights,
    get_airports,
    get_airlines,
    get_weather,
    weather_forecast,
    extract_destination,
)
# pyrefly: ignore [missing-import]
from state import TravelState

llm = get_llm()

def _llm_text(system: str, prompt: str) -> str:
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ])
    return response.content

def _json_from_llm(text: str) -> dict:
    print("\n=======RAW LLM RESPONSE=======")
    print(text)
    print("================================")

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_text = text[start:end]
        parsed = json.loads(json_text)
    except Exception as e:
        print(f"JSON parsing fallback due to: {e}")
        parsed = {
            "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
            "trip_constraints": {
                "destination": "",
                "origin": "",
                "duration": "",
                "budget": "",
                "travel_style": "",
                "special_preferences": []
            },
            "reasoning": "Standard full travel agent pipeline selected."
        }

    print("\n======PARSED JSON======")
    print(json.dumps(parsed, indent=2))
    print("========================\n")

    return parsed

def supervisor_agent(state: TravelState):
    query = state.get("user_query", "")
    guardrail_prompt = f"""
    Determine whether the following request is a valid travel planning request.
    Return pnly JSON in this format:
    {{
        "allowed": true,
        "reason": ""
    }}

    User request:
    {query}
    """

    guardrail_raw = _llm_text(
        "You are an input validation guardrail. Return strict JSON only.",
        guardrail_prompt,
    )

    print("\n========== GUARDRAIL RAW RESPONSE ==========")
    print(guardrail_raw)
    print("============================================\n")

    guardrail_result = _json_from_llm(guardrail_raw)

    print("\n========== GUARDRAIL PARSED RESPONSE ==========")
    print(json.dumps(guardrail_result, indent=2))
    print("================================================\n")

    if not guardrail_result.get("allowed", False):
        reason = guardrail_result.get(
            "reason",
            "Request rejected by input guardrail."
        )

        return {
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [
                AIMessage(content=f"Guardrail blocked request: {reason}")
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
        prompt = f"""
You are the supervisor of a real-world multi-agent travel planning system.

Decide which specialist agents are needed for this user request.

Available agents:
- flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
- hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
- weather_agent: use when weather, climate, season, packing, or forecast is useful
- budget_agent: use when budget, affordability, cost, or price constraints are mentioned
- itinerary_agent: almost always needed to produce the travel plan

Return only JSON with this schema:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "",
    "origin": "",
    "duration": "",
    "budget": "",
    "travel_style": "",
    "special_preferences": []
  }},
  "reasoning": ""
}}

User request:
{query}
"""
    raw = _llm_text(
        "You route work to specialist agents. Return strict JSON only.",
        prompt,
    )
    print("\n======RAW SUPERVISOR RESPONSE=======")
    print(raw)
    print("====================================\n")

    parsed = _json_from_llm(raw)

    return {
        "selected_agents": parsed.get("selected_agents", ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"]),
        "trip_constraints": parsed.get("trip_constraints", {}),
        "supervisor_reasoning": parsed.get("reasoning", ""),
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def flight_agent(state: TravelState):
    query = state.get("user_query", "")
    constraints = state.get("trip_constraints", {})
    destination = constraints.get("destination", "")
    origin = constraints.get("origin", "")

    print(f"\n=====FLIGHT AGENT WORKING ON ORIGIN={origin} DESTINATION={destination}=====\n")

    flight_query = f"{origin} to {destination}".strip() if (origin or destination) else query
    live_flight_data = search_flights(flight_query)
    airports = get_airports(destination)
    airlines = get_airlines()

    prompt = f"""
    Create flight Guidance for this trip.
    User Request:
    {query}

    Trip Constraints:
    {json.dumps(constraints, indent=2)}

    Live Flight Records:
    {live_flight_data}

    Airport & Carrier Context:
    {json.dumps(airports, indent=2)}
    {json.dumps(airlines, indent=2)}

    Provide recommended flight routes, estimated duration, fare estimates,
    departure/arrival airport suggestions, and booking tips.
    """

    result = _llm_text(
        "You are an expert flight planning specialist.",
        prompt,
    )

    print("\n======Flight Agent Output======")
    print(result)
    print("\n==============================\n")

    return {
        "flight_results": result,
        "messages": state.get("messages", []) + [AIMessage(content="Flight Agent completed flight guidance.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def hotel_agent(state: TravelState):
    constraints = state.get("trip_constraints", {})
    dest = constraints.get("destination", "")
    query = f"Best hotels and stays in {dest} {state.get('user_query', '')}".strip()

    print("\n========== HOTEL AGENT INPUT ==========")
    print(query)
    print("=======================================\n")

    result = asyncio.run(tavily_mcp_search(query))

    print("\n========== HOTEL SEARCH RESULT ==========")
    print(result)
    print("=========================================\n")

    return {
        "hotel_results": str(result),
        "messages": [AIMessage(content="Hotel agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def weather_agent(state: TravelState):
    constraints = state.get("trip_constraints", {})
    city = constraints.get("destination") or extract_destination(state.get("user_query", ""))

    print("\n========== WEATHER AGENT INPUT ==========")
    print("City:", city)
    print("=========================================\n")

    weather_data = get_weather(city)
    forecast_data = weather_forecast(city)

    print("\n========== CURRENT WEATHER ==========")
    print(weather_data)
    print("=====================================\n")

    print("\n========== WEATHER FORECAST ==========")
    print(forecast_data)
    print("======================================\n")

    result = f"""
Current weather:
{weather_data}

Forecast:
{forecast_data}
"""

    print("\n========== WEATHER AGENT OUTPUT ==========")
    print(result)
    print("==========================================\n")

    return {
        "weather_results": result,
        "messages": [AIMessage(content="Weather agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def budget_agent(state: TravelState):
    print("\n========== BUDGET AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))
    print("\nFlight Results:")
    print(state.get("flight_results"))
    print("\nHotel Results:")
    print(state.get("hotel_results"))
    print("\nWeather Results:")
    print(state.get("weather_results"))
    print("=========================================\n")

    prompt = f"""
Analyze whether this trip plan is realistic for the user's budget.

User request:
{state.get('user_query', '')}

Constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Return a concise budget assessment with:
1. estimated cost categories
2. risk areas
3. money-saving suggestions
4. whether the plan seems feasible
"""

    result = _llm_text(
        "You are a practical travel budget analyst.",
        prompt,
    )

    print("\n========== BUDGET AGENT OUTPUT ==========")
    print(result)
    print("=========================================\n")

    return {
        "budget_results": result,
        "messages": [AIMessage(content="Budget agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def itinerary_agent(state: TravelState):
    print("\n========== ITINERARY AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))
    print("\nFlight Results:")
    print(state.get("flight_results"))
    print("\nHotel Results:")
    print(state.get("hotel_results"))
    print("\nWeather Results:")
    print(state.get("weather_results"))
    print("\nBudget Results:")
    print(state.get("budget_results"))
    print("===========================================\n")

    prompt = f"""
Create a clear, structured draft travel itinerary.

User request:
{state.get('user_query', '')}

Trip constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Budget results:
{state.get('budget_results', '')}

Make the output structured by days, practical, engaging, and ready for human review.
"""

    result = _llm_text(
        "You are an expert itinerary planner.",
        prompt,
    )

    print("\n========== ITINERARY OUTPUT ==========")
    print(result)
    print("======================================\n")

    approval_request = f"""
Please review this draft travel plan.

{result}

Reply with approval or feedback.
"""

    return {
        "itinerary": result,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def human_approval_agent(state: TravelState):
    feedback = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional feedback for revision",
            },
        }
    )

    approved = feedback.get("approved", True) if isinstance(feedback, dict) else True
    human_feedback = feedback.get("feedback", "") if isinstance(feedback, dict) else str(feedback)

    return {
        "approved": approved,
        "human_feedback": human_feedback,
        "messages": [AIMessage(content="Human approval step completed.")],
    }

def final_response_agent(state: TravelState):
    print("\n========== FINAL AGENT INPUT ==========")
    print("Approved:", state.get("approved"))
    print("Feedback:", state.get("human_feedback"))
    print("=======================================\n")

    if state.get("approved", True):
        prompt = f"""
The human approved this draft itinerary.

Produce the final polished, user-ready travel plan with all flight, hotel, weather, and itinerary details.

Draft itinerary:
{state.get('itinerary', '')}

Budget notes:
{state.get('budget_results', '')}
"""
    else:
        prompt = f"""
The human requested adjustments to the draft.

Original user request:
{state.get('user_query', '')}

Draft itinerary:
{state.get('itinerary', '')}

Human feedback:
{state.get('human_feedback', '')}

Budget notes:
{state.get('budget_results', '')}

Revise and produce the final polished travel plan addressing the human feedback.
"""

    result = _llm_text(
        "You produce final user-ready travel plans.",
        prompt,
    )

    print("\n========== FINAL RESPONSE ==========")
    print(result)
    print("====================================\n")

    return {
        "final_response": result,
        "messages": [AIMessage(content=result)],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }