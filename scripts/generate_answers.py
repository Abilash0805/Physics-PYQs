#!/usr/bin/env python3
"""
Write exam-ready answers for the question bank, using the claude CLI.

Answers are generated from each question's own text and cached by question
id, so a run can be interrupted and resumed without losing work or paying
for the same answer twice.

Two details are load-bearing:

*  Answers come back in a delimited block format, not JSON. Every answer is
   dense with LaTeX, and asking for JSON means asking the model to escape
   every backslash correctly in a 2,000-question run - `\\frac` is a broken
   JSON string, and one bad escape loses the whole batch.

*  Each answer is parsed by KaTeX before it is accepted. A malformed maths
   run blanks the answer in the UI, so a batch that fails validation is
   retried rather than stored.

Usage:
    scripts/generate_answers.py [--limit N] [--workers N] [--missing-only]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

DATA_PATH = 'src/data/pyq_data.json'
CACHE_PATH = 'scripts/.answers_cache.jsonl'

BEGIN = re.compile(r'^<<<ID:(\S+)>>>\s*$')
END = '<<<END>>>'

STYLE = """\
You are a CBSE Class 12 Physics examiner writing model answers for the \
2026-27 board syllabus. Write the answer a student should give to earn full \
marks.

Length and shape follow the mark value:
  1 mark  - a multiple-choice question: begin exactly "Option (X) is correct." \
then one sentence giving the reason or formula. A fill-in-the-blank or \
one-word question: give the answer, then at most one short sentence.
  2 marks - 2 to 4 sentences, or two labelled points. Include the governing \
formula.
  3 marks - state the formula, substitute, and give the result with units; or \
three labelled points. Roughly 60-110 words.
  4 marks - a case study: answer each sub-part on its own line, labelled \
(i), (ii), ... as the question labels them.
  5 marks - cover each part the question asks for, labelled (a), (b), ... \
Give the key steps of any derivation, not just the final line. 120-180 words.

Rules:
- Answer the question actually asked. If it has parts, answer every part.
- Put every symbol, formula and number in LaTeX between single dollar signs: \
$v_d = eE\\tau/m$, $1.6 \\times 10^{-19}$ C. Never use display math, \
\\begin{...} environments, or double dollars.
- Use only LaTeX that KaTeX supports. Keep it simple.
- When a question depends on a figure that is not provided, answer the \
physics it is testing in general terms; do not say the figure is missing.
- Write the answer only. No preamble, no restating the question, no headings.
- Where the answer has steps or parts, start each on a new line so it renders \
as separate steps.
"""


def make_prompt(batch: list[dict]) -> str:
    lines = [STYLE, '', f'Write an answer for each of the {len(batch)} '
             'questions below.', '',
             'Return them in exactly this format, and nothing else:', '',
             '<<<ID:the-question-id>>>', 'the answer text', END, '',
             'Repeat that block for every question, in the order given.', '']
    for q in batch:
        lines.append(f'<<<ID:{q["id"]}>>>')
        lines.append(f'Chapter: {q["chapter"]}')
        lines.append(f'Marks: {q["marks"]} ({q["type"]})')
        lines.append(f'Question: {q["question"]}')
        lines.append(END)
        lines.append('')
    return '\n'.join(lines)


def parse_blocks(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    cur: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = BEGIN.match(line.strip())
        if m:
            cur, buf = m.group(1), []
            continue
        if line.strip() == END:
            if cur:
                body = '\n'.join(buf).strip()
                if body:
                    out[cur] = body
            cur, buf = None, []
            continue
        if cur is not None:
            buf.append(line)
    return out


def katex_ok(answers: list[str]) -> set[int]:
    """Indices whose maths KaTeX parses. Runs one node process per batch."""
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'katex_check.js')
    proc = subprocess.run(['node', checker], input=json.dumps(answers),
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f'katex check failed: {proc.stderr[:200]}')
    return set(json.loads(proc.stdout)['ok'])


def call_claude(prompt: str, timeout: int) -> str:
    """One answer batch.

    Writing answers needs no tools and no MCP servers, but the CLI would
    otherwise start every configured MCP server and load the repository's
    CLAUDE.md on each of the several hundred calls a full run makes. The
    flags below drop that startup work, and running from a neutral
    directory keeps the project instructions out of the prompt - they are
    about editing this codebase, not about physics.
    """
    proc = subprocess.run(
        ['claude', '-p', prompt, '--output-format', 'text',
         '--strict-mcp-config', '--tools', ''],
        capture_output=True, text=True, timeout=timeout,
        cwd=tempfile.gettempdir())
    if proc.returncode != 0:
        raise RuntimeError(f'claude exited {proc.returncode}: '
                           f'{proc.stderr[:200]}')
    return proc.stdout


class Cache:
    """Append-only answer cache, so an interrupted run resumes where it was."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.data: dict[str, str] = {}
        if os.path.exists(path):
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self.data[rec['id']] = rec['answer']

    def add(self, items: dict[str, str]) -> None:
        with self.lock:
            with open(self.path, 'a', encoding='utf-8') as fh:
                for qid, ans in items.items():
                    if qid in self.data:
                        continue
                    self.data[qid] = ans
                    fh.write(json.dumps({'id': qid, 'answer': ans},
                                        ensure_ascii=False) + '\n')


