from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing import TypedDict, Literal, Annotated
import uuid
from pathlib import Path

from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

from part_lookup import get_part_info as fetch_part_info
from model_lookup import get_model_info as fetch_model_info


llm = init_chat_model('gpt-4o-mini')


def _load_prompt(filename: str) -> str:
    return (Path(__file__).parent / 'prompts' / filename).read_text(encoding='utf-8').strip()


COOPER_SYSTEM_PROMPT = _load_prompt('cooper.md')
COOPER_PART_PROMPT   = _load_prompt('part_lookup.md')
COOPER_MODEL_PROMPT  = _load_prompt('model_lookup.md')


class CooperOutput(BaseModel):
    reply: str | None = Field(description="Cooper's response to the user. Null when routing to one or more specialist nodes — those nodes will provide the response.")
    intent: list[Literal['part_lookup', 'model_lookup', 'repair_lookup', 'order_lookup']] = Field(
        description="Specialist nodes to call. Return an empty list when no node is needed (greetings, chat, out-of-scope). Return multiple to fan out in parallel."
    )
    part_number: str | None = Field(default=None, description="PS part number extracted from the conversation. Required when part_lookup is in intent.")
    model_number: str | None = Field(default=None, description="Appliance model number extracted from the conversation. Required when model_lookup is in intent.")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: list[str] | None
    part_number: str | None
    model_number: str | None
    part_info: dict | None  # raw data returned by get_part_info for Cooper to format


# Cached structured-output chain
_cooper = llm.with_structured_output(CooperOutput)


def cooper_node(state: State):
    # Returning from get_part_info — format the raw data and respond
    if state.get('part_info'):
        info = state['part_info']
        if 'error' in info:
            return {'intent': [], 'part_info': None, 'messages': [{'role': 'assistant', 'content': info['error']}]}
        part_context = (
            f"Part number: {info['part_number']}\n"
            f"Name: {info['name']}\n"
            f"Price: {info['price'] or 'not listed'}\n"
            f"Image URL: {info['image_url'] or 'not available'}"
        )
        response = llm.invoke([
            {'role': 'system', 'content': COOPER_PART_PROMPT},
            {'role': 'system', 'content': part_context},
            *state['messages']
        ])
        return {'intent': [], 'part_info': None, 'messages': [{'role': 'assistant', 'content': response.content}]}

    # Returning from any other specialist node — it already added its response, end the turn
    if state['messages'][-1].type != 'human':
        return {'intent': []}

    result = _cooper.invoke([
        {'role': 'system', 'content': COOPER_SYSTEM_PROMPT},
        *state['messages']
    ])

    intent = list(result.intent)

    # Guard: strip lookup intents if the required identifier wasn't extracted
    if 'part_lookup' in intent and not result.part_number:
        intent.remove('part_lookup')
    if 'model_lookup' in intent and not result.model_number:
        intent.remove('model_lookup')

    updates: dict = {'intent': intent}

    if result.reply:
        updates['messages'] = [{'role': 'assistant', 'content': result.reply}]
    if result.part_number:
        updates['part_number'] = result.part_number
    if result.model_number:
        updates['model_number'] = result.model_number

    return updates


def get_part_info(state: State):
    # Fetch only — no LLM call. Raw data is stored in state for cooper_node to format.
    info = fetch_part_info(state.get('part_number'))

    if not info:
        return {'part_info': {'error': f"I wasn't able to find part {state.get('part_number')} on PartSelect. Double-check the number and try again."}}

    return {'part_info': {
        'part_number': state.get('part_number'),
        'name': info['name'],
        'price': info['price'],
        'image_url': info['image_url'],
    }}


def get_model_info(state: State):
    info = fetch_model_info(state.get('model_number'))

    if not info:
        return {'messages': [{'role': 'assistant', 'content': f"I wasn't able to find model {state.get('model_number')} on PartSelect. Double-check the number and try again."}]}

    symptom_parts: dict[str, list] = {}
    for part in info['compatible_parts']:
        for symptom, rate in part['fixes'].items():
            symptom_parts.setdefault(symptom, []).append(
                {'part_number': part['part_number'], 'name': part['name'], 'fix_rate': rate or 0}
            )
    for parts in symptom_parts.values():
        parts.sort(key=lambda p: p['fix_rate'], reverse=True)

    symptom_lines = '\n'.join(
        f"  {symptom}: {parts[0]['name']} ({parts[0]['part_number']}) — {parts[0]['fix_rate']}% fix rate"
        for symptom, parts in symptom_parts.items()
    )
    model_context = (
        f"Model: {info['model_number']}\n"
        f"Brand: {info['brand']}\n"
        f"Type: {info['appliance_type']}\n"
        f"Known symptoms and top fix for each:\n{symptom_lines}"
    )

    response = llm.invoke([
        {'role': 'system', 'content': COOPER_MODEL_PROMPT},
        {'role': 'system', 'content': model_context},
        *state['messages']
    ])
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


def get_repair_info(state: State):
    # TODO: implement repair RAG
    return {'messages': [{'role': 'assistant', 'content': 'REPAIR RAG'}]}


def get_order_info(state: State):
    # TODO: implement order lookup
    return {'messages': [{'role': 'assistant', 'content': 'ORDER LOOKUP'}]}


graph_builder = StateGraph(State)

graph_builder.add_node('cooper_node', cooper_node)
graph_builder.add_node('get_part_info', get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info', get_repair_info)
graph_builder.add_node('get_order_info', get_order_info)

graph_builder.add_edge(START, 'cooper_node')
graph_builder.add_conditional_edges(
    'cooper_node',
    lambda state: state['intent'] if state['intent'] else 'done',
    {'part_lookup': 'get_part_info', 'model_lookup': 'get_model_info',
     'repair_lookup': 'get_repair_info', 'order_lookup': 'get_order_info', 'done': END}
)

# All specialist nodes return to cooper_node — it detects the AI response and exits cleanly
graph_builder.add_edge('get_part_info', 'cooper_node')
graph_builder.add_edge('get_model_info', 'cooper_node')
graph_builder.add_edge('get_repair_info', 'cooper_node')
graph_builder.add_edge('get_order_info', 'cooper_node')

checkpointer = InMemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

graph.get_graph().draw_mermaid_png(output_file_path='graph.png')

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("Enter your query: ")
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config)

    last_human = max(i for i, m in enumerate(result['messages']) if m.type == 'human')
    for msg in result['messages'][last_human + 1:]:
        if msg.type == 'ai':
            print(msg.content)
