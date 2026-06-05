from .context import _fired
from .utils import _text
from .config import rag_llm
from .vectorstore import vectorstore
from .state import State


def repair_node(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[RAG]')
    query     = state['messages'][-1].content
    documents = vectorstore.similarity_search(query, k=5)
    context   = '\n\n---\n\n'.join(doc.page_content for doc in documents)
    messages  = [
        {'role': 'system', 'content': (
            f"You are a repair guidance agent for PartSelect appliances. "
            f"Using the repair knowledge below, help the user with their issue. "
            f"If the context does not directly cover their symptom, identify the most closely related guidance and explain what it covers — do not simply say you don't know. "
            f"Never invent repair steps that are not present in the context.\n\nRepair knowledge:\n{context}"
        )},
    ] + state['messages']
    return {'repair_info': _text(rag_llm.invoke(messages))}
