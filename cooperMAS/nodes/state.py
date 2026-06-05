"""Graph state and structured output schema."""

from typing import TypedDict, Literal, Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Output schema for the CooperOutput node, which is the final node in the graph that produces a response to the user.
class CooperOutput(BaseModel):
    reply: str | None = Field(
        description="Cooper's response. Null when routing to specialist nodes.")
    intent: list[Literal['part_lookup', 'model_lookup', 'repair_lookup', 'order_lookup']] = Field(
        description="Nodes to call. Empty list for chat/greetings/out-of-scope.")
    part_number: str | None = Field(default=None,
        description="PS part number (e.g. PS11752778). Required when part_lookup is in intent.")
    model_number: str | None = Field(default=None,
        description="Appliance model number (e.g. WDT780SAEM1). Normalise to uppercase. Required when model_lookup is in intent.")
    order_id: str | None = Field(default=None,
        description="Order ID (e.g. ORD-10042). Required when order_lookup is in intent.")
    order_email: str | None = Field(default=None,
        description="Customer email. Required when order_lookup is in intent.")

# This TypedDict defines the state that is passed between nodes in the graph. It includes the conversation history (messages), the extracted intent and parameters, and any retrieved information from specialist nodes.
class State(TypedDict):
    messages:     Annotated[list, add_messages]
    intent:       list[str] | None
    part_number:  str | None
    model_number: str | None
    order_id:     str | None
    order_email:  str | None
    part_info:    dict | None  # set by get_part_info,  consumed by cooper_compiler
    model_info:   dict | None  # set by get_model_info, consumed by cooper_compiler
    repair_info:  str | None   # set by get_repair_info, consumed by cooper_compiler
    order_info:   str | None   # set by get_order_info, consumed by cooper_compiler
