#!/usr/bin/env python3
"""
Pull the figures out of the chapter PDFs and attach them to their questions.

About a quarter of the bank asks about a diagram - a circuit, a ray path, a
graph - that the site never had, so those questions were unanswerable as
printed. The images are in the PDFs; the problem is knowing which question
each one belongs to, because the text layer and the images are separate.

The join is positional. The same parse `extract_v2` performs is repeated
here, but recording where each question's `Q<n>.` marker sits on the page,
so an image can be assigned to the last question that began above it. That
also fixes the ordering question for free: `extract_v2` walks sections in
document order and questions within them in document order, so the n-th
question it emits is the n-th marker found here.

Usage:
    scripts/extract_figures.py <pdf-dir> <data.json> <public-dir>
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_v2
from extract_v2 import META_RE, QSTART_RE, SECTION_RE
from pdfmath import MathBuilder

# Anything this small is a rule, a bullet or a logo rather than a diagram.
MIN_W, MIN_H = 40, 28
MIN_AREA = 2600


def page_lines(page) -> list[tuple[float, str]]:
    """Rendered lines of a page with the y they sit at."""
    toks, strokes = extract_v2.page_tokens(page)
    if not toks:
        return []
    out: list[tuple[float, str]] = []
    for grp in extract_v2.group_lines(MathBuilder(toks, strokes).result()):
        txt = extract_v2.render_line(grp)
        if not txt:
            continue
        if any(n in txt for n in extract_v2.NOISE) or extract_v2.NOISE_RE.match(txt):
            continue
        out.append((min(t.y0 for t in grp), txt))
    return out


def build_document(path):
    """Full text plus an index from character offset back to (page, y)."""
    doc = pymupdf.open(path)
    chunks: list[str] = []
    index: list[tuple[int, int, float]] = []   # (offset, page, y)
    offset = 0
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno])
        for y, txt in lines:
            index.append((offset, pno, y))
            chunks.append(txt)
            offset += len(txt) + 1            # +1 for the newline joiner
        chunks.append('')                      # page break keeps join faithful
        offset += 1
    return doc, '\n'.join(chunks), index


def locate(index, offset):
    """(page, y) of the line containing this character offset."""
    lo, hi = 0, len(index) - 1
    best = index[0] if index else (0, 0, 0.0)
    while lo <= hi:
        mid = (lo + hi) // 2
        if index[mid][0] <= offset:
            best = index[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best[1], best[2]


def question_positions(path):
    """(page, y) for every question, in the order extract_v2 emits them."""
    doc, full, index = build_document(path)
    heads = [(mm.start(), mm.end(), int(mm.group(1)), mm.group(4).strip())
             for mm in SECTION_RE.finditer(full)]
    positions: list[tuple[int, float]] = []
    for idx, (hs, he, marks, qtype) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(full)
        body = full[he:end]
        starts = list(QSTART_RE.finditer(body))
        for k, mm in enumerate(starts):
            stop = starts[k + 1].start() if k + 1 < len(starts) else len(body)
            chunk = body[mm.end():stop]
            meta = META_RE.search(chunk)
            if meta:
                chunk = chunk[:meta.start()] + chunk[meta.end():]
            # the same rejection extract_v2 applies, so the sequences line up
            if len(extract_v2.clean(chunk)) < 12:
                continue
            positions.append(locate(index, he + mm.start()))
    return doc, positions


def figures_on(doc):
    """Every sizeable image in the document as (page, rect, xref)."""
    out = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for info in page.get_images(full=True):
            xref = info[0]
            for rect in page.get_image_rects(xref):
                if (rect.width < MIN_W or rect.height < MIN_H
                        or rect.width * rect.height < MIN_AREA):
                    continue
                out.append((pno, rect, xref))
    return out


def main() -> None:
    src, data_path, public_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    out_dir = os.path.join(public_dir, 'figures')
    os.makedirs(out_dir, exist_ok=True)

    data = json.load(open(data_path, encoding='utf-8'))
    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for q in data['questions']:
        by_chapter[q['chapter']].append(q)

    pdfs = sorted(f for f in os.listdir(src)
                  if f.startswith('class-12-physics-') and f.endswith('.pdf'))

    attached = skipped = 0
    print(f'{"chapter":42}{"figures":>9}{"attached":>10}')
    print('-' * 61)
    for f in pdfs:
        path = os.path.join(src, f)
        chapter = extract_v2.chapter_from_filename(path)
        doc, positions = question_positions(path)
        questions = by_chapter.get(chapter, [])
        # out-of-syllabus removal means the dataset holds a subset; align on
        # the ids extract_v2 would have produced, which are 1-based per chapter
        by_num = {}
        for q in questions:
            m = re.search(r'-(\d+)$', q['id'])
            if m:
                by_num[int(m.group(1))] = q

        figs = figures_on(doc)
        per_q: dict[int, list] = defaultdict(list)
        for pno, rect, xref in figs:
            # the question this figure sits under: the last one starting at or
            # above it on the same page, else the last on an earlier page
            best = None
            for i, (qp, qy) in enumerate(positions):
                if (qp, qy) <= (pno, rect.y0):
                    best = i
                else:
                    break
            if best is None:
                skipped += 1
                continue
            per_q[best + 1].append((pno, rect, xref))

        n_att = 0
        for qnum, items in per_q.items():
            q = by_num.get(qnum)
            if q is None:            # removed as out of syllabus
                continue
            paths = []
            for j, (pno, rect, xref) in enumerate(items):
                name = f'{q["id"]}-{j + 1}.png'
                dest = os.path.join(out_dir, name)
                pix = doc[pno].get_pixmap(clip=rect, dpi=150)
                if not os.path.exists(dest):
                    pix.save(dest)
                # the intrinsic size travels with the figure so the card can
                # reserve its space and not jump as the image loads
                paths.append({'src': f'/figures/{name}',
                              'width': pix.width, 'height': pix.height})
            if paths:
                q['figures'] = paths
                n_att += 1
        attached += n_att
        print(f'{chapter[:42]:42}{len(figs):9}{n_att:10}')

    json.dump(data, open(data_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print('-' * 61)
    print(f'questions given figures : {attached}')
    print(f'figures with no question: {skipped}')
    print(f'saved                   → {out_dir}')


if __name__ == '__main__':
    main()
