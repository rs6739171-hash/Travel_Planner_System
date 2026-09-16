from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_llm():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required to plan a trip.")
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5.1"),
        api_key=OPENAI_API_KEY,
        timeout=60,
        max_retries=2
    )

