from .utils import _text
from .config import compiler_llm
from .prompts import COOPER_COMPILER_PROMPT
from .state import State

# This node compiles all retrieved information and the conversation history into a final response to the user.

def compiler_node(state: State):
    sections = []

    if state.get('part_info'):
        info = state['part_info']
        sections.append(info.get('error') or (
            f"Part lookup result:\n"
            f"  Part number: {info['part_number']}\n"
            f"  Name: {info['name']}\n"
            f"  Price: {info['price'] or 'not listed'}\n"
            f"  Image URL: {info['image_url'] or 'not available'}"
        ))

    if state.get('model_info'):
        info = state['model_info']
        if 'error' in info:
            sections.append(info['error'])
        else:
            symptom_lines = '\n'.join(
                f"    {sym}: {d['name']} ({d['part_number']}) — {d['fix_rate']}% fix rate"
                for sym, d in info['symptoms'].items()
            )
            sections.append(
                f"Model lookup result:\n"
                f"  Model: {info['model_number']}\n"
                f"  Brand: {info['brand']}\n"
                f"  Type:  {info['appliance_type']}\n"
                f"  Symptoms and top fix:\n{symptom_lines}"
            )

    if state.get('repair_info'):
        sections.append(f"Repair info:\n  {state['repair_info']}")

    if state.get('order_info'):
        sections.append(f"Order lookup result:\n{state['order_info']}")

    context       = '\n\n'.join(sections)
    full_response = ''
    for chunk in compiler_llm.stream([
        {'role': 'system', 'content': COOPER_COMPILER_PROMPT},
        {'role': 'system', 'content': f"Retrieved data:\n\n{context}"},
        *state['messages']
    ]):
        text = _text(chunk)
        if text:
            print(text, end='', flush=True)
            full_response += text
    print()

    return {
        'messages':    [{'role': 'assistant', 'content': full_response}],
        'part_info':   None,
        'model_info':  None,
        'repair_info': None,
        'order_info':  None,
    }
