# Travel Planner — review and deployment preparation

Reviewed baseline: `2ac92accaebfa80b39329f3e2294b6c2eb527725`.

## Findings addressed

| Severity | Original location | Finding and correction |
|---|---|---|
| P1 | `agents.py:supervisor_agent` | Valid input reached an undefined `prompt` because its assignment was inside an unreachable rejected-input branch. Moved the prompt to the valid path and validate structured output. |
| P1 | `graph.py:route_from_supervisor` | Rejected requests still routed to itinerary generation. Added explicit blocked state and an END route. |
| P1 | `graph.py:build_graph` | Without DATABASE_URL the graph had no checkpointer, breaking interruption/resume. Added in-memory checkpointing; Postgres uses a connection pool when configured. |
| P1 | `requirements.txt` | Conflicting psycopg versions and Windows-only pywin32 prevented a Linux install. Replaced the environment dump with direct runtime requirements. |
| P2 | `graph.py` and `frontend.py` | Rejected drafts were immediately finalized. Revisions now return to itinerary generation and require approval again. Fresh drafts start fresh sessions. |
| P2 | `agents.py:flight_agent` | The additive message reducer received old messages again. Nodes now return only new messages. |
| P2 | `mcp_client.py:search_flights` | Natural-language origin/destination were ignored by an unrelated flight-status feed. Such input now reports route data unavailable instead of presenting unrelated flights. HTTPS replaces HTTP. |

## Required configuration

`OPENAI_API_KEY` is required. Configure `OPENAI_MODEL` to a model available in your account. Optional `TAVILY_API_KEY` enables hotel web search; `OPENWEATHER_API_KEY` enables current weather/forecast; `AVIATION_STACK_API_KEY` supports operational flight-status lookup only. This app does not verify fares, seat availability, or make bookings. A proper route/fare API integration remains future work.

`DATABASE_URL` enables PostgreSQL checkpoints. Without it, sessions survive Streamlit reruns but are lost on service restart, suspension, or deployment. This blueprint does not create a database. The supervisor and LLM guardrail are heuristic; they do not guarantee prompt-injection prevention.

Render uses root directory `Travel_Planner_Agent`, `pip install -r requirements.txt`, and `python serve.py`.

## Deployment configuration

`render.yaml` defines one Python web service. `serve.py` runs Streamlit on Render's `PORT`; where applicable, FastAPI runs only on `127.0.0.1:8000`. The launcher stops both processes if either exits. The Streamlit UI requires `APP_PASSWORD` on Render; the blueprint generates it. Retrieve that password from the service's Environment page. This is an owner/demo password gate, not enterprise identity or tenant isolation.

Secrets are declared with `sync: false`; enter real values in Render's Environment settings, never in Git or chat. The blueprint explicitly selects the free compute plan and disables automatic deployment. No paid service or database was provisioned by this change. Free instances have limited memory and can suspend; if a real build or runtime exceeds these limits, choose a suitable plan before deployment. See [Render blueprint fields](https://render.com/docs/blueprint-spec).

## Validation and limitations

The local review ran Python syntax checks, parsed the YAML, and ran focused regression tests against actual source functions with external dependencies controlled. Runtime integration tests are also included and run in GitHub Actions after installing the serving dependencies. Local dependency installation was blocked by a timeout downloading packages from files.pythonhosted.org. Therefore, a passing local isolated test does not establish that the complete deployed application starts.

No real provider requests or production data tests were performed: API credentials were not available. Model names remain configurable and preserve the existing defaults; verify access to those models in your provider account. Requirements constrain compatible major versions but are not a fully resolved lockfile. `uv.lock` and `pyproject.toml` are legacy development manifests; Render installs the explicitly named requirements file instead.

The review covered the main application, configuration, dependency, UI, and deployment paths. It is not a penetration test or proof of enterprise readiness. No obvious API-key patterns were found in the downloaded text source; Git history and binary data were not scanned.
