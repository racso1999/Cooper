"""
nodes.py — State definition, LLM setup, and all node functions for the Cooper agent.
Imported by graph.py (wiring) and cooper.py (entrypoint).
"""

import sqlite3
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from part_lookup import get_part_info as fetch_part_info
from model_lookup import get_model_info as fetch_model_info

BASE    = Path(__file__).parent
DB_PATH = BASE / 'orders.db'

# ── Model configuration ───────────────────────────────────────────────────────
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
    """Extract plain text from an LLM response regardless of provider format.
    OpenAI: content is a string. Gemini: content is a list of typed blocks."""
    content = response.content
    if isinstance(content, str):
        return content
    return ''.join(
        block['text'] if isinstance(block, dict) else str(block)
        for block in content
        if not isinstance(block, dict) or block.get('type') == 'text'
    )

# ── Pydantic output schema ────────────────────────────────────────────────────
class CooperOutput(BaseModel):
    reply: str | None = Field(
        description="Cooper's response. Null when routing to specialist nodes.")
    intent: list[Literal['part_lookup', 'model_lookup', 'repair_lookup', 'order_lookup']] = Field(
        description="Nodes to call. Empty list for chat/greetings/out-of-scope.")
    part_number: str | None = Field(default=None,
        description="PS part number (e.g. PS11752778). Required when part_lookup is in intent.")
    model_number: str | None = Field(default=None,
        description="Appliance model number (e.g. WDT780SAEM1). Normalise to uppercase. Required when model_lookup is in intent.")
    order_id: str | None = Field(default=None,
        description="Order ID (e.g. ORD-10042). Required when order_lookup is in intent.")
    order_email: str | None = Field(default=None,
        description="Customer email. Required when order_lookup is in intent.")

# ── Graph state ───────────────────────────────────────────────────────────────
class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: list[str] | None
    part_number: str | None
    model_number: str | None
    order_id: str | None
    order_email: str | None
    part_info: dict | None   # raw data set by get_part_info, consumed by cooper_compiler
    model_info: dict | None  # raw data set by get_model_info, consumed by cooper_compiler
    repair_info: str | None  # raw data set by get_repair_info, consumed by cooper_compiler
    order_info: str | None   # raw data set by get_order_info, consumed by cooper_compiler

# ── Turn tracking ─────────────────────────────────────────────────────────────
# Tracks which specialist nodes fired this turn — cleared before each graph.invoke()
_fired: list[str] = []

_cooper = cooper_llm.with_structured_output(CooperOutput)

# ── Node functions ────────────────────────────────────────────────────────────
def cooper_node(state: State):
    result = _cooper.invoke([
        {'role': 'system', 'content': COOPER_SYSTEM_PROMPT},
        *state['messages']
    ])

    intent = list(result.intent)

    # Guard: strip intents whose required identifier wasn't extracted
    if 'part_lookup'  in intent and not result.part_number:  intent.remove('part_lookup')
    if 'model_lookup' in intent and not result.model_number: intent.remove('model_lookup')
    if 'order_lookup' in intent and not (result.order_id and result.order_email):
        intent.remove('order_lookup')

    updates: dict = {'intent': intent}
    if result.reply:        updates['messages']     = [{'role': 'assistant', 'content': result.reply}]
    if result.part_number:  updates['part_number']  = result.part_number
    if result.model_number: updates['model_number'] = result.model_number
    if result.order_id:     updates['order_id']     = result.order_id
    if result.order_email:  updates['order_email']  = result.order_email
    return updates


def get_part_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[PART]')
    info = fetch_part_info(state.get('part_number'))
    if not info:
        return {'part_info': {'error': f"I wasn't able to find part {state.get('part_number')} on PartSelect."}}
    return {'part_info': {
        'part_number': state.get('part_number'),
        'name':        info['name'],
        'price':       info['price'],
        'image_url':   info['image_url'],
    }}


