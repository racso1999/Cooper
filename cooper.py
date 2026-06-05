from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from typing import TypedDict, Literal, Annotated
import uuid
from pathlib import Path
 
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

import sqlite3

from part_lookup import get_part_info as fetch_part_info
from model_lookup import get_model_info as fetch_model_info

KNOWLEDGE_BASE = (Path(__file__).parent / 'repair_info.txt').read_text().splitlines()
vectorstore = InMemoryVectorStore(embedding=OpenAIEmbeddings(model='text-embedding-3-small'))
vectorstore.add_documents([Document(page_content=text) for text in KNOWLEDGE_BASE])




DB_PATH = Path(__file__).parent / 'orders.db'


# Each node uses its own model — tune cost vs capability independently
# Prefix google_genai: routes to Gemini API (AI Studio); requires GOOGLE_API_KEY in .env
# Note: compiler uses OpenAI — Gemini does not stream tokens via LangChain (returns one chunk)
COOPER_NODE_MODEL     = 'google_genai:gemini-3.5-flash'  # main routing brain
COOPER_COMPILER_MODEL = 'gpt-4o-mini'                          # response synthesis — must stream
COOPER_RAG_MODEL      = 'google_genai:gemini-3.5-flash'  # RAG synthesis

cooper_llm   = init_chat_model(COOPER_NODE_MODEL)
compiler_llm = init_chat_model(COOPER_COMPILER_MODEL)
rag_llm      = init_chat_model(COOPER_RAG_MODEL)


def _load_prompt(filename: str) -> str:
    return (Path(__file__).parent / 'prompts' / filename).read_text(encoding='utf-8').strip()


def _text(response) -> str:
    """Extract plain text from an LLM response regardless of provider format.
    OpenAI returns response.content as a string; Gemini returns a list of content blocks."""
    content = response.content
    if isinstance(content, str):
        return content
    return ''.join(
        block['text'] if isinstance(block, dict) else str(block)
        for block in content
        if not isinstance(block, dict) or block.get('type') == 'text'
    )


COOPER_SYSTEM_PROMPT   = _load_prompt('cooper_system.md')
COOPER_COMPILER_PROMPT = _load_prompt('cooper_compiler.md')


class CooperOutput(BaseModel):
    reply: str | None = Field(description="Cooper's response to the user. Null when routing to one or more specialist nodes — those nodes will provide the response.")
    intent: list[Literal['part_lookup', 'model_lookup', 'repair_lookup', 'order_lookup']] = Field(
        description="Specialist nodes to call. Return an empty list when no node is needed (greetings, chat, out-of-scope). Return multiple to fan out in parallel."
    )
    part_number: str | None = Field(default=None, description="PS part number extracted from the conversation (e.g. PS11752778). Required when part_lookup is in intent.")
    model_number: str | None = Field(default=None, description="Appliance model number extracted from the conversation (e.g. WDT780SAEM1). Always normalise to uppercase — if the user writes 'wdt780saem1', return 'WDT780SAEM1'. Required when model_lookup is in intent.")
    order_id: str | None = Field(default=None, description="Order ID extracted from the conversation (e.g. ORD-10042). Extract even when the user provides it as raw data without explicit phrasing. Required when order_lookup is in intent.")
    order_email: str | None = Field(default=None, description="Customer email extracted from the conversation. Extract even when given inline without preamble. Required when order_lookup is in intent.")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: list[str] | None
    part_number: str | None
    model_number: str | None
    order_id: str | None
    order_email: str | None
    # Raw data set by specialist nodes, read and cleared by cooper_compiler
    part_info: dict | None
    model_info: dict | None
    repair_info: str | None
    order_info: str | None


# Cached structured-output chain — uses cooper_llm
_cooper = cooper_llm.with_structured_output(CooperOutput)

# Tracks which specialist nodes fired in the current turn — printed before the response
_fired: list[str] = []


def cooper_node(state: State):
    result = _cooper.invoke([
        {'role': 'system', 'content': COOPER_SYSTEM_PROMPT},
        *state['messages']
    ])

    intent = list(result.intent)

    # Guard: strip lookup intents if required identifiers weren't extracted
    if 'part_lookup' in intent and not result.part_number:
        intent.remove('part_lookup')
    if 'model_lookup' in intent and not result.model_number:
        intent.remove('model_lookup')
    if 'order_lookup' in intent and not (result.order_id and result.order_email):
        intent.remove('order_lookup')

    updates: dict = {'intent': intent}

    if result.reply:
        updates['messages'] = [{'role': 'assistant', 'content': result.reply}]
    if result.part_number:
        updates['part_number'] = result.part_number
    if result.model_number:
        updates['model_number'] = result.model_number
    if result.order_id:
        updates['order_id'] = result.order_id
    if result.order_email:
        updates['order_email'] = result.order_email

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
        'name': info['name'],
        'price': info['price'],
        'image_url': info['image_url'],
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
        'model_number': info['model_number'],
        'brand': info['brand'],
        'appliance_type': info['appliance_type'],
        'symptoms': {
            symptom: {'part_number': parts[0]['part_number'], 'name': parts[0]['name'], 'fix_rate': parts[0]['fix_rate']}
            for symptom, parts in symptom_parts.items()
        }
    }}


