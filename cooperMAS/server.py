import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph import graph
from functions import _fired


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        _fired.clear()
        config = {"configurable": {"thread_id": req.thread_id}}

        async for chunk in graph.astream(
            {"messages": [{"role": "user", "content": req.message}]},
            config=config,
        ):
            if "cooper_node" in chunk:
                intent = chunk["cooper_node"].get("intent") or []
                messages = chunk["cooper_node"].get("messages") or []
                if intent:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching some more information, hold tight...'})}\n\n"
                elif messages:
                    msg = messages[-1]
                    content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                    yield f"data: {json.dumps({'type': 'reply', 'message': content})}\n\n"

            elif "compiler_node" in chunk:
                messages = chunk["compiler_node"].get("messages") or []
                if messages:
                    msg = messages[-1]
                    content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                    yield f"data: {json.dumps({'type': 'reply', 'message': content})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
