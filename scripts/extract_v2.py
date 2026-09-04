#!/usr/bin/env python3
"""
Section-aware extraction of CBSE Class 12 Physics PYQs.

The previous extractor read the PDFs as flat text: it caught only the
1-mark MCQ section and labelled every question "1 mark". These PDFs
actually carry explicit section headers

    3-Mark Questions
    (56 questions · Section C · SA)

followed by `Q<n>.` items each ending in `[<year> • Set <id>]`.
This reads those sections properly and rebuilds the maths geometrically
(see pdfmath.py) so fractions, radicals and subscripts survive.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfmath import (MathBuilder, Stroke, Tok, is_math_span, polish_math,
                     render_flat, to_latex_text)

# ── page furniture we never want in a question ───────────────────────────────

NOISE = (
    'Collegedunia',
    'Previous Year Questions • Free download',
    'Class 12 Physics Chapterwise PYQs',
    'All CBSE Board Papers',
    'Chapter-wise previous year questions, sorted by marks and year',
    'Table of Contents',
)
NOISE_RE = re.compile(r'^\s*(Page \d+|Chapter \d+:.*)\s*$')

SECTION_RE = re.compile(
    r'(\d)\s*-\s*Mark Questions\s*\n?\s*\((\d+)\s+questions?\s*[·•]\s*Section\s+(\w+)\s*[·•]\s*([^)]+)\)'
)
QSTART_RE = re.compile(r'(?m)^\s*Q(\d+)\.\s*')
# Year markers come either fully qualified or as a bare year:
#   [2026 • Set 55-1-1]      [2026]
META_RE = re.compile(
    r'\[\s*(\d{4})(?:\s*[-–]\s*\d{2,4})?(?:\s*[•·]\s*([^\]]*?))?\s*\]'
)


# ── page -> text with inline $math$ ──────────────────────────────────────────

def page_tokens(page) -> tuple[list[Tok], list[Stroke]]:
    toks: list[Tok] = []
    d = page.get_text('dict')
    for block in d['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for s in line['spans']:
                txt = s['text']
                if not txt.strip() and len(txt) == 0:
                    continue
                b = s['bbox']
                toks.append(Tok(b[0], b[1], b[2], b[3], s['size'], s['font'],
                                txt, is_math=is_math_span(s['font'], txt)))

    strokes: list[Stroke] = []
    for dr in page.get_drawings():
        if dr['type'] != 's':
            continue
        r = dr['rect']
        # horizontal hairline, short enough to be a bar rather than a divider
        if r.height <= 0.8 and 1.0 <= r.width <= 260:
            strokes.append(Stroke(r.x0, (r.y0 + r.y1) / 2, r.x1))
    return toks, strokes


def group_lines(toks: list[Tok]) -> list[list[Tok]]:
    """Group already-collapsed tokens into visual lines."""
    if not toks:
        return []
    # Full-size tokens define the baselines. Script-sized tokens (sub- and
    # superscripts) sit well off the baseline - notably the mass/atomic
    # numbers in nuclide notation - so they are snapped onto the nearest
    # real line instead of being allowed to form lines of their own.
    # Body size is the *modal* size, not the maximum: the first page carries
    # a large title, and measuring against that would demote the running
    # text to "script" and fold it into the heading.
    weight: dict[float, int] = defaultdict(int)
    for t in toks:
        weight[round(t.size, 1)] += max(len(t.text.strip()), 1)
    body = max(weight, key=lambda k: weight[k])

    big = [t for t in toks if t.size >= 0.86 * body]
    small = [t for t in toks if t.size < 0.86 * body]
    if not big:
        big, small = toks, []

    big.sort(key=lambda t: (t.baseline, t.x0))
    lines: list[list[Tok]] = []
    cur = [big[0]]
    ref = big[0].baseline
    for t in big[1:]:
        if abs(t.baseline - ref) <= 4.5:
            cur.append(t)
        else:
            lines.append(cur)
            cur = [t]
            ref = t.baseline
    lines.append(cur)

    refs = [sum(t.baseline for t in l) / len(l) for l in lines]
    for t in small:
        k = min(range(len(refs)), key=lambda i: abs(refs[i] - t.baseline))
        if abs(refs[k] - t.baseline) <= 9.0:
            lines[k].append(t)
        else:
            lines.append([t])
            refs.append(t.baseline)

    # A small token that formed its own line was appended at the end, which
    # would strand it out of reading order - the per-question year markers
    # are set in a smaller face and would drift to the foot of the page.
    order = sorted(range(len(lines)), key=lambda i: refs[i])
    return [sorted(lines[i], key=lambda t: t.x0) for i in order]


def render_line(toks: list[Tok]) -> str:
    """Emit a line, wrapping runs of maths in $...$."""
    toks = sorted(toks, key=lambda t: t.x0)
    out: list[str] = []
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        math = t.is_math or t.latex is not None
        if not math:
            out.append(t.text)
            i += 1
            continue
        run = []
        while i < n and (toks[i].is_math or toks[i].latex is not None):
            run.append(toks[i])
            i += 1
        body = polish_math(render_flat(run))
        if body:
            # keep a space against neighbouring prose
            lead = ' ' if out and not out[-1].endswith((' ', '(', '[', '$')) else ''
            out.append(f'{lead}${body}$')
    line = ''.join(out)
    return re.sub(r'[ \t]+', ' ', line).strip()


def page_text(page) -> str:
    toks, strokes = page_tokens(page)
    if not toks:
        return ''
    collapsed = MathBuilder(toks, strokes).result()
    lines = []
    for grp in group_lines(collapsed):
        txt = render_line(grp)
        if not txt:
            continue
        if any(nz in txt for nz in NOISE) or NOISE_RE.match(txt):
            continue
        lines.append(txt)
    return '\n'.join(lines)


# ── document -> questions ────────────────────────────────────────────────────

LOWER_WORDS = {'and', 'of', 'the', 'in', 'on', 'to', 'a', 'an'}


def chapter_from_filename(path: str) -> str:
    """Chapter title from the filename.

    The title printed on page 1 wraps mid-word ("Electrostatic Po-"), so the
    filename slug is the more reliable source.
    """
    base = os.path.basename(path)
    slug = re.sub(r'^class-12-physics-', '', base)
    slug = re.sub(r'-pyq-\d+\.pdf$', '', slug)
    words = slug.split('-')
    out = [w if i and w in LOWER_WORDS else w.capitalize()
           for i, w in enumerate(words)]
    return ' '.join(out)


def toc_expected(doc) -> int:
    """Question total advertised in the table of contents on page 1."""
    text = doc[0].get_text()
    # stop before the first section body header, which repeats a count
    cut = re.search(r'\d\s*-\s*Mark Questions\s*\n?\s*\(', text)
    if cut:
        text = text[:cut.start()]
    return sum(int(x) for x in re.findall(r'(\d+)\s+questions', text))


# A handful of source PDFs leak raw LaTeX into their text layer, so nuclide
# notation arrives as literal braces sliced across font runs:
#     _ $\{1\}^{2\}${$H\}     ->    $^{2}_{1}H$
NUCLIDE_RE = re.compile(r'_\s*\$\\\{(\d+)\\\}\^\{(\d+)\\?\}\$\{?\$?([A-Za-z]{1,3})\\?\}?')


def sanitize_math(t: str) -> str:
    """Guarantee every `$...$` run is brace-balanced.

    KaTeX throws on a stray brace and would blank out the whole question,
    so drop anything unmatched rather than trusting the source.
    """
    def fix_scripts(run: str) -> str:
        # Repeated carets, and script groups left adjacent once neighbouring
        # runs were merged, both make KaTeX throw. Neither is a real double
        # exponent - they are stacking artefacts of the original typesetting.
        run = re.sub(r'\^\s*\^', '^', run)
        run = re.sub(r'_\s*_', '_', run)
        for _ in range(6):
            new = re.sub(r'((?:\^|_)\{[^{}]*\})\s*(?=[\^_]\{)', r'\1{}', run)
            if new == run:
                break
            run = new
        # a script marker with nothing to attach to
        return re.sub(r'[\^_]\s*(?=[\s)\],.;]|$)', '', run)

    def fix(run: str) -> str:
        run = fix_scripts(run)
        out: list[str] = []
        depth = 0
        i = 0
        while i < len(run):
            ch = run[i]
            if ch == '\\' and i + 1 < len(run):
                nxt = run[i + 1]
                if nxt in '{}':          # escaped literal brace - keep as-is
                    out.append(run[i:i + 2])
                    i += 2
                    continue
                out.append(run[i:i + 2])
                i += 2
                continue
            if ch == '{':
                depth += 1
                out.append(ch)
            elif ch == '}':
                if depth == 0:
                    i += 1               # unmatched closer - drop it
                    continue
                depth -= 1
                out.append(ch)
            else:
                out.append(ch)
            i += 1
        body = ''.join(out) + '}' * depth
        return re.sub(r'\{\s*\}', '{}', body)

    return re.sub(r'\$([^$]*)\$', lambda m: '$' + fix(m.group(1)) + '$', t)


def space_math_boundaries(t: str) -> str:
    """Ensure a blank between maths and adjoining words.

    Done by walking `$` parity rather than by regex: an opening delimiter
    and a closing one need opposite treatment, and a pattern cannot tell
    them apart.
    """
    out: list[str] = []
    in_math = False
    for i, ch in enumerate(t):
        if ch == '$':
            prev = out[-1] if out else ''
            nxt = t[i + 1] if i + 1 < len(t) else ''
            if not in_math:
                if prev and (prev.isalnum() or prev in ')]'):
                    out.append(' ')
                out.append(ch)
            else:
                out.append(ch)
                if nxt and (nxt.isalnum() or nxt == '('):
                    out.append(' ')
            in_math = not in_math
        else:
            out.append(ch)
    return ''.join(out)


def clean(text: str) -> str:
    t = text
    t = re.sub(r'\$\s*\$', ' ', t)                    # empty math
    for _ in range(3):                                # merge adjacent runs
        t = re.sub(r'\$([^$]*)\$ ?\$([^$]*)\$', r'$\1 \2$', t)
    t = re.sub(r'-\n(?=[a-z])', '', t)                # de-hyphenate wraps
    t = re.sub(r'\s*\n\s*', ' ', t)
    t = NUCLIDE_RE.sub(r'$^{\2}_{\1}\3$', t)
    for _ in range(3):
        t = re.sub(r'\$([^$]*)\$ ?\$([^$]*)\$', r'$\1 \2$', t)
    t = sanitize_math(t)
    t = space_math_boundaries(t)
    t = re.sub(r'\s{2,}', ' ', t)
    t = re.sub(r'\s+([,.;:?])', r'\1', t)
    t = re.sub(r'\{\s+', '{', t)
    t = re.sub(r'\s+\}', '}', t)
    return t.strip()


def parse_document(path: str) -> tuple[str, list[dict]]:
    doc = pymupdf.open(path)
    pages = [page_text(doc[p]) for p in range(len(doc))]
    full = '\n'.join(pages)

    chapter = chapter_from_filename(path)

    # locate every "N-Mark Questions (…)" header
    heads = [(mm.start(), mm.end(), int(mm.group(1)), mm.group(4).strip())
             for mm in SECTION_RE.finditer(full)]
    if not heads:
        return chapter, []

    questions: list[dict] = []
    for idx, (hs, he, marks, qtype) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(full)
        body = full[he:end]

        starts = [mm for mm in QSTART_RE.finditer(body)]
        for k, mm in enumerate(starts):
            stop = starts[k + 1].start() if k + 1 < len(starts) else len(body)
            chunk = body[mm.end():stop]

            year, paper = 0, ''
            meta = META_RE.search(chunk)
            if meta:
                year = int(meta.group(1))
                paper = (meta.group(2) or '').strip()
                chunk = chunk[:meta.start()] + chunk[meta.end():]

            qtext = clean(chunk)
            if len(qtext) < 12:
                continue
            questions.append({
                'chapter': chapter,
                'marks': marks,
                'type': qtype,
                'year': year,
                'paper': paper,
                'question': qtext,
            })
    return chapter, questions


def slugify(name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/pyq_new/1PYQs'
    out = sys.argv[2] if len(sys.argv) > 2 else 'src/data/pyq_data.json'

    pdfs = sorted(f for f in os.listdir(src)
                  if f.startswith('class-12-physics-') and f.endswith('.pdf'))

    all_q: list[dict] = []
    print(f'{"chapter":45} {"got":>5} {"expected":>9}')
    print('-' * 63)
    for f in pdfs:
        chapter, qs = parse_document(os.path.join(src, f))
        expected = toc_expected(pymupdf.open(os.path.join(src, f)))
        flag = '' if len(qs) == expected else '  <-- MISMATCH'
        print(f'{chapter[:45]:45} {len(qs):5} {expected:9}{flag}')
        all_q.extend(qs)

    # stable ids
    per_chapter: dict[str, int] = defaultdict(int)
    for q in all_q:
        per_chapter[q['chapter']] += 1
        q['id'] = f"{slugify(q['chapter'])}-{per_chapter[q['chapter']]}"
        q['answer'] = None
        q['bookmarked'] = False
        q['solved'] = False
        q['in_syllabus'] = True

    chapters = []
    for name in sorted({q['chapter'] for q in all_q}):
        qs = [q for q in all_q if q['chapter'] == name]
        dist: dict[str, int] = defaultdict(int)
        for q in qs:
            dist[str(q['marks'])] += 1
        years = sorted({q['year'] for q in qs if q['year']})
        chapters.append({
            'name': name,
            'count': len(qs),
            'years': years,
            'marks_dist': dict(dist),
            'slug': slugify(name),
        })

    data = {
        'chapters': chapters,
        'questions': all_q,
        'total': len(all_q),
        'matched_answers': 0,
    }
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    dist: dict[int, int] = defaultdict(int)
    for q in all_q:
        dist[q['marks']] += 1
    print('-' * 63)
    print('total questions :', len(all_q))
    print('by marks        :', dict(sorted(dist.items())))
    print('saved           →', out)


if __name__ == '__main__':
    main()
