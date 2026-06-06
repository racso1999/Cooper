from .part_func import fetch_part
from .context import _fired, log
from .state import State


def part_node(state: State):
    log.info('  [PART]   %s', state.get('part_number'))
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
