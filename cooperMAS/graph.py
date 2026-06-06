from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from functions import (
    State,
    cooper_node,
    part_node,
    model_node,
    repair_node,
    order_node,
    compiler_node,
    summarize_node,
)

graph_builder = StateGraph(State)

graph_builder.add_node('summarize_node', summarize_node)
graph_builder.add_node('cooper_node',    cooper_node)
graph_builder.add_node('part_node',      part_node)
graph_builder.add_node('model_node',     model_node)
graph_builder.add_node('repair_node',    repair_node)
graph_builder.add_node('order_node',     order_node)
graph_builder.add_node('compiler_node',  compiler_node)

graph_builder.add_edge(START,             'summarize_node')
graph_builder.add_edge('summarize_node',  'cooper_node')

# Empty intent - Cooper replied directly (chat/out-of-scope) - END
# Non-empty list - fan out to all matched specialist nodes in parallel
graph_builder.add_conditional_edges(
    'cooper_node',
    lambda state: state['intent'] if state['intent'] else 'done',
    {
        'part_lookup':   'part_node',
        'model_lookup':  'model_node',
        'repair_lookup': 'repair_node',
        'order_lookup':  'order_node',
        'done':          END,
    }
)

# All specialist nodes feed into the compiler, which synthesises and ends the turn
graph_builder.add_edge('part_node',     'compiler_node')
graph_builder.add_edge('model_node',    'compiler_node')
graph_builder.add_edge('repair_node',   'compiler_node')
graph_builder.add_edge('order_node',    'compiler_node')
graph_builder.add_edge('compiler_node', END)

graph = graph_builder.compile(checkpointer=InMemorySaver())
