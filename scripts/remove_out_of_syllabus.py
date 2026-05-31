#!/usr/bin/env python3
"""Remove out-of-syllabus questions entirely from pyq_data.json."""
import json

DATA_PATH = 'src/data/pyq_data.json'

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

before = len(data['questions'])
data['questions'] = [q for q in data['questions'] if q.get('in_syllabus', True) is not False]
removed = before - len(data['questions'])

# Recompute chapter counts
for ch in data['chapters']:
    ch_qs = [q for q in data['questions'] if q['chapter'] == ch['name']]
    ch['count'] = len(ch_qs)
    ch.pop('count_total', None)

data['total'] = len(data['questions'])

with open(DATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Removed {removed} out-of-syllabus questions. Remaining: {len(data['questions'])}")
