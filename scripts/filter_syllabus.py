#!/usr/bin/env python3
"""
Tag questions as in_syllabus=True/False based on CBSE Class 12 Physics
2025-26/2026-27 rationalized syllabus.

Removed topics (official CBSE rationalization, applicable 2026-27):
  1. Communication Systems (entire topic removed from Semiconductor chapter)
  2. Van de Graaff Generator (Ch 2)
  3. Cyclotron (Ch 4)
  4. Davisson-Germer experiment (Ch 11)
  5. Carbon resistors & colour code (Ch 3)
  6. Potentiometer – applications (Ch 3)
  7. Moving coil galvanometer conversion details (Ch 4) – kept for theory
  8. Specific de Broglie explanation of Bohr's 2nd postulate (Ch 12)
"""
import json, re, os

# ── Removed-topic rules ───────────────────────────────────────────────────────
# Each rule: (chapter_name_or_None, [keywords], description)
# chapter=None means any chapter.

REMOVED_RULES = [
    # 1. Communication Systems – entire block removed from Semiconductors
    (
        'Semiconductor Electronics',
        [
            'communication system', 'amplitude modulation', 'frequency modulation',
            'sky wave', 'space wave', 'ground wave', 'carrier wave', 'carrier frequency',
            'bandwidth', 'modulation index', 'demodulation', 'transmitt', 'receiver',
            'antenna', 'transducer', 'signal-to-noise', 'repeater',
            'electronic communication', 'long distance communication',
            'internet', 'optical fibre communication', 'radar',
        ],
        'Communication Systems',
    ),

    # 2. Van de Graaff Generator (Ch 2)
    (
        'Electrostatic Potential and Capacitance',
        ['van de graaff', 'van-de-graaff', 'electrostatic generator'],
        'Van de Graaff Generator',
    ),

    # 3. Cyclotron (Ch 4)
    (
        'Moving Charges and Magnetism',
        ['cyclotron'],
        'Cyclotron',
    ),

    # 4. Davisson-Germer experiment (Ch 11)
    (
        'Dual Nature of Radiation and Matter',
        ['davisson', 'germer', 'davisson-germer', 'davisson and germer'],
        'Davisson-Germer Experiment',
    ),

    # 5. Carbon resistors & colour code (Ch 3)
    (
        'Current Electricity',
        ['carbon resistor', 'colour code', 'color code', 'carbon composition'],
        'Carbon Resistors & Colour Code',
    ),

    # 6. Potentiometer (Ch 3) – principle and ALL applications removed
    (
        'Current Electricity',
        ['potentiometer'],
        'Potentiometer',
    ),
]

# ── Helper ────────────────────────────────────────────────────────────────────

def is_out_of_syllabus(question: dict) -> tuple[bool, str]:
    """Return (True, reason) if the question is out of syllabus, else (False, '')."""
    text = question['question'].lower()
    chapter = question.get('chapter', '')

    for rule_chapter, keywords, label in REMOVED_RULES:
        if rule_chapter and chapter != rule_chapter:
            continue
        for kw in keywords:
            if kw in text:
                return True, label

    return False, ''


def main():
    data_path = 'src/data/pyq_data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    removed_count = 0
    reasons: dict[str, int] = {}

    for q in data['questions']:
        out, reason = is_out_of_syllabus(q)
        q['in_syllabus'] = not out
        if out:
            q['removed_reason'] = reason
            removed_count += 1
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            q.pop('removed_reason', None)

    total = len(data['questions'])
    in_syllabus = total - removed_count

    print(f'Total questions : {total}')
    print(f'In syllabus     : {in_syllabus}')
    print(f'Out of syllabus : {removed_count}')
    print()
    print('Breakdown by removed topic:')
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f'  {reason:<45} {count}')

    # Update chapter counts to reflect in-syllabus numbers
    for ch in data['chapters']:
        ch_qs = [q for q in data['questions'] if q['chapter'] == ch['name']]
        ch['count_total'] = ch['count']          # preserve original
        ch['count'] = sum(1 for q in ch_qs if q.get('in_syllabus', True))

    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\nSaved → {data_path}')


if __name__ == '__main__':
    main()
