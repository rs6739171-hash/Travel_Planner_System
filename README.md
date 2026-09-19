# Multi-Agent Travel Planner

[Live app](https://travel-planner-rishabh.onrender.com/) · [Portfolio and demo access](https://my-portfolio-website-topaz-beta.vercel.app/)

A personal Python and GenAI project by Rishabh Shukla. A LangGraph supervisor chooses specialist agents for travel research, then prepares an itinerary for human approval or revision. The Streamlit demo is password protected and may need time to wake up.

## Recruiter quick scan

- **Multi-agent workflow:** a LangGraph supervisor routes relevant work to flight, hotel, weather and budget specialists.
- **Tool integration:** Tavily MCP and OpenWeather enrich research while missing-provider states are surfaced explicitly.
- **Human-in-the-loop & persistence:** itinerary approval/revision uses LangGraph interrupts with PostgreSQL checkpointing when configured.
- **Delivery:** Streamlit, validation, regression tests, GitHub Actions and Render deployment configuration.

## Implemented behavior

- Supervisor routing selects flight, hotel, weather and budget specialists when relevant.
- Tavily MCP supports hotel web research; OpenWeather provides weather data when keys are configured.
- The workflow pauses with a LangGraph interrupt before finalization. Rejected drafts return for revision and require approval again.
- PostgreSQL checkpointing is used when DATABASE_URL is configured; otherwise sessions use in-memory checkpoints.
- Input validation, provider error messages, regression tests and a Render deployment blueprint are included.

## Limits

This is a planning prototype. It does not make bookings or verify live fares. AviationStack is a flight-status integration; route-specific results are currently unavailable until verified IATA filters are implemented. Hotel search does not guarantee availability. Missing provider keys produce explicit unavailable-data messages. PostgreSQL persistence must be configured; the fallback does not survive restarts. No load or independent quality benchmark is claimed.

## Run locally

Use Python 3.12 or 3.13:

```bash
git clone https://github.com/rs6739171-hash/Travel_Planner_System.git
cd Travel_Planner_System
python -m venv .venv
source .venv/bin/activate
pip install -r Travel_Planner_Agent/requirements.txt
cd Travel_Planner_Agent
cp .env.example .env
# Set your own keys in .env.
python serve.py
```

Required: OPENAI_API_KEY. Set APP_PASSWORD for hosted access. Optional integrations: TAVILY_API_KEY, OPENWEATHER_API_KEY, AVIATION_STACK_API_KEY, DATABASE_URL. Never commit credentials. Open the Streamlit URL printed by the launcher.

## Verify and deploy

From the repository root, run `python -m unittest discover -s tests -v`. Tests include denial, routing, explicit approval, revision and reapproval. GitHub Actions installs dependencies, runs tests and checks Python syntax without paid provider calls.

The Render blueprint is [render.yaml](render.yaml). The detailed prior deployment review is [DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md). The presence of deployed UI and passing offline tests does not establish live availability of every external provider.