def get_model_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[MODEL]')
    info = fetch_model_info(state.get('model_number'))
    if not info:
        return {'model_info': {'error': f"I wasn't able to find model {state.get('model_number')} on PartSelect."}}
    symptom_parts: dict[str, list] = {}
    for part in info['compatible_parts']:
        for symptom, rate in part['fixes'].items():
            symptom_parts.setdefault(symptom, []).append(
                {'part_number': part['part_number'], 'name': part['name'], 'fix_rate': rate or 0}
            )
    for parts in symptom_parts.values():
        parts.sort(key=lambda p: p['fix_rate'], reverse=True)
    return {'model_info': {
        'model_number':   info['model_number'],
        'brand':          info['brand'],
        'appliance_type': info['appliance_type'],
        'symptoms': {
            symptom: {'part_number': p[0]['part_number'], 'name': p[0]['name'], 'fix_rate': p[0]['fix_rate']}
            for symptom, p in symptom_parts.items()
        },
    }}


def get_repair_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[RAG]')
    query     = state['messages'][-1].content
    documents = vectorstore.similarity_search(query, k=3)
    context   = '\n'.join(f'- {doc.page_content}' for doc in documents)
    messages  = [
        {'role': 'system', 'content': (
            f"You are a RAG agent. Answer the user using only the context below. "
            f"If the answer is not in it, say you don't know.\n\nContext:\n{context}"
        )},
    ] + state['messages']
    return {'repair_info': _text(rag_llm.invoke(messages))}


def get_order_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[ORDER]')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT o.order_id, o.customer_name, o.order_date, o.status, o.total_amount,
               GROUP_CONCAT(i.product_id || ' - ' || i.product_name || ' (x' || i.quantity || ')', '; ') AS items
        FROM orders o
        JOIN order_items i ON i.order_id = o.order_id
        WHERE UPPER(o.order_id)       = UPPER(?)
          AND LOWER(o.customer_email) = LOWER(?)
        GROUP BY o.order_id
    """, (state.get('order_id', '').strip(), state.get('order_email', '').strip())).fetchone()
    conn.close()
    if not row:
        return {'order_info': "No order found matching that order ID and email. Please check both and try again."}
    return {'order_info': (
        f"Order ID: {row['order_id']}\n"
        f"Customer: {row['customer_name']}\n"
        f"Date:     {row['order_date']}\n"
        f"Status:   {row['status']}\n"
        f"Total:    ${row['total_amount']:.2f}\n"
        f"Items:    {row['items']}"
    )}


def cooper_compiler(state: State):
    sections = []

    if state.get('part_info'):
        info = state['part_info']
        sections.append(info.get('error') or (
            f"Part lookup result:\n"
            f"  Part number: {info['part_number']}\n"
            f"  Name: {info['name']}\n"
            f"  Price: {info['price'] or 'not listed'}\n"
            f"  Image URL: {info['image_url'] or 'not available'}"
        ))

    if state.get('model_info'):
        info = state['model_info']
        if 'error' in info:
            sections.append(info['error'])
        else:
            symptom_lines = '\n'.join(
                f"    {sym}: {d['name']} ({d['part_number']}) — {d['fix_rate']}% fix rate"
                for sym, d in info['symptoms'].items()
            )
            sections.append(
                f"Model lookup result:\n"
                f"  Model: {info['model_number']}\n"
                f"  Brand: {info['brand']}\n"
                f"  Type:  {info['appliance_type']}\n"
                f"  Symptoms and top fix:\n{symptom_lines}"
            )

    if state.get('repair_info'):
        sections.append(f"Repair info:\n  {state['repair_info']}")

    if state.get('order_info'):
        sections.append(f"Order lookup result:\n{state['order_info']}")

    context       = '\n\n'.join(sections)
    full_response = ''
    for chunk in compiler_llm.stream([
        {'role': 'system', 'content': COOPER_COMPILER_PROMPT},
        {'role': 'system', 'content': f"Retrieved data:\n\n{context}"},
        *state['messages']
    ]):
        text = _text(chunk)
        if text:
            print(text, end='', flush=True)
            full_response += text
    print()

    return {
        'messages':    [{'role': 'assistant', 'content': full_response}],
        'part_info':   None,
        'model_info':  None,
        'repair_info': None,
        'order_info':  None,
    }
