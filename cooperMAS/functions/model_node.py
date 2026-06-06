from .model_func import fetch_model
from .context import _fired, log
from .state import State


def model_node(state: State):
    log.info('  [MODEL]  %s', state.get('model_number'))
    _fired.append('[MODEL]')
    info = fetch_model(state.get('model_number'))
    if not info:
        return {'model_info': {'error': f"I wasn't able to find model {state.get('model_number')} on PartSelect."}}
    symptom_parts: dict[str, list] = {}
    for part in info['compatible_parts']:
        for symptom, rate in part['fixes'].items():
            symptom_parts.setdefault(symptom, []).append(
                {'part_number': part['part_number'], 'name': part['name'], 'fix_rate': rate or 0}
            )
    for parts in symptom_parts.values():
        parts.sort(key=lambda p: p['fix_rate'], reverse=True)
    return {'model_info': {
        'model_number':   info['model_number'],
        'brand':          info['brand'],
        'appliance_type': info['appliance_type'],
        'symptoms': {
            symptom: {'part_number': p[0]['part_number'], 'name': p[0]['name'], 'fix_rate': p[0]['fix_rate']}
            for symptom, p in symptom_parts.items()
        },
    }}
