from .config import _fired, _text, rag_llm, vectorstore
from .state import State

# This node performs a RAG-based lookup to retrieve repair information relevant to the user's query.
def get_repair_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[RAG]')
    query     = state['messages'][-1].content
    documents = vectorstore.similarity_search(query, k=3)
    context   = '\n'.join(f'- {doc.page_content}' for doc in documents)
    messages  = [
        {'role': 'system', 'content': (
            f"You are a RAG agent. Answer the user using only the context below. "
            f"If the answer is not in it, say you don't know.\n\nContext:\n{context}"
        )},
    ] + state['messages']
    return {'repair_info': _text(rag_llm.invoke(messages))}
