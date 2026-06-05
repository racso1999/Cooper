"""LLM clients and shared path configuration."""
from pathlib import Path

from langchain.chat_models import init_chat_model

BASE    = Path(__file__).parent.parent
DB_PATH = BASE / 'data' / 'orders.db'

COOPER_NODE_MODEL     = 'gpt-5.4-2026-03-05'
COOPER_COMPILER_MODEL = 'gpt-5.4-2026-03-05'
COOPER_RAG_MODEL      = 'gpt-5.4-2026-03-05'

cooper_llm   = init_chat_model(COOPER_NODE_MODEL)
compiler_llm = init_chat_model(COOPER_COMPILER_MODEL)
rag_llm      = init_chat_model(COOPER_RAG_MODEL)
