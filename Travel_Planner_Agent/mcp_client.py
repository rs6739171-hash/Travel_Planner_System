import os
import asyncio
import requests
from langchain_mcp_adapters.client import MultiServerMCPClient
# pyrefly: ignore [missing-import]
from config import (
    AVIATION_STACK_API_KEY,
    OPENWEATHER_API_KEY,
    TAVILY_API_KEY,
    get_llm
)
from mcp.server.fastmcp import FastMCP

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY or os.getenv('TAVILY_API_KEY')}",
        }
    }
)

def search_flights(query: str = "") -> str:
    if not AVIATION_STACK_API_KEY:
        return "Flight search API key not configured."

    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": AVIATION_STACK_API_KEY,
        "limit": 5
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except Exception as e:
        return f"Flight lookup error: {e}"

    flights = []
    if "data" in data and isinstance(data["data"], list):
        for flight in data["data"][:5]:
            airline = flight.get("airline", {}).get("name", "Unknown")
            departure = flight.get("departure", {}).get("airport", "Unknown")
            arrival = flight.get("arrival", {}).get("airport", "Unknown")
            status = flight.get("flight_status", "Unknown")
            flights.append(
                f"Airline: {airline}\nDeparture: {departure}\nArrival: {arrival}\nStatus: {status}"
            )

    return "\n\n".join(flights) if flights else "No direct flight status records returned."

async def tavily_mcp_search(query: str = "Top hotels in Tokyo") -> str:
    try:
        tools = await client.get_tools()
        search_tool = next(
            tool
            for tool in tools
            if tool.name == "tavily_search"
        )
        result = await search_tool.ainvoke({"query": query})
        if isinstance(result, list):
            texts = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                else:
                    texts.append(str(item))
            return "\n".join(texts)
        return str(result)
    except Exception as e:
        return f"Hotel search error: {e}"

def get_airports(destination: str = ""):
    return {
        "destination": destination,
        "primary_airports": f"Major international & domestic airports serving {destination or 'the region'}"
    }

def get_airlines():
    return {
        "airlines": "Major domestic and international carriers"
    }

mcp = FastMCP("Weather Server")

@mcp.tool()
def get_weather(city: str):
    if not OPENWEATHER_API_KEY:
        return f"Weather data unavailable (API key missing) for {city}"

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        return {"error": str(e)}

    if response.status_code == 200:
        return {
            "city": data.get("name", city),
            "temperature": f"{data.get('main', {}).get('temp')} °C",
            "humidity": f"{data.get('main', {}).get('humidity')}%",
            "description": data.get("weather", [{}])[0].get("description", ""),
            "feels_like": f"{data.get('main', {}).get('feels_like')} °C",
            "wind_speed": f"{data.get('wind', {}).get('speed')} m/s"
        }
    return {"error": data.get("message", f"Failed to get weather for {city}")}

@mcp.tool()
def weather_forecast(city: str):
    if not OPENWEATHER_API_KEY:
        return f"Forecast data unavailable (API key missing) for {city}"

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        return {"error": str(e)}

    if response.status_code != 200:
        return {"error": data.get("message", f"Failed to get forecast for {city}")}

    forecasts = []
    for f in data.get("list", [])[:5]:
        forecasts.append({
            "dt_txt": f.get("dt_txt"),
            "temp": f"{f.get('main', {}).get('temp')} °C",
            "weather": f.get("weather", [{}])[0].get("description", "")
        })

    return {
        "city": city,
        "forecast": forecasts
    }

def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country from this query.

    Query:
    {query}

    Return only the destination name (e.g. Tokyo, Paris, Bali).
    """
    response = get_llm().invoke(prompt)
    return response.content.strip()

if __name__ == "__main__":
    print(weather_forecast("Delhi"))