"""
Chat agent: main conversation loop with tool-use support via Anthropic Claude.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.prompt import SYSTEM_PROMPT
from tools import maxwell_tools, result_tools

console = Console()

# ---------------------------------------------------------------------------
# Tool registry: maps tool name -> callable
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "connect_aedt": maxwell_tools.connect_aedt,
    "create_maxwell_project": maxwell_tools.create_maxwell_project,
    "create_motor_geometry": maxwell_tools.create_motor_geometry,
    "assign_material": maxwell_tools.assign_material,
    "setup_winding": maxwell_tools.setup_winding,
    "add_solution_setup": maxwell_tools.add_solution_setup,
    "run_simulation": maxwell_tools.run_simulation,
    "get_torque": result_tools.get_torque,
    "get_back_emf": result_tools.get_back_emf,
    "get_flux_density": result_tools.get_flux_density,
    "get_losses": result_tools.get_losses,
    "export_results": result_tools.export_results,
}

# ---------------------------------------------------------------------------
# Tool definitions for Claude API
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "connect_aedt",
        "description": "Connect to a running AEDT instance or launch a new one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "description": "AEDT version, e.g. '2024.1'"},
                "is_3d": {"type": "boolean", "description": "True for Maxwell 3D, False for Maxwell 2D"},
                "non_graphical": {"type": "boolean", "description": "Run without GUI"},
            },
        },
    },
    {
        "name": "create_maxwell_project",
        "description": "Create a new Maxwell 2D/3D project and design.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "design_name": {"type": "string"},
            },
            "required": ["project_name"],
        },
    },
    {
        "name": "create_motor_geometry",
        "description": "Build PMSM motor geometry in Maxwell 2D (stator, rotor, magnets, air gap).",
        "input_schema": {
            "type": "object",
            "properties": {
                "stator_outer_radius": {"type": "number", "description": "mm"},
                "stator_inner_radius": {"type": "number", "description": "mm"},
                "rotor_outer_radius": {"type": "number", "description": "mm"},
                "rotor_inner_radius": {"type": "number", "description": "mm"},
                "num_slots": {"type": "integer"},
                "num_poles": {"type": "integer"},
                "magnet_thickness": {"type": "number", "description": "mm"},
                "stack_length": {"type": "number", "description": "mm, axial length"},
            },
            "required": [
                "stator_outer_radius", "stator_inner_radius",
                "rotor_outer_radius", "rotor_inner_radius",
                "num_slots", "num_poles", "magnet_thickness",
            ],
        },
    },
    {
        "name": "assign_material",
        "description": "Assign a material to a geometry object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
                "material_name": {"type": "string"},
            },
            "required": ["object_name", "material_name"],
        },
    },
    {
        "name": "setup_winding",
        "description": "Configure a winding phase excitation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phase_name": {"type": "string"},
                "conductor_names": {"type": "array", "items": {"type": "string"}},
                "current_amplitude": {"type": "number", "description": "Peak current in A"},
                "frequency": {"type": "number", "description": "Electrical frequency in Hz"},
                "phase_angle": {"type": "number", "description": "Phase angle in degrees"},
            },
            "required": ["phase_name", "conductor_names", "current_amplitude"],
        },
    },
    {
        "name": "add_solution_setup",
        "description": "Add a solver setup (Transient / Magnetostatic / EddyCurrent).",
        "input_schema": {
            "type": "object",
            "properties": {
                "solver_type": {"type": "string", "enum": ["Transient", "Magnetostatic", "EddyCurrent"]},
                "stop_time": {"type": "number", "description": "seconds"},
                "time_step": {"type": "number", "description": "seconds"},
                "num_passes": {"type": "integer"},
            },
        },
    },
    {
        "name": "run_simulation",
        "description": "Run (analyze) the simulation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "setup_name": {"type": "string"},
            },
        },
    },
    {
        "name": "get_torque",
        "description": "Extract average torque and torque waveform.",
        "input_schema": {
            "type": "object",
            "properties": {
                "setup_name": {"type": "string"},
                "sweep_name": {"type": "string"},
            },
        },
    },
    {
        "name": "get_back_emf",
        "description": "Extract back-EMF waveform for a phase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phase_name": {"type": "string"},
                "setup_name": {"type": "string"},
            },
        },
    },
    {
        "name": "get_flux_density",
        "description": "Get flux density at a point.",
        "input_schema": {
            "type": "object",
            "properties": {
                "setup_name": {"type": "string"},
                "point": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z] mm"},
            },
        },
    },
    {
        "name": "get_losses",
        "description": "Get average iron and copper losses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "setup_name": {"type": "string"},
            },
        },
    },
    {
        "name": "export_results",
        "description": "Export results to CSV.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "result_type": {"type": "string", "enum": ["torque", "back_emf", "losses"]},
            },
            "required": ["output_path"],
        },
    },
]


# ---------------------------------------------------------------------------
# ChatAgent class
# ---------------------------------------------------------------------------

class ChatAgent:
    def __init__(self, model: str = "claude-opus-4-5"):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model
        self.history: list[dict] = []

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return its result as a JSON string."""
        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
        try:
            result = fn(**tool_input)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def chat(self, user_message: str) -> str:
        """Send a user message and return the final assistant response."""
        self.history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=self.history,
            )

            # Collect assistant content blocks
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self.history.append({"role": "assistant", "content": assistant_content})

            # If no tool calls, we're done
            if response.stop_reason != "tool_use":
                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                return final_text

            # Execute all tool calls
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                console.print(f"[dim]🔧 Calling tool: [bold]{block.name}[/bold] {json.dumps(block.input, ensure_ascii=False)}[/dim]")
                result_str = self._execute_tool(block.name, block.input)
                result_data = json.loads(result_str)
                if result_data.get("success"):
                    console.print(f"[green]  ✓ {result_data.get('result', 'OK')}[/green]")
                else:
                    console.print(f"[red]  ✗ {result_data.get('error', 'Error')}[/red]")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            self.history.append({"role": "user", "content": tool_results})
