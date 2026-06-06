import sys
import json
import logging
import time
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('cooper')


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
        t0 = time.perf_counter()
        log.info('→  %s', req.message[:80])
        config = {"configurable": {"thread_id": req.thread_id}}

        async for chunk in graph.astream(
            {"messages": [{"role": "user", "content": req.message}]},
            config=config,
        ):
            if "cooper_node" in chunk:
                intent = chunk["cooper_node"].get("intent") or []
                messages = chunk["cooper_node"].get("messages") or []
                if intent:
                    # Cooper identified a specialist task — notify the frontend while nodes run
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching some more information, hold tight...'})}\n\n"
                elif messages:
                    # Cooper answered directly (no specialist needed) — send reply immediately
                    msg = messages[-1]
                    content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                    yield f"data: {json.dumps({'type': 'reply', 'message': content})}\n\n"

            elif "compiler_node" in chunk:
                # Compiler has assembled the specialist data into a final response
                messages = chunk["compiler_node"].get("messages") or []
                if messages:
                    msg = messages[-1]
                    content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                    yield f"data: {json.dumps({'type': 'reply', 'message': content})}\n\n"

        elapsed = time.perf_counter() - t0
        nodes = ' '.join(_fired) if _fired else 'direct'
        log.info('←  [%s]  %.2fs', nodes, elapsed)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
