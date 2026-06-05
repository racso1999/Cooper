"""Shared configuration: models, LLMs, prompts, vectorstore, utilities, turn tracking."""

from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

BASE    = Path(__file__).parent.parent   # system/
DB_PATH = BASE / 'orders.db'

# ── Models ────────────────────────────────────────────────────────────────────
# Note: compiler uses OpenAI — Gemini does not stream tokens via LangChain
COOPER_NODE_MODEL     = 'google_genai:gemini-3.5-flash'
COOPER_COMPILER_MODEL = 'gpt-4o-mini'                    # must stream
COOPER_RAG_MODEL      = 'google_genai:gemini-3.5-flash'

cooper_llm   = init_chat_model(COOPER_NODE_MODEL)
compiler_llm = init_chat_model(COOPER_COMPILER_MODEL)
rag_llm      = init_chat_model(COOPER_RAG_MODEL)

# ── Prompts ───────────────────────────────────────────────────────────────────
def _load_prompt(filename: str) -> str:
    return (BASE / 'prompts' / filename).read_text(encoding='utf-8').strip()

COOPER_SYSTEM_PROMPT   = _load_prompt('cooper_system.md')
COOPER_COMPILER_PROMPT = _load_prompt('cooper_compiler.md')

# ── Vectorstore ───────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = (BASE / 'repair_info.txt').read_text().splitlines()
vectorstore    = InMemoryVectorStore(embedding=OpenAIEmbeddings(model='text-embedding-3-small'))
vectorstore.add_documents([Document(page_content=text) for text in KNOWLEDGE_BASE])

# ── Utilities ─────────────────────────────────────────────────────────────────
def _text(response) -> str:
    """Extract plain text regardless of provider format.
    OpenAI: content is a string. Gemini: content is a list of typed blocks."""
    content = response.content
    if isinstance(content, str):
        return content
    return ''.join(
        block['text'] if isinstance(block, dict) else str(block)
        for block in content
        if not isinstance(block, dict) or block.get('type') == 'text'
    )

# ── Turn tracking ─────────────────────────────────────────────────────────────
# Cleared before each graph.invoke(); appended to by specialist nodes
_fired: list[str] = []