def get_repair_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[RAG]')
    query = state['messages'][-1].content
    documents = vectorstore.similarity_search(query, k=3)

    context = '\n'.join(f'- {doc.page_content}' for doc in documents)

    messages = [
        {'role': 'system', 'content': f'You are a RAG agent. Answer the user using only the context below. If the answer is not in it, say you don\'t know.\n\nContext:\n{context}'},
    ] + state['messages']

    response = rag_llm.invoke(messages)

    return {'repair_info': _text(response)}


def get_order_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[ORDER]')
    # Both fields required — UPPER/LOWER for case-insensitive matching, prevents data leaks
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
        f"Date: {row['order_date']}\n"
        f"Status: {row['status']}\n"
        f"Total: ${row['total_amount']:.2f}\n"
        f"Items: {row['items']}"
    )}


def cooper_compiler(state: State):
    # Build a context block from whatever specialist nodes populated this turn
    sections = []

    if state.get('part_info'):
        info = state['part_info']
        if 'error' in info:
            sections.append(f"Part lookup: {info['error']}")
        else:
            sections.append(
                f"Part lookup result:\n"
                f"  Part number: {info['part_number']}\n"
                f"  Name: {info['name']}\n"
                f"  Price: {info['price'] or 'not listed'}\n"
                f"  Image URL: {info['image_url'] or 'not available'}"
            )

    if state.get('model_info'):
        info = state['model_info']
        if 'error' in info:
            sections.append(f"Model lookup: {info['error']}")
        else:
            symptom_lines = '\n'.join(
                f"    {symptom}: {data['name']} ({data['part_number']}) — {data['fix_rate']}% fix rate"
                for symptom, data in info['symptoms'].items()
            )
            sections.append(
                f"Model lookup result:\n"
                f"  Model: {info['model_number']}\n"
                f"  Brand: {info['brand']}\n"
                f"  Type: {info['appliance_type']}\n"
                f"  Symptoms and top fix:\n{symptom_lines}"
            )

    if state.get('repair_info'):
        sections.append(f"Repair info:\n  {state['repair_info']}")

    if state.get('order_info'):
        sections.append(f"Order lookup result:\n{state['order_info']}")

    context = '\n\n'.join(sections)

    # Stream tokens directly to the terminal as they arrive
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
    print()  # newline after stream ends

    # Clear all info fields after compiling
    return {
        'messages': [{'role': 'assistant', 'content': full_response}],
        'part_info': None,
        'model_info': None,
        'repair_info': None,
        'order_info': None,
    }


graph_builder = StateGraph(State)

graph_builder.add_node('cooper_node', cooper_node)
graph_builder.add_node('get_part_info', get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info', get_repair_info)
graph_builder.add_node('get_order_info', get_order_info)
graph_builder.add_node('cooper_compiler', cooper_compiler)

graph_builder.add_edge(START, 'cooper_node')
# Empty intent: Cooper already replied (chat/out-of-scope) — go straight to END
# Non-empty list: fan out to all matched specialist nodes
graph_builder.add_conditional_edges(
    'cooper_node',
    lambda state: state['intent'] if state['intent'] else 'done',
    {'part_lookup': 'get_part_info', 'model_lookup': 'get_model_info',
     'repair_lookup': 'get_repair_info', 'order_lookup': 'get_order_info', 'done': END}
)

# All specialist nodes feed into the compiler, which synthesises and ends the turn
graph_builder.add_edge('get_part_info', 'cooper_compiler')
graph_builder.add_edge('get_model_info', 'cooper_compiler')
graph_builder.add_edge('get_repair_info', 'cooper_compiler')
graph_builder.add_edge('get_order_info', 'cooper_compiler')
graph_builder.add_edge('cooper_compiler', END)

checkpointer = InMemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

graph.get_graph().draw_mermaid_png(output_file_path='graph.png')

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("> ")
    _fired.clear()
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config)

    # Agent path: compiler already printed tags and streamed the response — nothing to do.
    # Chat path: cooper_node replied directly (no nodes fired) — print it now.
    if not _fired:
        last_human = max(i for i, m in enumerate(result['messages']) if m.type == 'human')
        for msg in result['messages'][last_human + 1:]:
            if msg.type == 'ai':
                print(msg.content)
