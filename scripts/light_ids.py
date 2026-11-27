"""Preserve the public light identifier when a source repeats a number in its volume."""
from collections import defaultdict
from hashlib import sha256


def assign_ids(records, previous):
    old_groups = defaultdict(list)
    for light in previous:
        volume = light['id'].split('-', 1)[0]
        old_groups[f'{volume}-{light["number"]}'].append(light)
    groups = defaultdict(list)
    for light in records:
        groups[light['id']].append(light)
    for base, group in groups.items():
        old = old_groups[base]
        by_name = {light['name']: light['id'] for light in old}
        for light in group:
            if light['name'] in by_name:
                light['id'] = by_name[light['name']]
            elif len(old) == len(group) == 1:
                # The volume/list number remains unambiguous after a name change.
                light['id'] = old[0]['id']
            elif len(group) > 1 or len(old) > 1:
                light['id'] = base + '-' + sha256(light['name'].encode()).hexdigest()[:8]
    if len({light['id'] for light in records}) != len(records):
        raise ValueError('Duplicate volume/light identifier; review before publishing')
