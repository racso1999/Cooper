"""
graph.py — Assembles and compiles the LangGraph agent graph.
Imports node functions from nodes.py; exported graph is used by cooper.py.
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from nodes import (
    State,
    cooper_node,
    get_part_info,
    get_model_info,
    get_repair_info,
    get_order_info,
    cooper_compiler,
)

graph_builder = StateGraph(State)

graph_builder.add_node('cooper_node',    cooper_node)
graph_builder.add_node('get_part_info',  get_part_info)
graph_builder.add_node('get_model_info', get_model_info)
graph_builder.add_node('get_repair_info',get_repair_info)
graph_builder.add_node('get_order_info', get_order_info)
graph_builder.add_node('cooper_compiler',cooper_compiler)

graph_builder.add_edge(START, 'cooper_node')

# Empty intent → Cooper replied directly (chat/out-of-scope) → END
# Non-empty list → fan out to all matched specialist nodes in parallel
graph_builder.add_conditional_edges(
    'cooper_node',
    lambda state: state['intent'] if state['intent'] else 'done',
    {
        'part_lookup':   'get_part_info',
        'model_lookup':  'get_model_info',
        'repair_lookup': 'get_repair_info',
        'order_lookup':  'get_order_info',
        'done':          END,
    }
)

# All specialist nodes feed into the compiler, which synthesises and ends the turn
graph_builder.add_edge('get_part_info',   'cooper_compiler')
graph_builder.add_edge('get_model_info',  'cooper_compiler')
graph_builder.add_edge('get_repair_info', 'cooper_compiler')
graph_builder.add_edge('get_order_info',  'cooper_compiler')
graph_builder.add_edge('cooper_compiler', END)

graph = graph_builder.compile(checkpointer=InMemorySaver())
