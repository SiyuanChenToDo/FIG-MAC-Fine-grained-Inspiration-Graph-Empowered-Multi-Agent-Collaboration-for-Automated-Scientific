"""
Demo Streamer - Streams pre-recorded workflow data as SSE events
Simulates the full pipeline with realistic timing
"""

import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator

DEMO_DATA_PATH = Path(__file__).parent.parent / "static" / "data" / "demo_workflow.json"


def sse(event: str, data: dict) -> dict:
    """Build SSE event dict with JSON-serialized data"""
    return {
        "event": event,
        "data": json.dumps(data, ensure_ascii=False)
    }


async def stream_demo(topic: str, speed: float = 1.0) -> AsyncGenerator[dict, None]:
    """
    Stream demo workflow data as SSE events.
    Yields dict with 'event' and 'data' keys for EventSourceResponse.
    """
    with open(DEMO_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    yield sse("workflow_start", {
        "topic": data["topic"],
        "total_phases": len(data["phases"]),
        "graph_stats": data.get("graph_stats", {})
    })
    await asyncio.sleep(0.5 / speed)
    
    for phase_idx, phase in enumerate(data["phases"]):
        phase_name = phase["name"]
        
        yield sse("phase_start", {
            "phase": phase_name,
            "display_name": phase.get("display_name", phase_name),
            "icon": phase.get("icon", "📋"),
            "index": phase_idx,
            "total": len(data["phases"])
        })
        await asyncio.sleep(0.3 / speed)
        
        if "think_steps" in phase:
            for step in phase["think_steps"]:
                yield sse("think", {
                    "phase": phase_name,
                    "content": step["content"]
                })
                await asyncio.sleep(step.get("delay", 0.3) / speed)
        
        # Handle parallel analysis agents
        if phase.get("execution") == "parallel" and "agents" in phase:
            for agent in phase["agents"]:
                yield sse("agent_start", {
                    "phase": phase_name,
                    "agent": agent["name"],
                    "icon": agent["icon"],
                    "role": agent["role"]
                })
            await asyncio.sleep(0.3 / speed)
            
            max_steps = max(len(a["think_steps"]) for a in phase["agents"])
            for step_idx in range(max_steps):
                for agent in phase["agents"]:
                    if step_idx < len(agent["think_steps"]):
                        step = agent["think_steps"][step_idx]
                        yield sse("agent_think", {
                            "phase": phase_name,
                            "agent": agent["name"],
                            "icon": agent["icon"],
                            "content": step["content"]
                        })
                        await asyncio.sleep(step.get("delay", 0.3) / speed / len(phase["agents"]))
            
            for agent in phase["agents"]:
                yield sse("agent_complete", {
                    "phase": phase_name,
                    "agent": agent["name"],
                    "icon": agent["icon"],
                    "content_length": len(agent.get("content", "")),
                    "metadata": agent.get("metadata", {})
                })
                # Send full LLM output after completion
                if agent.get("content"):
                    # Send in chunks to simulate streaming the full response
                    full_content = agent["content"]
                    chunk_size = 2000
                    for i in range(0, len(full_content), chunk_size):
                        chunk = full_content[i:i+chunk_size]
                        yield sse("agent_full_output", {
                            "phase": phase_name,
                            "agent": agent["name"],
                            "icon": agent["icon"],
                            "role": agent["role"],
                            "content_chunk": chunk,
                            "chunk_index": i // chunk_size,
                            "total_chunks": (len(full_content) + chunk_size - 1) // chunk_size,
                            "content_length": len(full_content)
                        })
                        await asyncio.sleep(0.05 / speed)
        
        # Handle sequential agent
        elif "agent" in phase and "think_steps" in phase:
            yield sse("agent_start", {
                "phase": phase_name,
                "agent": phase["agent"],
                "icon": phase.get("icon", "🤖"),
                "role": phase.get("agent_role", "")
            })
            
            # Stream content preview for literature/ideation/synthesis/review/polish
            if phase_name in ["literature", "ideation", "synthesis", "review", "polish"] and "content" in phase:
                content = phase["content"]
                chunk_size = 300
                for i in range(0, min(len(content), 2000), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield sse("agent_content", {
                        "phase": phase_name,
                        "agent": phase["agent"],
                        "content": chunk,
                        "is_preview": True
                    })
                    await asyncio.sleep(0.15 / speed)
            
            yield sse("agent_complete", {
                "phase": phase_name,
                "agent": phase["agent"],
                "icon": phase.get("icon", "🤖"),
                "content_length": len(phase.get("content", "")),
                "metadata": phase.get("metadata", {})
            })
            
            # Send full LLM output in chunks to simulate streaming
            if phase.get("content"):
                full_content = phase["content"]
                chunk_size = 2000
                for i in range(0, len(full_content), chunk_size):
                    chunk = full_content[i:i+chunk_size]
                    yield sse("agent_full_output", {
                        "phase": phase_name,
                        "agent": phase["agent"],
                        "icon": phase.get("icon", "🤖"),
                        "role": phase.get("agent_role", ""),
                        "content_chunk": chunk,
                        "chunk_index": i // chunk_size,
                        "total_chunks": (len(full_content) + chunk_size - 1) // chunk_size,
                        "content_length": len(full_content)
                    })
                    await asyncio.sleep(0.05 / speed)
        
        phase_meta = {}
        if "score" in phase:
            phase_meta["score"] = phase["score"]
        if "threshold" in phase:
            phase_meta["threshold"] = phase["threshold"]
        if "scores" in phase:
            phase_meta["scores"] = phase["scores"]
        
        yield sse("phase_end", {
            "phase": phase_name,
            "display_name": phase.get("display_name", phase_name),
            **phase_meta
        })
        await asyncio.sleep(0.5 / speed)
    
    # Send inspiration paths
    if "inspiration_paths" in data:
        for path in data["inspiration_paths"]:
            yield sse("inspiration_path", path)
            await asyncio.sleep(0.3 / speed)
    
    # Send final results
    final_content = ""
    for phase in data["phases"]:
        if phase["name"] == "polish" and "content" in phase:
            final_content = phase["content"]
        elif phase["name"] == "synthesis" and not final_content and "content" in phase:
            final_content = phase["content"]
    
    scores = {}
    for phase in data["phases"]:
        if "scores" in phase:
            scores = phase["scores"]
    
    yield sse("workflow_complete", {
        "topic": data["topic"],
        "final_content": final_content,
        "scores": scores,
        "total_phases": len(data["phases"]),
        "inspiration_paths": data.get("inspiration_paths", []),
        "graph_stats": data.get("graph_stats", {})
    })
