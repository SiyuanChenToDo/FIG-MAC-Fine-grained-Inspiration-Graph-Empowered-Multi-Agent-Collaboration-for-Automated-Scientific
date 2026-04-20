"""
Scientific Hypothesis Generation System - Web Demo
FastAPI backend with SSE streaming
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_demo.streamers.demo_streamer import stream_demo
from web_demo.streamers.realtime_streamer import stream_realtime

# Global state
_app_state = {
    "pipeline_ready": False,
    "faiss_ready": False,
    "agents_ready": False,
    "pipeline_status_msg": "未加载"
}


def _check_system_status():
    """Check if the core system components are available"""
    status = {
        "graphstorm_model": False,
        "faiss_index": False,
        "camel_agents": False,
        "neo4j": False
    }
    msgs = []
    
    # Check GraphStorm model
    model_path = PROJECT_ROOT / "workspace" / "inference_results" / "custom_kg_v6c" / "predictions"
    if model_path.exists():
        status["graphstorm_model"] = True
        msgs.append("GraphStorm 模型就绪")
    else:
        msgs.append("GraphStorm 模型未找到")
    
    # Check FAISS index
    faiss_path = PROJECT_ROOT / "data" / "rq_faiss.index"
    if faiss_path.exists():
        status["faiss_index"] = True
        msgs.append("FAISS 索引就绪")
    else:
        msgs.append("FAISS 索引未找到")
    
    # Check Neo4j export data
    neo4j_path = PROJECT_ROOT / "data" / "graph_data" / "data"
    if neo4j_path.exists():
        status["neo4j"] = True
        msgs.append("Neo4j 数据就绪")
    else:
        msgs.append("Neo4j 数据未找到")
    
    # Check CAMEL (just check if module is importable)
    try:
        import camel
        status["camel_agents"] = True
        msgs.append("CAMEL 框架就绪")
    except ImportError:
        msgs.append("CAMEL 框架未安装")
    
    _app_state["pipeline_ready"] = status["graphstorm_model"] and status["faiss_index"]
    _app_state["faiss_ready"] = status["faiss_index"]
    _app_state["agents_ready"] = status["camel_agents"]
    _app_state["pipeline_status_msg"] = "; ".join(msgs)
    
    return status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    _check_system_status()
    yield


app = FastAPI(
    title="科学假设自动生成系统",
    description="基于 GraphStorm GNN + CAMEL 多智能体协作的科学假设生成",
    version="1.0.0",
    lifespan=lifespan
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main SPA"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/status")
async def status():
    """Get system component status"""
    status = _check_system_status()
    return {
        "graphstorm_model": status["graphstorm_model"],
        "faiss_index": status["faiss_index"],
        "camel_agents": status["camel_agents"],
        "neo4j": status["neo4j"],
        "pipeline_ready": _app_state["pipeline_ready"],
        "message": _app_state["pipeline_status_msg"]
    }


@app.post("/api/demo/start")
async def start_demo(request: Request):
    """Start demo mode - streams pre-recorded workflow data"""
    body = await request.json()
    topic = body.get("topic", "")
    speed = body.get("speed", 1.0)
    
    async def event_generator():
        async for event in stream_demo(topic, speed=speed):
            yield event
    
    return EventSourceResponse(event_generator())


@app.post("/api/realtime/start")
async def start_realtime(request: Request):
    """Start realtime mode - actually runs the multi-agent system"""
    body = await request.json()
    topic = body.get("topic", "")
    max_iterations = body.get("max_iterations", 3)
    quality_threshold = body.get("quality_threshold", 8.0)
    
    if not _app_state["agents_ready"]:
        async def error_stream():
            yield {
                "event": "error",
                "data": json.dumps({"message": "CAMEL 框架未安装，无法启动实时模式"}, ensure_ascii=False)
            }
        return EventSourceResponse(error_stream())
    
    async def event_generator():
        try:
            async for event in stream_realtime(
                topic=topic,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold
            ):
                yield event
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"实时模式出错: {str(e)}"}, ensure_ascii=False)
            }
    
    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
