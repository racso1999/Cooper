from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing import TypedDict, Literal, Annotated
import uuid

from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv()


llm = init_chat_model('gpt-5.4-mini')

# Separate tiny model for the cheap scope check — keeps cost down on every message
scope_llm = init_chat_model('gpt-4o-mini')

SCOPE_SYSTEM_PROMPT = """You are a scope checker for PartSelect, an e-commerce site for appliance parts.

## Rules
- Mark as IN SCOPE: any question about refrigerator or dishwasher parts, repairs, compatibility, or orders. Greetings and polite small talk are also IN SCOPE.
- Mark as OUT OF SCOPE: anything unrelated to refrigerator or dishwasher parts (e.g. washing machines, ovens, general chat, cooking advice, unrelated shopping).
- If unsure, lean towards IN SCOPE."""

OUT_OF_SCOPE_MESSAGE = (
    "I can only help with Dishwasher and Refrigerator parts and repairs! "
    "Got a question about finding a part, compatibility, or a repair? I'm happy to help."
)

class ScopeCheck(BaseModel):
    in_scope: bool = Field(description="True if the query relates to refrigerator or dishwasher parts/repairs on PartSelect. False otherwise.")

class IntentClassifier(BaseModel):
    # List allows multiple intents — LangGraph fans out to each corresponding node in parallel
    message_intent: list[Literal['model_lookup', 'part_lookup', 'order_lookup', 'repairRAG']] = Field(description="Classify the intent. This will determine which agent(s) to call. The options are: Lookup Model Name or Model (model_lookup), Lookup Part (part_lookup), Lookup Order (order_lookup), Find repair information (repairRAG). Return multiple intents if multiple agents need to be called. If you are unsure, just return the most likely intent.")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: list[str] | None
    in_scope: bool | None


def check_scope(state: State):
    structured_llm = scope_llm.with_structured_output(ScopeCheck)
    result = structured_llm.invoke([
        {'role': 'system', 'content': SCOPE_SYSTEM_PROMPT},
        {'role': 'user', 'content': state['messages'][-1].content}
    ])

    if not result.in_scope:
        return {'in_scope': False, 'messages': [{'role': 'assistant', 'content': OUT_OF_SCOPE_MESSAGE}]}

    return {'in_scope': True}


def classify_intent(state: State):
    structured_llm = llm.with_structured_output(IntentClassifier)
    result = structured_llm.invoke([
        {'role': 'system', 'content': 'Determine/Classify which agent/s to call based on the user query. The options are: model_lookup, part_lookup, order_lookup, repairRAG.'},
        {'role': 'user', 'content': state['messages'][-1].content}
    ])

    return {'message_intent': result.message_intent}

def get_part_info(state: State):
    messages = [{'role': 'system', 'content': 'No matter what the query is, say PART LOOKUP.'}] + state['messages']

    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}

def get_model_info(state: State):
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

graph_builder.add_node('check_scope', check_scope)
graph_builder.add_node('scope_gate', classify_intent)
graph_builder.add_node('get_part_info', get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info', get_repair_info)
graph_builder.add_node('get_order_info', get_order_info)

graph_builder.add_edge(START, 'check_scope')
# Out-of-scope queries short-circuit to END with a helpful message; in-scope continue to intent classification
graph_builder.add_conditional_edges('check_scope', lambda state: 'in_scope' if state['in_scope'] else 'out_of_scope', {'in_scope': 'scope_gate', 'out_of_scope': END})
# Returning a list from the routing function fans out to all matched nodes in parallel
graph_builder.add_conditional_edges('scope_gate', lambda state: state['message_intent'], {'part_lookup': 'get_part_info', 'model_lookup': 'get_model_info', 'repairRAG': 'get_repair_info', 'order_lookup': 'get_order_info'})

graph_builder.add_edge('get_part_info', END)
graph_builder.add_edge('get_model_info', END)
graph_builder.add_edge('get_repair_info', END)
graph_builder.add_edge('get_order_info', END)

checkpointer = InMemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("Enter your query: ")
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config) 

    # Print all agent responses (fan-out produces one message per agent)
    for msg in result['messages']:
        if msg.type == 'ai':
            print(msg.content)