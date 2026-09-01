#!/usr/bin/env python3
"""
Token layer for the Oswaal-style full board papers.

`pdfmath` reconstructs maths from LaTeX-generated PDFs, where Computer
Modern names the maths and every fraction bar and radical overline is a
stroke. The Oswaal solved papers are typeset in a DTP program instead, so
two of those assumptions break:

  * fonts carry no "this is maths" signal in their name - the body face is
    ZapfCalligraphic and maths arrives as Times/Symbol/MT runs
  * a radical is not a glyph at all. It is a *filled vector path* tracing
    the tick and the overline, so `pdfmath` never sees the `√` it looks
    for and `1/√2` collapses to the same `\\frac{1}{2}` as `1/2`

This module supplies the missing signals - classifying spans by font and
synthesising a `√` token plus its overline stroke out of the path - and
then hands the result to the ordinary `MathBuilder`, so both PDF families
share one reconstruction engine.
"""
from __future__ import annotations

import pymupdf

from pdfmath import Stroke, Tok

# Faces used for running prose. Everything else in these papers is maths:
# variables set in Times, Greek in Symbol, operators in MT-Extra.
PROSE_FONTS = (
    'ZAPFCALLIGRAPHIC801BT-RO',
    'ZAPFCALLIGRAPHIC801BT-BO',
    'AVENIRLTSTD',
    'PALATINO',
    'CALIBRI',
    'ARIAL',
    'HELVETICA',
)


def is_math_font(font: str) -> bool:
    f = font.upper()
    return not any(f.startswith(p) for p in PROSE_FONTS)



# Adobe Symbol encoding. PyMuPDF decodes some Symbol runs to Unicode already
# but leaves others as the raw Latin byte, so `Ω` arrives as a bare "W" and
# "10 W" reads as watts rather than ohms. Mapping is applied only to
# characters that are still ASCII, so an already-decoded run is left alone.
SYMBOL_ENC = {
    'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ', 'h': 'η',
    'q': 'θ', 'i': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ',
    'o': 'ο', 'p': 'π', 'r': 'ρ', 's': 'σ', 't': 'τ', 'u': 'υ', 'f': 'φ',
    'c': 'χ', 'y': 'ψ', 'w': 'ω', 'v': 'ϖ', 'j': 'φ', 'V': 'ς', 'J': 'ϑ',
    'A': 'Α', 'B': 'Β', 'G': 'Γ', 'D': 'Δ', 'E': 'Ε', 'Z': 'Ζ', 'H': 'Η',
    'Q': 'Θ', 'I': 'Ι', 'K': 'Κ', 'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 'X': 'Ξ',
    'O': 'Ο', 'P': 'Π', 'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ', 'F': 'Φ',
    'C': 'Χ', 'Y': 'Ψ', 'W': 'Ω',
    '\xb0': '°', '\xb1': '±', '\xb4': '×', '\xb8': '÷', '\xb9': '≠',
    '\xa3': '≤', '\xb3': '≥', '\xbb': '≈', '\xae': '→', '\xa5': '∞',
    '\xb6': '∂', '\xd6': '√', '\xf2': '∫', '\xe5': '∑', '\xd5': '∏',
    '\xce': '∈', '\xd0': '∠', '\xd7': '⋅', '\xd1': '∇',
}


def decode_symbol(text: str) -> str:
    """Translate a Symbol-font run into the glyphs it actually renders."""
    return ''.join(SYMBOL_ENC.get(ch, ch) if ord(ch) < 256 else ch
                   for ch in text)


def _horizontal_items(drawing) -> list[tuple[float, float, float]]:
    """Horizontal line segments of a drawing as (x0, x1, y)."""
    out = []
    for it in drawing['items']:
        if it[0] != 'l':
            continue
        a, b = it[1], it[2]
        if abs(a.y - b.y) <= 0.35:
            out.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
    return out


