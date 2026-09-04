#!/usr/bin/env python3
"""
Geometry-aware LaTeX reconstruction from LaTeX-generated PDFs.

The chapter PYQ PDFs are typeset with LaTeX (Computer Modern math fonts).
Plain-text extraction destroys 2D structure: `5/sqrt(2)` and `5*sqrt(2)`
both flatten to the same "5 \n sqrt \n 2". This module rebuilds the real
structure from span geometry plus the horizontal rules that LaTeX draws
for fraction bars and square-root overlines.

Key signals
  * prose spans use CharterBT*, math spans use CM* (Computer Modern)
  * a fraction bar is a horizontal stroke with content above AND below
  * a sqrt overline is a horizontal stroke starting at a radical glyph's
    right edge, with content only beneath it
  * sub/superscripts are ~0.67x the surrounding size, distinguished by
    whether their baseline sits below or above the running baseline
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Unicode -> LaTeX ─────────────────────────────────────────────────────────

GREEK = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
    'ε': r'\varepsilon', 'ϵ': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta',
    'θ': r'\theta', 'ϑ': r'\vartheta', 'ι': r'\iota', 'κ': r'\kappa',
    'λ': r'\lambda', 'μ': r'\mu', 'µ': r'\mu', 'ν': r'\nu', 'ξ': r'\xi',
    'π': r'\pi', 'ρ': r'\rho', 'σ': r'\sigma', 'τ': r'\tau',
    'υ': r'\upsilon', 'φ': r'\phi', 'ϕ': r'\phi', 'χ': r'\chi',
    'ψ': r'\psi', 'ω': r'\omega',
    'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda',
    'Ξ': r'\Xi', 'Π': r'\Pi', 'Σ': r'\Sigma', 'Υ': r'\Upsilon',
    'Φ': r'\Phi', 'Ψ': r'\Psi', 'Ω': r'\Omega',
}

SYMBOLS = {
    '×': r'\times', '÷': r'\div', '±': r'\pm', '∓': r'\mp',
    '≤': r'\leq', '≥': r'\geq', '≠': r'\neq', '≈': r'\approx',
    '≡': r'\equiv', '∝': r'\propto', '∞': r'\infty', '∴': r'\therefore',
    '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
    '⇒': r'\Rightarrow', '⇌': r'\rightleftharpoons',
    '∈': r'\in', '∑': r'\sum', '∫': r'\int', '∮': r'\oint',
    '∂': r'\partial', '∇': r'\nabla', '·': r'\cdot', '⋅': r'\cdot',
    '°': r'^{\circ}', '′': r"'", '″': r"''",
    '⊥': r'\perp', '∥': r'\parallel', '∠': r'\angle',
    '−': '-', '–': '-', '—': '---',
    '⟨': r'\langle', '⟩': r'\rangle', 'ℏ': r'\hbar', 'ℓ': r'\ell',
    # U+2126 OHM SIGN - distinct codepoint from U+03A9 capital omega,
    # and the one Computer Modern actually emits for resistance units.
    'Ω': r'\Omega',
    '◦': r'^{\circ}', '∘': r'^{\circ}',
    '̸': '',            # combining long solidus, handled by \neq etc.
    '′': r"'", '·': r'\cdot',
    '≫': r'\gg', '≪': r'\ll', '∼': r'\sim', '≅': r'\cong', '⊙': r'\odot',
    '˚': r'^{\circ}', '¯': '-', 'ˇ': '', '˙': '',
}

# Accents arrive as free-standing positioned glyphs rather than as combining
# marks attached to a base letter, so they can land on either side of it.
VEC_ARROW = '⃗'   # COMBINING RIGHT ARROW ABOVE - vectors
HAT_CIRC = 'ˆ'    # MODIFIER LETTER CIRCUMFLEX - unit vectors, superscripts

# Superscript / subscript unicode that LaTeX sometimes emits directly
UNI_SUP = {'⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
           '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', '⁻': '-', '⁺': '+'}
UNI_SUB = {'₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5',
           '₆': '6', '₇': '7', '₈': '8', '₉': '9', '₋': '-', '₊': '+'}

RADICAL = '√'

# CMEX10 is LaTeX's extension font: it holds the grown delimiters, and its
# glyph codes are raw control bytes that no Unicode mapping recovers. The
# encoding repeats every 16 codes, one size step per block.
CMEX_DELIMS = {
    0x0: '(', 0x1: ')', 0x2: '[', 0x3: ']',
    0x4: r'\lfloor', 0x5: r'\rfloor', 0x6: r'\lceil', 0x7: r'\rceil',
    0x8: r'\{', 0x9: r'\}', 0xA: r'\langle', 0xB: r'\rangle',
    0xC: '|', 0xD: r'\|', 0xE: '/', 0xF: r'\backslash',
}


def cmex_char(ch: str) -> str | None:
    o = ord(ch)
    if o < 0x40:
        return CMEX_DELIMS.get(o & 0x0F)
    return None


def esc_latex(ch: str) -> str:
    """Escape a single character for LaTeX math mode."""
    if ch in GREEK:
        return GREEK[ch]
    if ch in SYMBOLS:
        return SYMBOLS[ch]
    if ch in UNI_SUP:
        return '^{%s}' % UNI_SUP[ch]
    if ch in UNI_SUB:
        return '_{%s}' % UNI_SUB[ch]
    if ch in '%&#_':
        return '\\' + ch
    if ch == '\\':
        return r'\backslash '
    if ch in '{}':
        return '\\' + ch
    return ch


def to_latex_text(s: str, font: str = '') -> str:
    if font.upper().startswith('CMEX'):
        return ''.join((cmex_char(c) or esc_latex(c)) for c in s)
    # stray control bytes from any other maths font carry no glyph
    return ''.join(esc_latex(c) for c in s if ord(c) >= 32 or c in '\t')


# Every control sequence this module can emit, longest first so that
# \varepsilon is tried before \var-anything-shorter.
_CMDS = sorted(
    {v.lstrip('\\').rstrip(' ') for v in list(GREEK.values()) + list(SYMBOLS.values())
     if v.startswith('\\') and v[1:].isalpha()} | {'sqrt', 'frac'},
    key=len, reverse=True,
)
_CMD_RE = re.compile(r'(\\(?:%s))(?=[A-Za-z])' % '|'.join(_CMDS))
_FUNCS = ('arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh',
          'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'exp', 'max', 'min')
_FUNC_RE = re.compile(r'(?<![A-Za-z\\])(%s)(?![A-Za-z])' % '|'.join(_FUNCS))


def polish_math(body: str) -> str:
    """Tidy a reconstructed maths run.

    * `\\omegat` -> `\\omega t`   (a command must not swallow the next letter)
    * `sin` -> `\\sin`            (upright operator names)
    """
    body = _CMD_RE.sub(r'\1 ', body)
    body = _FUNC_RE.sub(r'\\\1', body)

    # vector arrows -> \vec{B}
    body = re.sub(VEC_ARROW + r'\s*([A-Za-z])', r'\\vec{\1}', body)
    body = re.sub(r'([A-Za-z])\s*' + VEC_ARROW, r'\\vec{\1}', body)
    body = body.replace(VEC_ARROW, '')

    # circumflex: a superscript when it introduces a group, otherwise the
    # unit-vector hat of the adjacent letter
    body = re.sub(HAT_CIRC + r'\s*\\?\{', '^{', body)
    body = re.sub(HAT_CIRC + r'\s*([A-Za-z])', r'\\hat{\1}', body)
    body = re.sub(r'([A-Za-z])\s*' + HAT_CIRC, r'\\hat{\1}', body)
    body = body.replace(HAT_CIRC, '^')

    # a few PDFs carry literal LaTeX in the text layer; un-escape the braces
    # that form a script group so `^\{2\}` reads as `^{2}`
    body = re.sub(r'([\^_])\\\{([^{}\\]*?)\\\}', r'\1{\2}', body)

    # Two scripts in a row ("i^{2} ^{1}") is a stacking artefact, not a
    # double exponent. Give the second one an empty base so KaTeX accepts it
    # instead of throwing and blanking the whole expression.
    for _ in range(4):
        new = re.sub(r'(\^\{[^{}]*\})\s*(?=\^\{)', r'\1{}', body)
        new = re.sub(r'(_\{[^{}]*\})\s*(?=_\{)', r'\1{}', new)
        if new == body:
            break
        body = new

    body = re.sub(r'\s{2,}', ' ', body)
    return body.strip()


# ── Tokens ───────────────────────────────────────────────────────────────────

@dataclass
class Tok:
    """A span or a synthesised composite (fraction / sqrt) with geometry."""
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str
    text: str            # raw text for leaf spans
    latex: str | None = None   # set for composites
    is_math: bool = False
    anchor: float | None = None   # text baseline, for line grouping

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def baseline(self) -> float:
        """Where this token sits on the running text line.

        A composite spans several visual rows, so its bounding box centre is
        useless for line grouping - carry the real baseline instead.
        """
        return self.anchor if self.anchor is not None else self.y1


@dataclass
class Stroke:
    x0: float
    y: float
    x1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0


# Glyphs that live in a maths font but read as punctuation - keeping them
# out of math mode avoids a page full of "$\bullet$".
PROSE_GLYPHS = set('•·–—‘’“”…')


def _has_content(t: 'Tok') -> bool:
    return t.latex is not None or bool(t.text.strip())


def is_math_font(font: str) -> bool:
    f = font.upper()
    return f.startswith('CM') or 'MATH' in f or f.startswith('MSBM') or f.startswith('MSAM')


def is_math_span(font: str, text: str) -> bool:
    if not is_math_font(font):
        return False
    stripped = text.strip()
    if stripped and all(c in PROSE_GLYPHS for c in stripped):
        return False
    return True


# ── Core reconstruction ──────────────────────────────────────────────────────

class MathBuilder:
    """Rebuilds LaTeX from spans + horizontal rules within one text line group."""

    # tolerances (PDF points)
    X_TOL = 1.8
    Y_TOL = 1.2

    def __init__(self, toks: list[Tok], strokes: list[Stroke]):
        self.toks = list(toks)
        self.strokes = list(strokes)

    # -- classification -------------------------------------------------

    def _radical_for(self, s: Stroke, claimed: set[int]) -> Tok | None:
        """Return the radical glyph whose overline this stroke is, if any."""
        best = None
        for t in self.toks:
            if t.latex is not None or RADICAL not in t.text or id(t) in claimed:
                continue
            # overline begins at the radical's right edge and sits near its top
            if abs(t.x1 - s.x0) <= self.X_TOL and t.y0 - 2.5 <= s.y <= t.y1:
                if best is None or abs(t.x1 - s.x0) < abs(best.x1 - s.x0):
                    best = t
        return best

    # -- collapsing -----------------------------------------------------

    def _consume(self, items: list[Tok]) -> None:
        for it in items:
            if it in self.toks:
                self.toks.remove(it)

    def _spans_in_x(self, s: Stroke, pad: float = 0.0) -> list[Tok]:
        """Spans horizontally under the rule AND vertically adjacent to it.

        The vertical window matters: without it a rule happily swallows
        unrelated text further down the page.
        """
        lo, hi = s.x0 - pad, s.x1 + pad
        out = []
        for t in self.toks:
            if not (lo - self.X_TOL <= t.cx <= hi + self.X_TOL):
                continue
            if abs(t.cy - s.y) > 1.45 * max(t.size, 7.0):
                continue
            out.append(t)
        return out

    def collapse(self) -> None:
        """Fold every stroke into a composite token, innermost first."""
        # Pair radicals with their overlines up front. Radicals are claimed
        # exclusively, so a radical belonging to the option on the next row
        # cannot be dragged into this one's radicand.
        pairs: list[tuple[Stroke, Tok]] = []
        bars: list[Stroke] = []
        claimed: set[int] = set()
        for s in sorted(self.strokes, key=lambda s: s.width):
            rad = self._radical_for(s, claimed)
            if rad is not None:
                claimed.add(id(rad))
                pairs.append((s, rad))
            else:
                bars.append(s)

        self._claimed_radicals = claimed
        # radicals nest inside fractions far more often than the reverse
        for s, rad in sorted(pairs, key=lambda p: p[0].width):
            self._collapse_sqrt(s, rad)
        for s in sorted(bars, key=lambda s: s.width):
            self._collapse_frac(s)

    def _collapse_sqrt(self, s: Stroke, rad: Tok) -> None:
        # LaTeX draws the overline exactly over the radicand, so require
        # horizontal containment rather than mere centre-overlap.
        body = [t for t in self.toks
                if t is not rad
                and t.x0 >= s.x0 - self.X_TOL
                and t.x1 <= s.x1 + self.X_TOL
                and t.cy > s.y
                and t.cy - s.y <= 1.45 * max(t.size, 7.0)]
        inner = render_flat(body).strip() if body else ''
        x0, y0 = rad.x0, min([rad.y0] + [t.y0 for t in body])
        x1 = max([rad.x1, s.x1] + [t.x1 for t in body])
        y1 = max([rad.y1] + [t.y1 for t in body])
        base = max([t.baseline for t in body], default=rad.y1)
        tok = Tok(x0, y0, x1, y1, rad.size, rad.font, '',
                  latex=r'\sqrt{%s}' % inner, is_math=True, anchor=base)
        self._consume(body + [rad])
        self.toks.append(tok)

    @staticmethod
    def _nearest_row(cands: list[Tok], bar_y: float) -> list[Tok]:
        """Keep only the row closest to the rule.

        Line spacing is comparable to the numerator gap, so an unguarded
        search happily reaches into the previous printed line and drags a
        stray word into the fraction.
        """
        if not cands:
            return []
        closest = min(abs(t.cy - bar_y) for t in cands)
        return [t for t in cands
                if abs(t.cy - bar_y) - closest <= 0.55 * max(t.size, 7.0)]

    def _collapse_frac(self, s: Stroke) -> None:
        # A LaTeX fraction is built from maths-font material; prose spans in
        # range belong to the surrounding sentence, not to the fraction.
        # Blank spans are dropped too: LaTeX parks kerning glyphs right on
        # the maths axis, and they would otherwise win "nearest row" and
        # evict the actual numerator.
        cand = [t for t in self._spans_in_x(s, pad=1.0)
                if (t.latex is not None or t.is_math) and _has_content(t)]
        num = self._nearest_row([t for t in cand if t.cy < s.y], s.y)
        den = self._nearest_row([t for t in cand if t.cy > s.y], s.y)
        # A genuine fraction has content on both sides. A bare rule with
        # nothing above or below is a table/section divider - leave it be.
        if not num or not den:
            return
        n = render_flat(num).strip() if num else ''
        d = render_flat(den).strip() if den else ''
        group = num + den
        x0 = min([s.x0] + [t.x0 for t in group])
        x1 = max([s.x1] + [t.x1 for t in group])
        y0 = min([s.y] + [t.y0 for t in group])
        y1 = max([s.y] + [t.y1 for t in group])
        size = max((t.size for t in group), default=10.0)
        # the rule sits on the maths axis, roughly a quarter em above baseline
        tok = Tok(x0, y0, x1, y1, size, 'CM', '',
                  latex=r'\frac{%s}{%s}' % (n or '{}', d or '{}'),
                  is_math=True, anchor=s.y + 0.25 * size)
        self._consume(group)
        self.toks.append(tok)

    def result(self) -> list[Tok]:
        self.collapse()
        return sorted(self.toks, key=lambda t: t.x0)


def render_flat(toks: list[Tok]) -> str:
    """Render a horizontally-ordered token list, handling sub/superscripts."""
    if not toks:
        return ''
    toks = sorted(toks, key=lambda t: t.x0)
    main = max(t.size for t in toks)
    # running baseline = baseline of the largest tokens
    base_toks = [t for t in toks if t.size >= main * 0.9]
    baseline = sorted(t.baseline for t in base_toks)[len(base_toks) // 2]

    out: list[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.size < main * 0.86:
            # gather the contiguous run of same-script small tokens
            sub = t.baseline > baseline + 0.6
            run = [t]
            j = i + 1
            while j < len(toks):
                n = toks[j]
                if n.size >= main * 0.86:
                    break
                if (n.baseline > baseline + 0.6) != sub:
                    break
                if n.x0 - run[-1].x1 > 1.6:
                    break
                run.append(n)
                j += 1
            body = ''.join(_leaf(x) for x in run).strip()
            if body:
                out.append(('_{%s}' if sub else '^{%s}') % body)
            i = j
            continue
        out.append(_leaf(t))
        i += 1
    return ''.join(out)


def _leaf(t: Tok) -> str:
    if t.latex is not None:
        return t.latex
    return to_latex_text(t.text, t.font)
