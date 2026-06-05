from .config import cooper_llm, COOPER_SYSTEM_PROMPT
from .state import CooperOutput, State

_cooper = cooper_llm.with_structured_output(CooperOutput)


def cooper_node(state: State):
    result = _cooper.invoke([
        {'role': 'system', 'content': COOPER_SYSTEM_PROMPT},
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
