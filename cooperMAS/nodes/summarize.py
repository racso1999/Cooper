from langchain_core.messages import RemoveMessage
from .config import compiler_llm
from .state import State

SUMMARIZE_AFTER = 10  # trigger when message count exceeds this
KEEP_RECENT     = 6   # always keep the most recent N messages verbatim

_PROMPT = """\
Summarize this customer support conversation concisely (under 150 words).
Include every specific identifier mentioned: part numbers, model numbers, order IDs, email addresses.
Capture what the customer asked and what information was provided."""

def maybe_summarize(state: State):
    messages = state['messages']
    if len(messages) <= SUMMARIZE_AFTER:
        return {}

    to_summarize = messages[:-KEEP_RECENT]

    prior = state.get('summary') or ''
    conversation = '\n'.join(f"{m.type.upper()}: {m.content}" for m in to_summarize)
    user_content  = (f"Existing summary:\n{prior}\n\nAdditional messages:\n{conversation}"
                     if prior else conversation)

    new_summary = compiler_llm.invoke([
        {'role': 'system', 'content': _PROMPT},
        {'role': 'user',   'content': user_content},
    ]).content

    return {
        'summary':  new_summary,
        'messages': [RemoveMessage(id=m.id) for m in to_summarize],
    }