def radical_from_path(drawing) -> tuple[Tok, Stroke] | None:
    """Recover a `√` and its overline from a filled path, if it is one.

    The glyph is drawn as a closed polygon: a short tick that dives down
    and back up, then a long horizontal top edge running right over the
    radicand. That top edge is the overline `MathBuilder` pairs with the
    radical, so it is handed back as a stroke starting exactly at the
    radical's right edge - the adjacency `_radical_for` tests for.
    """
    r = drawing['rect']
    if drawing['type'] != 'f' or len(drawing['items']) < 4:
        return None
    if not (3.0 <= r.width <= 300 and 3.0 <= r.height <= 40):
        return None

    horiz = _horizontal_items(drawing)
    if not horiz:
        return None
    top = min(h[2] for h in horiz)
    # the overline is the widest segment sitting on that top edge
    cands = [h for h in horiz if abs(h[2] - top) <= 0.6]
    x0, x1, y = max(cands, key=lambda h: h[1] - h[0])
    if x1 - x0 < 1.5:
        return None
    # the tick has to actually descend below the overline, or this is just
    # a rule that happened to be filled rather than stroked
    if r.y1 - y < 2.5:
        return None

    rad = Tok(r.x0, r.y0, x0, r.y1, max(r.height * 0.7, 6.0), 'Radical', '√',
              is_math=True)
    return rad, Stroke(x0, y, x1)


def page_tokens(page) -> tuple[list[Tok], list[Stroke]]:
    toks: list[Tok] = []
    for block in page.get_text('dict')['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for s in line['spans']:
                txt = s['text']
                if not txt.strip():
                    continue
                if 'SYMBOL' in s['font'].upper():
                    txt = decode_symbol(txt)
                b = s['bbox']
                toks.append(Tok(b[0], b[1], b[2], b[3], s['size'], s['font'],
                                txt, is_math=is_math_font(s['font'])))

    strokes: list[Stroke] = []
    for dr in page.get_drawings():
        r = dr['rect']
        if dr['type'] == 'f':
            found = radical_from_path(dr)
            if found:
                rad, over = found
                toks.append(rad)
                strokes.append(over)
            continue
        if r.height <= 1.2 and 1.0 <= r.width <= 260:
            strokes.append(Stroke(r.x0, (r.y0 + r.y1) / 2, r.x1))
    return toks, strokes


def columns(toks: list[Tok], strokes: list[Stroke]) -> list[tuple[list[Tok], list[Stroke]]]:
    """Split a page into its text columns.

    The board papers are set two-up. Grouping tokens into lines by baseline
    alone would weld a line of the left column onto whatever sits beside it
    in the right, interleaving two unrelated questions.

    The gutter is found as the quietest vertical band rather than an empty
    one: running heads and footers stretch clean across the page, so on
    most spreads no column of pixels is actually untouched, and demanding
    an empty run silently falls back to single-column - which is exactly
    the case that produces interleaved nonsense.
    """
    body = [t for t in toks if t.x1 > t.x0]
    if len(body) < 40:
        return [(toks, strokes)]

    lo = min(t.x0 for t in body)
    hi = max(t.x1 for t in body)
    if hi - lo < 100:
        return [(toks, strokes)]

    cells = int(hi - lo) + 1
    used = [0] * cells
    for t in body:
        a = max(0, int(t.x0 - lo))
        b = min(cells - 1, int(t.x1 - lo))
        for i in range(a, b + 1):
            used[i] += 1

    ranked = sorted(used)
    median = ranked[len(ranked) // 2]
    if median <= 0:
        return [(toks, strokes)]
    quiet = max(1.0, 0.25 * median)

    best = None
    i = int(0.30 * cells)
    end = int(0.70 * cells)
    while i < end:
        if used[i] >= quiet:
            i += 1
            continue
        j = i
        while j < end and used[j] < quiet:
            j += 1
        if (j - i) >= 6 and (best is None or (j - i) > (best[1] - best[0])):
            best = (i, j)
        i = j

    if best is None:
        return [(toks, strokes)]

    cut = lo + (best[0] + best[1]) / 2
    left = ([t for t in toks if t.cx < cut],
            [s for s in strokes if (s.x0 + s.x1) / 2 < cut])
    right = ([t for t in toks if t.cx >= cut],
             [s for s in strokes if (s.x0 + s.x1) / 2 >= cut])
    if len(left[0]) < 15 or len(right[0]) < 15:
        return [(toks, strokes)]
    return [left, right]
