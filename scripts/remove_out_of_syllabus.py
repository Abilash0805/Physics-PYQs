#!/usr/bin/env python3
"""Remove out-of-syllabus questions entirely from pyq_data.json."""
import json

DATA_PATH = 'src/data/pyq_data.json'

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

before = len(data['questions'])
data['questions'] = [q for q in data['questions'] if q.get('in_syllabus', True) is not False]
removed = before - len(data['questions'])

# Recompute the per-chapter summaries. The marks breakdown and the year
# list have to be rebuilt alongside the count: they are what the chapter
# page's marks tabs and year filter are drawn from, so leaving them at
# their pre-removal values overstates every tab.
for ch in data['chapters']:
    ch_qs = [q for q in data['questions'] if q['chapter'] == ch['name']]
    ch['count'] = len(ch_qs)
    dist = {}
    for q in ch_qs:
        key = str(q['marks'])
        dist[key] = dist.get(key, 0) + 1
    ch['marks_dist'] = dict(sorted(dist.items()))
    ch['years'] = sorted({q['year'] for q in ch_qs if q['year']})
    ch.pop('count_total', None)

data['total'] = len(data['questions'])
# the homepage reads this as its "with answers" figure, so it has to follow
# the questions that actually remain
data['matched_answers'] = sum(1 for q in data['questions'] if q.get('answer'))

with open(DATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Removed {removed} out-of-syllabus questions. Remaining: {len(data['questions'])}")
