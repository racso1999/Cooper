import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from part_lookup import get_part_info as fetch_part_info
from .config import _fired
from .state import State


def get_part_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[PART]')
    info = fetch_part_info(state.get('part_number'))
    if not info:
        return {'part_info': {'error': f"I wasn't able to find part {state.get('part_number')} on PartSelect."}}
    return {'part_info': {
        'part_number': state.get('part_number'),
        'name':        info['name'],
        'price':       info['price'],
        'image_url':   info['image_url'],
    }}
