import re as _re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

_BASE = Path(__file__).parent.parent

_raw           = (_BASE / 'data' / 'repair_info.txt').read_text()
KNOWLEDGE_BASE = [c.strip() for c in _re.split(r'\n(?=####)', _raw) if len(c.strip()) > 80] # split into chunks by #### section headers, which denote complete repair procedures
vectorstore    = InMemoryVectorStore(embedding=OpenAIEmbeddings(model='text-embedding-3-small'))
vectorstore.add_documents([Document(page_content=chunk) for chunk in KNOWLEDGE_BASE])
