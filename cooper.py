from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing import TypedDict, Literal, Annotated
import uuid

from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv()

from part_lookup import get_part_info as fetch_part_info


llm = init_chat_model('gpt-5.4-mini')
# Separate tiny model for cheap scope checking — runs on every message
scope_llm = init_chat_model('gpt-4o-mini')

SCOPE_SYSTEM_PROMPT = """You are a scope checker for Cooper, the PartSelect assistant. PartSelect sells refrigerator and dishwasher parts only.

Mark as IN SCOPE only if the message is about:
- Refrigerator or dishwasher parts, models, symptoms, repairs, or compatibility
- Looking up a customer order for a refrigerator or dishwasher part
- A greeting or opening message (e.g. "hi", "hello", "can you help me?")

Mark as OUT OF SCOPE if the message is about:
- Any other appliance (washing machines, ovens, microwaves, dryers, etc.)
- General cooking, home improvement, or unrelated shopping
- Anything with no connection to refrigerator or dishwasher parts

Be strict. When in doubt, mark OUT OF SCOPE."""

COOPER_OUT_OF_SCOPE_PROMPT = """You are Cooper, a warm and direct assistant for PartSelect, specialising exclusively in refrigerator and dishwasher parts.
The user has asked something outside your scope. Politely let them know you can't help with that, and steer them back toward what you can help with.
Plain text only — no markdown, no bullet points. Keep it brief and friendly."""

COOPER_CHAT_PROMPT = """You are Cooper, a helpful assistant for PartSelect, specialising exclusively in refrigerator and dishwasher parts.
Respond warmly and concisely. If the user hasn't asked for anything specific yet, invite them to share what they need help with."""

COOPER_PART_PROMPT = """You are Cooper, a precise and enthusiastic assistant for PartSelect.
You have just retrieved live part data from PartSelect. Present it in Cooper's voice.
Plain text only — no markdown, no bullet points, no bold, no colons used as headers.
Write in flowing sentences. Be warm, direct, and specific. State the part name, price, and part number confidently."""


class ScopeCheck(BaseModel):
    in_scope: bool = Field(description="True if the query relates to refrigerator or dishwasher parts/repairs on PartSelect, or is a greeting. False otherwise.")

class PartNumberExtractor(BaseModel):
    part_number: str | None = Field(description="The most recent PS part number in the conversation (e.g. PS11752778). None if not present.")

class ModelNumberExtractor(BaseModel):
    model_number: str | None = Field(description="The appliance model number in the conversation (e.g. WDT780SAEM1). None if not present.")

class IntentClassifier(BaseModel):
    # List allows multiple intents — LangGraph fans out to each corresponding node in parallel
    message_intent: list[Literal['model_lookup', 'part_lookup', 'order_lookup', 'repairRAG']] = Field(
        description="Classify which agent(s) to call. Options: model_lookup (look up a model), part_lookup (find a part), order_lookup (track an order), repairRAG (repair guidance). Return multiple if several agents are needed. Return an empty list if no specific agent is needed (e.g. greeting or general chat)."
    )

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: list[str] | None
    # Identifiers extracted by supervisor and passed directly to agent nodes
    part_number: str | None
    model_number: str | None


