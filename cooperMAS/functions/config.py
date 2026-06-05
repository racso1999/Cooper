#Configuration Settings for Cooper MAS

from langchain.chat_models import init_chat_model

cooper_llm   = init_chat_model('gpt-5.4-2026-03-05')
compiler_llm = init_chat_model('gpt-5.4-2026-03-05')
rag_llm      = init_chat_model('gpt-5.4-2026-03-05')
