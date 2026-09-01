#!/usr/bin/env python3
"""
Carry answers from the old dataset onto the re-extracted questions.

Only answers that can still be trusted are moved across. The previous
extraction flattened all 2D maths, so two different options could come out
as identical strings - any answer produced from such a question may name
the wrong option. Those are dropped rather than propagated, and so is the
"refer to the official paper" filler.
"""
from __future__ import annotations

import json
import re
import sys

FALLBACK = 'Refer to the official CBSE'
MATHY = re.compile(r'[√πωΩμ°]|\$|\\frac|\\sqrt')


def norm(s: str) -> str:
    s = re.sub(r'\$[^$]*\$', ' ', s)      # maths was unreliable before
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return ' '.join(s.split())


def main() -> None:
    old_path, new_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    old = json.load(open(old_path, encoding='utf-8'))
    new = json.load(open(new_path, encoding='utf-8'))

    trusted: dict[str, str] = {}
    dropped_fallback = dropped_mathy = 0
    for q in old['questions']:
        ans = q.get('answer')
        if not ans:
            continue
        if ans.startswith(FALLBACK):
            dropped_fallback += 1
            continue
        # the old question text drove the answer; if it contained maths the
        # answer was written against a corrupted reading of the options
        if MATHY.search(q['question']):
            dropped_mathy += 1
            continue
        trusted.setdefault(norm(q['question'])[:90], ans)

    carried = 0
    for q in new['questions']:
        key = norm(q['question'])[:90]
        if key in trusted:
            q['answer'] = trusted[key]
            carried += 1

    new['matched_answers'] = carried
    json.dump(new, open(out_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    print(f'old answers                : {sum(1 for q in old["questions"] if q.get("answer"))}')
    print(f'  dropped (filler text)    : {dropped_fallback}')
    print(f'  dropped (mangled maths)  : {dropped_mathy}')
    print(f'  trusted and reusable     : {len(trusted)}')
    print(f'carried onto new questions : {carried} / {len(new["questions"])}')
    print(f'still needing an answer    : {len(new["questions"]) - carried}')


if __name__ == '__main__':
    main()
