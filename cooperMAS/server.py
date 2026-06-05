import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import graph
from nodes import _fired

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

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    _fired.clear()
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config=config,
    )
    last_human = max(i for i, m in enumerate(result["messages"]) if m.type == "human")
    reply = next(
        (m.content for m in reversed(result["messages"][last_human + 1:]) if m.type == "ai"),
        "",
    )
    return ChatResponse(reply=reply)
