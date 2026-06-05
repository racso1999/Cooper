from .config import _fired, _text, rag_llm, vectorstore
from .state import State

# This node performs a RAG-based lookup to retrieve repair information relevant to the user's query.
def get_repair_info(state: State):
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
