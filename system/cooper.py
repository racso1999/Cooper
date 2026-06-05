import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from graph import graph
from nodes import _fired

config = {'configurable': {'thread_id': uuid.uuid4()}}

while True:
    user_input = input("> ")
    _fired.clear()
    result = graph.invoke({'messages': [{'role': 'user', 'content': user_input}]}, config=config)

    # Agent path: compiler already streamed the response — nothing to print.
    # Chat path: cooper_node replied directly (no nodes fired) — print it now.
    if not _fired:
        last_human = max(i for i, m in enumerate(result['messages']) if m.type == 'human')
        for msg in result['messages'][last_human + 1:]:
            if msg.type == 'ai':
                print(msg.content)
