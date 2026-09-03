#!/usr/bin/env python3
"""
Check the generated answers before they go out.

Three thousand answers cannot be read by hand, and the failure modes that
matter are ones a glance would miss: an option letter that is not among the
options offered, a batch delimiter left in the text, an answer to a
five-mark question that is one line long. Each check below is something
that would be visible to a student on the site.

Usage:
    scripts/audit_answers.py [--verbose]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import os
from collections import Counter

DATA_PATH = 'src/data/pyq_data.json'

OPTION_IN_Q = re.compile(r'\(([A-Da-d])\)')
# answers usually restate the option before "is correct", so allow text
# between the two - matching how AnswerRenderer detects the option
OPTION_IN_A = re.compile(r'^\s*Option\s*\(([A-Da-d])\)\s*(.*?)\s*is\s+correct', re.I)
LEAKED = ('<<<ID:', '<<<END>>>', 'Chapter:', 'Marks:')
HEDGES = (
    'figure is not provided', 'figure is missing', 'no figure',
    'without the figure', 'cannot see', 'not shown here', 'as an ai',
    'i cannot', "i'm unable", 'unable to determine from',
)

# a five-mark answer that fits in a tweet is not a five-mark answer
MIN_CHARS = {1: 20, 2: 80, 3: 140, 4: 140, 5: 220}


def mcq_options(question: str) -> set[str]:
    """The option letters a question offers, empty if it is not an MCQ.

    `(a)`, `(b)`, `(c)` also label the parts of a structured question, so
    the markers alone would make "Can a transformer step up dc power? (a)
    ... (b) ... (c) ..." look like a multiple-choice question and its
    perfectly good part-by-part answer look like a miss. Real options run
    in order from (a) or (A) and are printed together at the end.
    """
    found = [(m.start(), m.group(1).lower())
             for m in re.finditer(r'\(([A-Da-d])\)', question)]
    if len(found) < 3:
        return set()
    letters = [f[1] for f in found]
    if letters != [chr(ord('a') + i) for i in range(len(letters))]:
        return set()
    if found[-1][0] - found[0][0] > 400:
        return set()
    return {c.upper() for c in letters}


def katex_failures(answers: list[str]) -> list[int]:
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'katex_check.js')
    proc = subprocess.run(['node', checker], input=json.dumps(answers),
                          capture_output=True, text=True, timeout=300)
    proc.check_returncode()
    ok = set(json.loads(proc.stdout)['ok'])
    return [i for i in range(len(answers)) if i not in ok]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    data = json.load(open(DATA_PATH, encoding='utf-8'))
    qs = data['questions']
    problems: dict[str, list[tuple[str, str]]] = {}

    def flag(kind: str, q: dict, detail: str = '') -> None:
        problems.setdefault(kind, []).append((q['id'], detail))

    answered = [q for q in qs if q.get('answer')]
    for q in qs:
        ans = (q.get('answer') or '').strip()
        if not ans:
            flag('missing', q)
            continue

        if any(tok in ans for tok in LEAKED):
            flag('leaked prompt scaffolding', q, ans[:60])

        low = ans.lower()
        for h in HEDGES:
            if h in low:
                flag('hedging / refusal text', q, h)
                break

        # A fill-in-the-blank is answered by the missing word, so "rectify"
        # is a complete one-mark answer and not a truncated one.
        blank = '___' in q['question']
        if not blank and len(ans) < MIN_CHARS.get(q['marks'], 20):
            flag(f'too short for {q["marks"]} marks', q, f'{len(ans)} chars')

        # An MCQ's answer must name one of the options the question offers.
        opts = mcq_options(q['question'])
        is_mcq = len(opts) >= 3
        m = OPTION_IN_A.match(ans)
        if is_mcq and not m:
            flag('MCQ without an option named', q, ans[:60])
        if m and opts and m.group(1).upper() not in opts:
            flag('option not among those offered', q,
                 f'answered ({m.group(1).upper()}), offered {sorted(opts)}')

    if answered:
        texts = [q['answer'] for q in answered]
        for i in katex_failures(texts):
            flag('KaTeX parse failure', answered[i], texts[i][:60])

    total = len(qs)
    print(f'questions        : {total}')
    print(f'with answers     : {len(answered)}')
    print(f'missing answers  : {total - len(answered)}')
    print()
    if not problems:
        print('no problems found')
        return
    print('problems:')
    for kind, items in sorted(problems.items(), key=lambda kv: -len(kv[1])):
        print(f'  {kind:32} {len(items)}')
        if args.verbose:
            for qid, detail in items[:8]:
                print(f'      {qid}: {detail}')


if __name__ == '__main__':
    main()