class Breaker:
    """Stops the run when the CLI starts refusing every call.

    Hitting a usage limit makes `claude -p` exit non-zero with an empty
    stderr, which is indistinguishable from any other failure. Without a
    breaker each remaining batch still burns its full retry budget, so a
    limit reached early chews through the whole queue in minutes and the
    run ends with nothing but failures. Tripping instead leaves the cache
    intact to resume from once the limit resets.
    """

    LIMIT = 10

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.consecutive = 0
        self.tripped = False

    def record(self, ok: bool) -> None:
        with self.lock:
            if ok:
                self.consecutive = 0
                return
            self.consecutive += 1
            if self.consecutive >= self.LIMIT and not self.tripped:
                self.tripped = True
                print(f'\n  stopping: {self.LIMIT} batches failed in a row - '
                      'the CLI is refusing calls (usage limit reached?).\n'
                      '  Cached answers are kept; rerun to resume.\n',
                      flush=True)


def run_batch(batch: list[dict], cache: Cache, breaker: Breaker,
              attempts: int = 3) -> int:
    """Answer one batch, keeping only what round-trips and parses."""
    if breaker.tripped:
        return 0
    wanted = {q['id'] for q in batch}
    for attempt in range(attempts):
        if breaker.tripped:
            return 0
        try:
            raw = call_claude(make_prompt(batch), timeout=240 + 60 * attempt)
            got = {k: v for k, v in parse_blocks(raw).items() if k in wanted}
            if not got:
                continue
            ids = list(got)
            ok = katex_ok([got[i] for i in ids])
            good = {ids[i]: got[ids[i]] for i in range(len(ids)) if i in ok}
            if good:
                cache.add(good)
                breaker.record(True)
                return len(good)
        except Exception as exc:                      # noqa: BLE001
            if attempt == attempts - 1:
                print(f'  batch {batch[0]["id"]} failed: {exc}', flush=True)
            else:
                time.sleep(5 * (attempt + 1) ** 2)
    breaker.record(False)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0,
                    help='only process this many questions (for a trial run)')
    ap.add_argument('--batch', type=int, default=6)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--missing-only', action='store_true',
                    help='keep existing answers instead of rewriting them')
    ap.add_argument('--apply', action='store_true',
                    help='write the cached answers into the dataset and stop')
    args = ap.parse_args()

    with open(DATA_PATH, encoding='utf-8') as fh:
        data = json.load(fh)
    cache = Cache(CACHE_PATH)

    if args.apply:
        applied = 0
        for q in data['questions']:
            ans = cache.data.get(q['id'])
            if ans:
                q['answer'] = ans
                applied += 1
        data['matched_answers'] = sum(1 for q in data['questions']
                                      if q.get('answer'))
        with open(DATA_PATH, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f'applied {applied} answers -> {DATA_PATH}')
        return

    todo = [q for q in data['questions'] if q['id'] not in cache.data]
    if args.missing_only:
        todo = [q for q in todo if not q.get('answer')]
    if args.limit:
        todo = todo[:args.limit]

    print(f'cached {len(cache.data)} | to answer {len(todo)}')
    if not todo:
        return

    batches = [todo[i:i + args.batch] for i in range(0, len(todo), args.batch)]
    done = 0
    lock = threading.Lock()

    breaker = Breaker()

    def work(batch: list[dict]) -> None:
        nonlocal done
        n = run_batch(batch, cache, breaker)
        with lock:
            done += n
            if n:
                print(f'  {done}/{len(todo)} answered', flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, batches))

    print(f'\ncached total: {len(cache.data)}')
    print(f'run scripts/generate_answers.py --apply to write them in')


if __name__ == '__main__':
    main()
