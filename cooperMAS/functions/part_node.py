from .part_func import fetch_part
from .context import _fired
from .state import State


def part_node(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[PART]')
    info = fetch_part(state.get('part_number'))
    if not info:
        return {'part_info': {'error': f"I wasn't able to find part {state.get('part_number')} on PartSelect."}}
    return {'part_info': {
        'part_number': state.get('part_number'),
        'name':        info['name'],
        'price':       info['price'],
        'image_url':   info['image_url'],
    }}
