from pydantic import BaseModel, Field
from typing import TypedDict, Literal, Annotated

from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv()


llm = init_chat_model('open_ai: gpt-5.1-mini')

class AgentClassifier(BaseModel):
    agent_call: Literal['model_lookup', 'part_lookup', 'order_lookup', 'repairRAG'] = Field(description="Classify which agent to call based on the user's query. Options: 'model_lookup', 'part_lookup', 'order_lookup', 'repairRAG'")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    agent_call: str | None