def supervisor_node(state: State):
    # Returning from an agent — agents have already added their responses, end this turn
    if state['messages'][-1].type != 'human':
        return {'message_intent': []}

    # Step 1: cheap scope check on latest message only
    scope_result = scope_llm.with_structured_output(ScopeCheck).invoke([
        {'role': 'system', 'content': SCOPE_SYSTEM_PROMPT},
        {'role': 'user', 'content': state['messages'][-1].content}
    ])

    if not scope_result.in_scope:
        response = llm.invoke([{'role': 'system', 'content': COOPER_OUT_OF_SCOPE_PROMPT}] + state['messages'])
        return {'message_intent': [], 'messages': [{'role': 'assistant', 'content': response.content}]}

    # Step 2: intent classification over full conversation history
    intent_result = llm.with_structured_output(IntentClassifier).invoke([
        {'role': 'system', 'content': 'Determine which agent(s) to call based on the conversation. Options: model_lookup, part_lookup, order_lookup, repairRAG. Return an empty list for greetings or general chat.'},
        *state['messages']
    ])

    if not intent_result.message_intent:
        response = llm.invoke([{'role': 'system', 'content': COOPER_CHAT_PROMPT}] + state['messages'])
        return {'message_intent': [], 'messages': [{'role': 'assistant', 'content': response.content}]}

    # Step 3: validate required identifiers before routing — only activate agents when we have what they need
    routable = []
    updates = {}
    missing = []

    if 'part_lookup' in intent_result.message_intent:
        extracted = llm.with_structured_output(PartNumberExtractor).invoke([
            {'role': 'system', 'content': 'Extract the most recent PS part number from the conversation (e.g. PS11752778). Return null if not present.'},
            *state['messages']
        ])
        if extracted.part_number:
            routable.append('part_lookup')
            updates['part_number'] = extracted.part_number
        else:
            missing.append('PS part number (e.g. PS11752778)')

    if 'model_lookup' in intent_result.message_intent:
        extracted = llm.with_structured_output(ModelNumberExtractor).invoke([
            {'role': 'system', 'content': 'Extract the appliance model number from the conversation (e.g. WDT780SAEM1). Return null if not present.'},
            *state['messages']
        ])
        if extracted.model_number:
            routable.append('model_lookup')
            updates['model_number'] = extracted.model_number
        else:
            missing.append('model number (you can find it on a sticker inside the appliance door)')

    # repairRAG and order_lookup pass through — their nodes handle any further missing info
    for intent in ['repairRAG', 'order_lookup']:
        if intent in intent_result.message_intent:
            routable.append(intent)

    if missing:
        # Ask for missing identifiers in Cooper's voice before routing any agents
        missing_str = ' and '.join(missing)
        response = llm.invoke([
            {'role': 'system', 'content': COOPER_CHAT_PROMPT},
            *state['messages'],
            {'role': 'system', 'content': f'Ask the user for their {missing_str} before you can proceed. Keep it brief and warm.'}
        ])
        return {'message_intent': [], 'messages': [{'role': 'assistant', 'content': response.content}]}

    return {'message_intent': routable, **updates}


def get_part_info(state: State):
    # part_number is guaranteed by supervisor — no need to re-extract or ask
    part_number = state['part_number']

    info = fetch_part_info(part_number)

    if not info:
        return {'messages': [{'role': 'assistant', 'content': f"I wasn't able to find part {part_number} on PartSelect. Double-check the number and try again."}]}

    part_context = f"Part number: {part_number}\nName: {info['name']}\nPrice: {info['price'] or 'not listed'}"
    response = llm.invoke([
        {'role': 'system', 'content': COOPER_PART_PROMPT},
        {'role': 'system', 'content': part_context},
        *state['messages']
    ])
    return {'messages': [{'role': 'assistant', 'content': response.content}]}

def get_model_info(state: State):
    # model_number is guaranteed by supervisor
    messages = [{'role': 'system', 'content': 'No matter what the query is, say MODEL LOOKUP.'}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}

def get_repair_info(state: State):
    messages = [{'role': 'system', 'content': 'No matter what the query is, say REPAIR RAG.'}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}

def get_order_info(state: State):
    messages = [{'role': 'system', 'content': 'No matter what the query is, say ORDER LOOKUP.'}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


graph_builder = StateGraph(State)

graph_builder.add_node('supervisor_node', supervisor_node)
graph_builder.add_node('get_part_info', get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info', get_repair_info)
graph_builder.add_node('get_order_info', get_order_info)

graph_builder.add_edge(START, 'supervisor_node')
# Empty intent: supervisor already responded (chat, out-of-scope, or asking for missing info) — END
# Non-empty list: fans out in parallel to all matched agent nodes
graph_builder.add_conditional_edges(
    'supervisor_node',
    lambda state: state['message_intent'] if state['message_intent'] else 'done',
    {'part_lookup': 'get_part_info', 'model_lookup': 'get_model_info', 'repairRAG': 'get_repair_info', 'order_lookup': 'get_order_info', 'done': END}
)

# All agents return to supervisor so it can decide whether more work is needed
graph_builder.add_edge('get_part_info', 'supervisor_node')
graph_builder.add_edge('get_model_info', 'supervisor_node')
graph_builder.add_edge('get_repair_info', 'supervisor_node')
graph_builder.add_edge('get_order_info', 'supervisor_node')

checkpointer = InMemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)

graph.get_graph().draw_mermaid_png(output_file_path='graph.png')

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("Enter your query: ")
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config)

    # Only print AI messages from this turn (everything after the last human message)
    last_human = max(i for i, m in enumerate(result['messages']) if m.type == 'human')
    for msg in result['messages'][last_human + 1:]:
        if msg.type == 'ai':
            print(msg.content)
