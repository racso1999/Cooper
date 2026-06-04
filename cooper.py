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

class IntentClassifier(BaseModel):
    message_intent: Literal['model_lookup', 'part_lookup', 'order_lookup', 'repairRAG'] = Field(description="Classify the intent. This will determine which agent to call. The options are: Lookup Model Name or Model (model_lookup), Lookup Part (part_lookup), Lookup Order (order_lookup), Find repair information (repairRAG).")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: str | None


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

graph_builder = StateGraph(State)

graph_builder.add_node('classify_gate', classify_intent)
graph_builder.add_node('get_part_info', get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info', get_repair_info)

graph_builder.add_edge(START, 'classify_gate')
graph_builder.add_conditional_edges('classify_gate', lambda state: state['message_intent'], {'part_lookup': 'get_part_info', 'model_lookup': 'get_model_info', 'repairRAG': 'get_repair_info'})

graph_builder.add_edge('get_part_info', END)
graph_builder.add_edge('get_model_info', END)
graph_builder.add_edge('get_repair_info', END)

checkpointer = InMemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("Enter your query: ")
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config)

    print(result['messages'][-1].content)