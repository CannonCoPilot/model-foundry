#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server
Provides file system access, code execution, and LLM interaction
For integration with Roo Code, Cline, Aider, etc.
Base Path: /mnt/ai8_arch
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import subprocess

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server for Agentic Coding")

# Configuration
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "/workspace"))
WORKSPACE_DIR.mkdir(exist_ok=True)

http_client = httpx.AsyncClient(timeout=300.0)

# MCP Protocol Models
class ReadFileRequest(BaseModel):
    path: str

class WriteFileRequest(BaseModel):
    path: str
    content: str

class ExecuteCommandRequest(BaseModel):
    command: str
    args: List[str] = []
    cwd: str = None

class LLMRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "gpt-oss-120b"
    temperature: float = 0.7
    max_tokens: int = 4096

# File System Operations
@app.post("/fs/read")
async def read_file(request: ReadFileRequest):
    """Read file from workspace"""
    file_path = WORKSPACE_DIR / request.path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not str(file_path).startswith(str(WORKSPACE_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        content = file_path.read_text()
        return {"path": request.path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fs/write")
async def write_file(request: WriteFileRequest):
    """Write file to workspace"""
    file_path = WORKSPACE_DIR / request.path
    
    if not str(file_path).startswith(str(WORKSPACE_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content)
        return {"path": request.path, "status": "written"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fs/list")
async def list_files(path: str = "."):
    """List files in workspace directory"""
    dir_path = WORKSPACE_DIR / path
    
    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    
    if not str(dir_path).startswith(str(WORKSPACE_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        files = [
            {
                "name": f.name,
                "type": "directory" if f.is_dir() else "file",
                "size": f.stat().st_size if f.is_file() else None
            }
            for f in dir_path.iterdir()
        ]
        return {"path": path, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Code Execution
@app.post("/exec")
async def execute_command(request: ExecuteCommandRequest):
    """Execute command in workspace"""
    cwd = WORKSPACE_DIR / (request.cwd or ".")
    
    if not str(cwd).startswith(str(WORKSPACE_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        result = subprocess.run(
            [request.command] + request.args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# LLM Integration
@app.post("/llm/chat")
async def chat_completion(request: LLMRequest):
    """Chat completion through LiteLLM"""
    try:
        response = await http_client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            json={
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent Workflow
@app.post("/agent/plan")
async def create_plan(task: str, model: str = "gpt-oss-120b"):
    """Create execution plan for task"""
    messages = [
        {"role": "system", "content": "You are a coding assistant. Break down tasks into actionable steps."},
        {"role": "user", "content": f"Task: {task}\n\nCreate a step-by-step plan to accomplish this task."}
    ]
    
    response = await chat_completion(LLMRequest(messages=messages, model=model))
    plan = response["choices"][0]["message"]["content"]
    
    return {"task": task, "plan": plan}

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "workspace": str(WORKSPACE_DIR),
        "litellm": LITELLM_URL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```