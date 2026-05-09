# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Run
python3 main.py                     # interactive mode
python3 main.py -p "帮我建一个PMSM"  # single-shot

# Tests (must run from repo root with venv active)
python3 -m pytest tests/                          # all tests
python3 -m pytest tests/test_regressions.py -k "test_foo"  # single test

# Windows packaging
build.bat   # outputs dist/ansys-agent.exe
```

> **Note:** Tests stub out all heavy dependencies (rich, openai, ansys libs) in `test_regressions.py` top-level setup — no Ansys installation required to run tests.

## Architecture

### Request Flow

```
main.py (CLI + /commands)
  └─ ChatAgent.chat()
       ├─ RAG inject (keyword trigger → search_index → prepend system msg)
       ├─ history compression (token threshold → LLM summarize)
       └─ OmAgentWorkflow
            ├─ FunctionNode   (prepare context, inject roles/knowledge)
            └─ StreamingToolLoopNode  (LLM ↔ tool calls, up to 30 rounds)
                 └─ delegate_to_agent(agent_name, task, context)
                       └─ Dispatcher → SubAgent.execute()
                            └─ OmAgentWorkflow [PlanningNode → ToolLoopNode → SummaryNode]
                                 └─ tools/*.py
```

### The Three-Layer Pattern

Every domain follows the same pattern:

1. **`tools/xxx_tools.py`** — stateless functions wrapping Ansys Python APIs. Global `_app` / `_model` etc. are lazy-init singletons. Every function returns `{"success": bool, "result": ...}` via `_ok()` / `_err()` from `tools/utils.py`.

2. **`agent/tool_definitions.py`** — single source of truth for all tool metadata. **When adding a tool, three things must be updated in sync:**
   - `TOOL_REGISTRY` dict (name → callable)
   - `TOOL_DEFINITIONS` list (OpenAI function calling JSON schema)
   - The relevant `_XXX_TOOL_NAMES` frozenset (controls which tools each Sub-Agent sees)

3. **`agent/sub_agents/xxx_agent.py`** — inherits `SubAgentBase`, passes the filtered `XXX_TOOL_DEFINITIONS` / `XXX_TOOL_REGISTRY` slices.

### Sub-Agent Roster

| agent_name | file | domains |
|---|---|---|
| `maxwell` | `maxwell_agent.py` | EM modeling, results, RMXprt, Circuit |
| `icepak` | `icepak_agent.py` | thermal |
| `fluent` | `fluent_agent.py` | CFD, Meshing, CHT multi-condition |
| `mapdl` | `mapdl_agent.py` | structural, NVH, MapdlPool submodel, Mechanical standalone, DPF-Core |
| `motorcad` | `motorcad_agent.py` | analytical initial design |
| `optimization` | `optimization_agent.py` | optiSLang, parametric sweep, DOE |
| `reporting` | `reporting_agent.py` | HTML/PDF reports |
| `ev_powertrain` | `ev_powertrain_agent.py` | battery + controller + motor cosim |
| `nvh` | `nvh_agent.py` | EM force → structural → acoustic chain |
| `cost` | `cost_agent.py` | manufacturing cost estimation |

### Runtime Data Directory

All writable state goes to `ANSYS_DATA_DIR` (= `$ANSYS_AGENT_HOME` or `~/.AnsysAgent`):

```
~/.AnsysAgent/
├── .env            ← LLM provider / API key config (written by /config)
├── memory/         ← persistent memories (*.md + MEMORY.md index)
├── .rag/           ← keyword_index.json (auto-built, delete to rebuild)
├── knowledge/      ← user-added docs (official/ and internal/)
├── logs/           ← rotating daily logs (30-day retention)
├── rules/          ← custom system rules (injected each turn)
├── skills/         ← user custom skills (<name>/SKILL.md)
└── mcp_servers.json
```

The project directory is **read-only at runtime** — never write files next to the source tree.

### LLM & Fallback

Config lives in `agent/config_manager.py`. The active provider/model is read from `ANSYS_DATA_DIR/.env`. On 429/402/503 errors the call automatically retries through `FALLBACK_CHAIN` (GLM → MiniMax) without interrupting the conversation. All Sub-Agents share the Main Agent's client instances.

### RAG

`rag/` uses BM25-style keyword matching (no embeddings). `build_index()` scans `docs/api/` and `knowledge/` at startup and writes `keyword_index.json`. Retrieval is triggered when the user message contains words from `_KNOWLEDGE_HINTS` in `chat_agent.py`. Delete `keyword_index.json` and restart to force a rebuild after adding docs.

### Skills

`skills/<name>/SKILL.md` files are loaded on demand via `use_skill` tool. The agent reads the full SKILL.md text and follows it verbatim. Built-in skills ship with the repo; user skills go in `ANSYS_DATA_DIR/skills/`.

## Key Conventions

- **Tool return contract**: always `{"success": True, "result": ...}` or `{"success": False, "error": "..."}`. Use `_ok()` / `_err()` / `ok_message()` from `tools/utils.py`.
- **Tool state**: global module-level variables (`_mapdl_app`, `_dpf_model`, etc.) are the lazy singleton pattern used across all tool files. Access via a module-level `_app()` / `_session()` helper that raises a descriptive error if not yet initialized.
- **Adding a Sub-Agent**: create file in `agent/sub_agents/`, inherit `SubAgentBase`, register in `ChatAgent._init_sub_agents()`, add `agent_name` enum value to `DELEGATE_TOOL_DEFINITION` in `tool_definitions.py`.
- **Adding a tool**: implement in `tools/`, then update all three locations in `tool_definitions.py` (registry + definitions list + frozenset). Run the syntax check: `python3 -c "import ast; ast.parse(open('agent/tool_definitions.py').read()); print('ok')"`.
