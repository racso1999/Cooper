from .config import cooper_llm
from .prompts import COOPER_SYSTEM_PROMPT
from .state import CooperOutput, State

_cooper = cooper_llm.with_structured_output(CooperOutput)

# This node is the entry point for the graph. It takes the conversation history as input,
# and uses the Cooper LLM to extract the user's intent and any relevant parameters (part number, model number, order ID/email).
# It returns these as updates to the state, which will be used by downstream nodes to route to specialist lookups or compile a response.
def cooper_node(state: State):
    prefix = []

    if state.get('summary'):
        prefix.append({'role': 'system', 'content': f"Summary of earlier conversation:\n{state['summary']}"})

    known = {k: v for k, v in {
        'part_number':  state.get('part_number'),
        'model_number': state.get('model_number'),
        'order_id':     state.get('order_id'),
        'order_email':  state.get('order_email'),
    }.items() if v}
    if known:
        prefix.append({'role': 'system', 'content': 'Known entities from this session: ' + ', '.join(f'{k}={v}' for k, v in known.items())})

    result = _cooper.invoke([
        {'role': 'system', 'content': COOPER_SYSTEM_PROMPT},
        *prefix,
        *state['messages']
    ])

    intent = list(result.intent)

    # Guard: strip intents whose required identifier wasn't extracted
    if 'part_lookup'  in intent and not result.part_number:  intent.remove('part_lookup')
    if 'model_lookup' in intent and not result.model_number: intent.remove('model_lookup')
    if 'order_lookup' in intent and not (result.order_id and result.order_email):
        intent.remove('order_lookup')

    updates: dict = {'intent': intent}
    if result.reply:        updates['messages']     = [{'role': 'assistant', 'content': result.reply}]
    if result.part_number:  updates['part_number']  = result.part_number
    if result.model_number: updates['model_number'] = result.model_number
    if result.order_id:     updates['order_id']     = result.order_id
    if result.order_email:  updates['order_email']  = result.order_email
    return updates
