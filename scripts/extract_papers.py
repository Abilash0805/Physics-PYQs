#!/usr/bin/env python3
"""
Pull questions out of the full CBSE board papers (Oswaal solved papers).

The chapterwise PDFs are already compiled from these same papers, so most
of what is here is a duplicate of something the dataset holds. This keeps
only the questions that are genuinely absent, and files each one under a
chapter using a classifier trained on the chapterwise set - the papers
themselves are ordered by section, not by chapter, so there is no chapter
label to read off the page.

Text comes through `paperpdf`, which reconstructs the maths geometrically;
see that module for why these PDFs need their own token layer.
"""
from __future__ import annotations

import glob
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_v2
from paperpdf import columns, page_tokens
from pdfmath import MathBuilder

# ── page -> text ─────────────────────────────────────────────────────────────

PAPER_NOISE = (
    'Oswaal CBSE',
    'Previous years’ Solved Papers',
    'SOLVED PAPER',
    'CBSE Marking Scheme',
    'Detailed Answer',
    'Answering Tip',
    'Commonly Made Error',
)


MARK_TOK = re.compile(r'^[1-5]$')
# sentinel carrying a mark read off the page margin through the flattened text
MARK_SIG = '\x00M%d'
MARK_SIG_RE = re.compile(r'\x00M([1-5])')


def mark_scripts(grp: list) -> list:
    """Flag sub/superscripts so the renderer treats them as maths.

    `render_flat` already turns a raised or dropped run into `^{}`/`_{}`,
    but only within a run of maths tokens, and these papers set most
    numbers in the body face. Left alone, `10` followed by a raised `11`
    renders as "1011" - so an exponent silently becomes four more digits
    of the mantissa. Marking the script, and the atom it attaches to,
    puts them in one run and the exponent survives.
    """
    real = [t for t in grp if t.latex is None and t.text.strip()]
    if len(real) < 2:
        return grp
    main = max(t.size for t in real)
    full = [t for t in real if t.size >= main * 0.86]
    if not full:
        return grp
    base = sorted(t.baseline for t in full)[len(full) // 2]
    ordered = sorted(grp, key=lambda t: t.x0)
    for idx, t in enumerate(ordered):
        if t.latex is not None or not t.text.strip():
            continue
        if t.size >= main * 0.86:
            continue
        if abs(t.baseline - base) <= 0.6:
            continue
        # a lone raised digit right after a number is an exponent
        t.is_math = True
        if idx > 0 and ordered[idx - 1].size >= main * 0.86:
            ordered[idx - 1].is_math = True
    return grp


def render_column(ctoks, cstrokes) -> list[str]:
    """Render one column, lifting the mark printed in its right margin.

    Each question states its mark as a bare digit set hard against the
    column's right edge. Read as text it is indistinguishable from a digit
    that belongs to the question ("... find the value of n. 2"), so it is
    taken here, where the geometry still says which is which, and carried
    forward as a sentinel.
    """
    built = MathBuilder(ctoks, cstrokes).result()
    if not built:
        return []
    right = max(t.x1 for t in built)
    out: list[str] = []
    for grp in extract_v2.group_lines(built):
        grp = sorted(grp, key=lambda t: t.x0)
        mark = None
        if len(grp) > 1:
            last = grp[-1]
            if (last.latex is None and MARK_TOK.match(last.text.strip())
                    and last.x1 >= right - 12):
                mark = int(last.text.strip())
                grp = grp[:-1]
        txt = extract_v2.render_line(mark_scripts(grp))
        if not txt:
            continue
        if any(n in txt for n in PAPER_NOISE):
            continue
        out.append(txt + (MARK_SIG % mark if mark else ''))
    return out


def two_column_page(toks) -> bool:
    """Whether this page carries two populated columns of text."""
    xs = [t.cx for t in toks]
    if len(xs) < 40:
        return False
    mid = (min(xs) + max(xs)) / 2
    left = sum(1 for x in xs if x < mid)
    right = len(xs) - left
    return min(left, right) / max(left, right, 1) >= 0.35


def page_text(page) -> str | None:
    """Rendered page, or None if it cannot be read safely.

    A two-column page whose gutter was not found would be flattened line by
    line straight across the spread, welding the left column's question onto
    whatever sits beside it. That reads as fluent nonsense - "the shortcomings
    of Rutherford atomic electrons may revolve in stationary orbit" - which no
    later check can reliably spot, so such a page is dropped instead.
    """
    toks, strokes = page_tokens(page)
    if not toks:
        return ''
    cols = columns(toks, strokes)
    if len(cols) < 2 and two_column_page(toks):
        return None
    lines: list[str] = []
    for ctoks, cstrokes in cols:
        lines.extend(render_column(ctoks, cstrokes))
    return '\n'.join(lines)


# ── paper -> question chunks ─────────────────────────────────────────────────

QSTART = re.compile(r'(?m)^\s*\*?\s*(\d{1,2})\.\s+(?=\S)')
ANSTART = re.compile(r'(?m)^\s*Ans\b|^\s*Sol\b|^\s*Explanation\b')
SECTION = re.compile(r'(?m)^\s*SECTION\s*[-–—]?\s*([A-E])\b')
YEAR_RE = re.compile(r'(20\d{2})')
PAGES_DROPPED: dict[str, int] = {}

# marks printed hard against the end of the last line of a question
TRAIL_MARKS = re.compile(r'(?<=[\.\?\:\)\_a-zA-Z])\s*([1-5])\s*$')


def paper_year(path: str, doc=None) -> int:
    m = YEAR_RE.search(os.path.basename(path))
    if m:
        return int(m.group(1))
    # not every paper is dated in its filename; the cover states the year
    if doc is not None:
        head = ' '.join(doc[p].get_text() for p in range(min(2, doc.page_count)))
        m = re.search(r'(?:EXAMINATION|SOLVED)\s+PAPER\s*[-–]?\s*(20\d{2})', head, re.I)
        if m:
            return int(m.group(1))
        found = YEAR_RE.findall(head)
        if found:
            return int(Counter(found).most_common(1)[0][0])
    return 0


def tidy(chunk: str) -> tuple[str, int]:
    """Collapse a chunk to one line and lift its printed mark."""
    marks = 0
    found = MARK_SIG_RE.findall(chunk)
    if found:
        # the mark belonging to this question is the last one printed before
        # the next question starts; earlier hits belong to its sub-parts
        marks = int(found[-1])
    chunk = MARK_SIG_RE.sub(' ', chunk)
    text = extract_v2.clean(chunk)
    # option markers butt straight against the end of the previous option
    text = re.sub(r'(?<=[^\s(])\((([a-dA-D])|([ivx]{1,3}))\)', r' (\1)', text)
    # Private-use codepoints are the Symbol font's extensible bracket
    # pieces - the segments a tall parenthesis is drawn from. They carry no
    # text, and KaTeX throws on them, which would blank the whole question.
    text = re.sub(r'[\ue000-\uf8ff]', '', text)
    text = ''.join(c for c in text if c >= ' ' or c == '\n')
    # empty maths left behind where a formula's parts were consumed by a
    # fraction composite; KaTeX renders `$$` as a stray blank
    text = re.sub(r'\$\s*\$', ' ', text)
    # discretionary hyphens survive extraction and split words back open
    # once the line break they belonged to is gone: "equa\xad tion"
    text = re.sub(r'\u00ad\s*', '', text)
    # a mark that stayed glued to the last word, where the margin test could
    # not separate it from the sentence
    text = re.sub(r'(?<=[a-z\)\.])\s?[1-5]\s*$', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text, marks


def paper_questions(path: str) -> list[dict]:
    doc = pymupdf.open(path)
    pages, dropped = [], 0
    for p in range(doc.page_count):
        t = page_text(doc[p])
        if t is None:
            dropped += 1
            continue
        pages.append(t)
    full = '\n'.join(pages)
    PAGES_DROPPED[os.path.basename(path)] = dropped

    # section each question falls in, so a question with no printed mark can
    # still be given the value its section carries
    sec_at: list[tuple[int, str]] = [(m.start(), m.group(1))
                                     for m in SECTION.finditer(full)]

    def section_of(pos: int) -> str:
        cur = ''
        for at, name in sec_at:
            if at <= pos:
                cur = name
            else:
                break
        return cur

    year = paper_year(path, doc)
    out: list[dict] = []
    starts = list(QSTART.finditer(full))
    for i, m in enumerate(starts):
        stop = starts[i + 1].start() if i + 1 < len(starts) else len(full)
        chunk = full[m.end():stop]
        a = ANSTART.search(chunk)
        if a:
            chunk = chunk[:a.start()]
        text, marks = tidy(chunk)
        if not text:
            continue
        out.append({
            'question': text,
            'marks': marks,
            'section': section_of(m.start()),
            'year': year,
            'source': os.path.basename(path),
        })

    # Questions whose mark did not survive take the value that section of
    # this paper carries, measured from the questions in it that did. The
    # section-to-mark pattern changed between exam years, so it is read off
    # each paper rather than assumed.
    by_sec: dict[str, Counter] = defaultdict(Counter)
    for q in out:
        if q['marks']:
            by_sec[q['section']][q['marks']] += 1
    for q in out:
        if not q['marks'] and by_sec[q['section']]:
            q['marks'] = by_sec[q['section']].most_common(1)[0][0]
    return out


# ── quality gate ─────────────────────────────────────────────────────────────

OPTION_RE = re.compile(r'\(([a-dA-D])\)\s*([^()]*)')
JUNK_LINE = re.compile(r'^[\W\d_]{0,4}$')


def options_of(text: str) -> list[str]:
    return [o.strip(' .') for _, o in OPTION_RE.findall(text)]


def mcq_options(text: str) -> list[str]:
    """The option list of a multiple-choice question, if this is one.

    `(a)`/`(b)` also number the parts of a structured question, and a
    worked answer inherits that numbering - so the markers alone cannot
    tell an option list from an essay's sub-parts. Options are terse
    ("10 V", "both increase"); sub-parts run to whole sentences.
    """
    found = OPTION_RE.findall(text)
    # An option list runs a, b, c, d in order. Physics prose is full of
    # bracketed single letters that are not options at all - the electric
    # field (E), the magnetic field (B) - and matching markers loosely lets
    # an essay's (a)/(b) sub-parts plus a stray (E) pass as a question's
    # choices.
    letters = [m.lower() for m, _ in found]
    if len(letters) < 3 or letters != [chr(ord('a') + i) for i in range(len(letters))]:
        return []
    opts = [o.strip(' .') for _, o in found]
    if max(len(o) for o in opts) > 80:
        return []
    # Options are printed together at the foot of the question. The parts of
    # a long structured answer are also lettered in order and can each be
    # short, but they are spread over the whole text rather than bunched.
    marks = [m.start() for m in OPTION_RE.finditer(text)]
    if marks[-1] - marks[0] > 400:
        return []
    return opts


# The verb has to sit where an instruction sits - opening the question or a
# sub-part - because the same words appear inside answers as description:
# "Define mutual inductance" asks, "resistivity is defined as" does not.
# The verb has to sit where an instruction sits - opening the question or a
# sub-part - because the same words appear inside answers as description:
# "Define mutual inductance" asks, "resistivity is defined as" does not.
# The trailing boundaries matter as much as the leading one: without them
# "How" matches "However" and "Give" matches "Given", so an answer's own
# prose reads as an instruction.
ASKS = re.compile(
    r'(?:^|[.:;?]\s*|\)\s*|\bOR\s+)\s*'
    r'(calculat\w*|find(?!ing\b)\w*|deriv\w*|state(?!ment)\w*|explain\w*|'
    r'draw\w*|show(?!n\b)\w*|defin\w*|write\w*|obtain\w*|deduc\w*|prove\w*|'
    r'determin\w*|compar\w*|name(?!d\b)\w*|identif\w*|distinguish\w*|'
    r'establish\w*|justify|discuss\w*|mention\w*|estimat\w*|plot\w*|trace\w*|'
    r'describ\w*|what|why|how(?!ever)|which|where|when(?!ever)|give(?!n\b)\w*|'
    r'answer\w*|choose|select|fill|assertion|reason)\b',
    re.I)


SOLUTION_OPENER = re.compile(
    r'^\s*\(?[a-z]?\)?\s*(given|since|hence|therefore|thus|from eq|as per|'
    r'we know|let|according to|substituting|putting|on solving|comparing)\b', re.I)


def looks_like_solution(text: str) -> bool:
    """Whether this chunk is a worked answer rather than a question.

    The papers interleave each question with its marking-scheme solution.
    Most solutions are introduced by "Ans." and cut off there, but some
    run on unlabelled, and a numbered working step reads exactly like a
    question number. A solution states rather than asks: it opens with
    "Given"/"Since", and it is dense with equations.
    """
    if SOLUTION_OPENER.match(text):
        return True
    words = re.sub(r'\$[^$]*\$', ' ', text).split()
    if not words:
        return True
    # an unusual density of equals signs is working, not a question
    if text.count('=') >= 3 and text.count('=') / len(words) > 0.06:
        return True
    # A multiple-choice stem states rather than asks - "the force per unit
    # length between them is:" - so requiring a question verb would throw
    # away most of the MCQs. Having options is itself proof of a question.
    if len([o for o in mcq_options(text) if o]) >= 2:
        return False
    # Judge the opening, not the whole text. A question asks something up
    # front - or sets up a scenario and asks by the end of its first part -
    # whereas an answer opens by stating ("The kinetic energy of emitted
    # photoelectrons varies because ...") and only reads like an
    # instruction much later, where its own explanation happens to use one
    # of these verbs.
    head = text[:220]
    if not ASKS.search(head) and '?' not in head and '___' not in head:
        return True
    return False


def is_sound(text: str) -> tuple[bool, str]:
    """Reject anything whose notation clearly did not survive the PDF.

    The whole point of this pass is notation, so a question that reads
    plausibly but has lost the maths that distinguishes its options is
    worse than no question at all.
    """
    if not (40 <= len(text) <= 1800):
        return False, 'length'
    words = re.sub(r'\$[^$]*\$', ' ', text).split()
    if len(words) < 8:
        return False, 'too few words'
    # stray single characters are the signature of a column fragment that
    # drifted into the chunk
    if sum(1 for w in words if len(w) == 1 and w.isalpha()) > 6:
        return False, 'fragments'
    opts = mcq_options(text)
    if opts:
        real = [o for o in opts if o]
        if len(real) < len(opts):
            return False, 'empty option'
        if len(set(real)) < len(real):
            return False, 'duplicate options'
    if text.count('$') % 2:
        return False, 'unbalanced math'
    if re.search(r'(Fig|figure|graph|diagram|shown in)', text, re.I) and len(words) < 14:
        return False, 'figure-only'
    if looks_like_solution(text):
        return False, 'worked solution'
    # A question that stops mid-sentence lost its tail to a page or column
    # break. Option lists legitimately end on the last option, so they are
    # judged on their options instead.
    if not opts and text[-1] not in '.?:;)]}"\'':
        return False, 'truncated'
    # Two columns of a comparison table read row by row run their cells
    # together - "particles.particles.", "fissionNuclear" - which is the
    # one kind of damage that still reads as continuous prose.
    joins = (len(re.findall(r'[a-z]\.[a-z]', text))
             + len(re.findall(r'[a-z][A-Z]', text)))
    if joins >= 2:
        return False, 'run-together'
    # A formula drawn with tall brackets loses its structure when those
    # bracket glyphs are dropped, leaving its symbols stranded as bare
    # commands: "a capacitor of $\\mu$ F and an $\\pi$ 4 inductor of H".
    lone = sum(1 for i, part in enumerate(text.split('$'))
               if i % 2 and re.fullmatch(r'\s*\\[a-zA-Z]+\s*', part))
    if lone >= 3:
        return False, 'broken formula'
    return True, ''


# ── chapter classifier ───────────────────────────────────────────────────────

STOP = set('''a an the of in on to for and or is are was were be been being with by
from at as that this these those it its which what how why when where does do did
following given figure fig shown find calculate obtain derive state define explain
write draw show two one also if then than into out has have such each per using use
same different between will can may would should i ii iii iv v b c d'''.split())

TOKEN = re.compile(r'[a-z]+')


def features(text: str) -> list[str]:
    text = re.sub(r'\$[^$]*\$', ' ', text).lower()
    return [w for w in TOKEN.findall(text) if len(w) > 2 and w not in STOP]


class NaiveBayes:
    """Multinomial naive Bayes - the vocabulary here is strongly chapter
    specific ("capacitor", "de-broglie", "prism"), so a bag of words
    separates the chapters well and stays inspectable."""

    def __init__(self) -> None:
        self.prior: dict[str, float] = {}
        self.lik: dict[str, dict[str, float]] = {}
        self.default: dict[str, float] = {}

    def fit(self, docs: list[tuple[str, str]]) -> None:
        by_class: dict[str, Counter] = defaultdict(Counter)
        counts: Counter = Counter()
        vocab: set[str] = set()
        for label, text in docs:
            f = features(text)
            by_class[label].update(f)
            counts[label] += 1
            vocab.update(f)
        n = len(docs)
        v = len(vocab)
        for label, cnt in by_class.items():
            self.prior[label] = math.log(counts[label] / n)
            total = sum(cnt.values()) + v
            self.lik[label] = {w: math.log((c + 1) / total) for w, c in cnt.items()}
            self.default[label] = math.log(1 / total)

    def scores(self, text: str) -> list[tuple[float, str]]:
        f = features(text)
        out = []
        for label in self.prior:
            s = self.prior[label]
            lik, dflt = self.lik[label], self.default[label]
            for w in f:
                s += lik.get(w, dflt)
            out.append((s, label))
        out.sort(reverse=True)
        return out


def norm_key(s: str) -> str:
    s = re.sub(r'\$[^$]*\$', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return ' '.join(s.split())


def main() -> None:
    src = sys.argv[1]
    base_path = sys.argv[2]
    out_path = sys.argv[3]

    base = json.load(open(base_path, encoding='utf-8'))
    known = base['questions']

    # ---- train + report held-out accuracy -------------------------------
    docs = [(q['chapter'], q['question']) for q in known]
    rnd = random.Random(20260901)
    shuffled = docs[:]
    rnd.shuffle(shuffled)
    cut = int(0.8 * len(shuffled))
    dev = NaiveBayes()
    dev.fit(shuffled[:cut])
    hold = shuffled[cut:]
    ok = margin_ok = margin_n = 0
    for label, text in hold:
        sc = dev.scores(text)
        if sc[0][1] == label:
            ok += 1
        if sc[0][0] - sc[1][0] >= MARGIN:
            margin_n += 1
            if sc[0][1] == label:
                margin_ok += 1
    print(f'classifier held-out accuracy : {ok}/{len(hold)} = {ok/len(hold):.1%}')
    print(f'  at margin >= {MARGIN}            : {margin_ok}/{margin_n} = '
          f'{margin_ok/max(margin_n,1):.1%} (keeps {margin_n/len(hold):.0%})')

    clf = NaiveBayes()
    clf.fit(docs)

    # ---- index the existing questions for duplicate detection -----------
    idx: dict[str, list[int]] = defaultdict(list)
    normed = [norm_key(q['question']) for q in known]
    for i, b in enumerate(normed):
        w = b.split()
        for k in range(0, max(1, len(w) - 7), 3):
            idx[' '.join(w[k:k + 8])].append(i)

    def seen(text: str) -> bool:
        w = norm_key(text).split()
        if len(w) < 8:
            return True
        for k in range(0, max(1, len(w) - 7), 3):
            if ' '.join(w[k:k + 8]) in idx:
                return True
        return False

    papers = [f for f in sorted(glob.glob(os.path.join(src, '*.pdf')))
              if not os.path.basename(f).startswith('class-12-physics-')]

    rejected: Counter = Counter()
    kept: list[dict] = []
    fresh_keys: set[str] = set()
    print(f'\n{"paper":32}{"found":>7}{"dup":>6}{"cut":>6}{"new":>6}')
    for f in papers:
        qs = paper_questions(f)
        dup = cut_n = new = 0
        for q in qs:
            good, why = is_sound(q['question'])
            if not good:
                rejected[why] += 1
                cut_n += 1
                continue
            if seen(q['question']):
                dup += 1
                continue
            key = norm_key(q['question'])[:120]
            if key in fresh_keys:
                dup += 1
                continue
            fresh_keys.add(key)
            sc = clf.scores(q['question'])
            if sc[0][0] - sc[1][0] < MARGIN:
                rejected['unsure chapter'] += 1
                cut_n += 1
                continue
            q['chapter'] = sc[0][1]
            kept.append(q)
            new += 1
        print(f'{os.path.basename(f)[:32]:32}{len(qs):7}{dup:6}{cut_n:6}{new:6}')

    # Every question needs a real mark: it drives the marks filter, the
    # chapter breakdown and the answer hints, and a question whose mark
    # could not be read is usually one whose text is not a question either.
    graded = [q for q in kept if q['marks'] in (1, 2, 3, 4, 5)]
    rejected['no mark'] = len(kept) - len(graded)

    print('\nrejected:', dict(rejected.most_common()))
    print('kept     :', len(graded))

    # ---- merge into the dataset ----------------------------------------
    TYPE = {1: 'MCQ', 2: 'VSA', 3: 'SA', 4: 'Case Study', 5: 'Long Answer'}
    per_chapter: Counter = Counter()
    for q in known:
        per_chapter[q['chapter']] += 1

    merged = list(known)
    for q in sorted(graded, key=lambda z: (z['chapter'], z['year'])):
        per_chapter[q['chapter']] += 1
        slug = re.sub(r'[^a-z0-9]+', '-', q['chapter'].lower()).strip('-')
        merged.append({
            'chapter': q['chapter'],
            'marks': q['marks'],
            'type': TYPE[q['marks']],
            'year': q['year'],
            'paper': f"Board Paper {q['year']}" if q['year'] else 'Board Paper',
            'question': q['question'],
            'id': f'{slug}-{per_chapter[q["chapter"]]}',
            'answer': None,
            'bookmarked': False,
            'solved': False,
            'in_syllabus': True,
        })

    chapters = []
    for name in sorted({q['chapter'] for q in merged}):
        qs = [q for q in merged if q['chapter'] == name]
        dist: Counter = Counter()
        for q in qs:
            dist[str(q['marks'])] += 1
        chapters.append({
            'name': name,
            'count': len(qs),
            'years': sorted({q['year'] for q in qs if q['year']}),
            'marks_dist': dict(sorted(dist.items())),
            'slug': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'),
        })

    data = {
        'chapters': chapters,
        'questions': merged,
        'total': len(merged),
        'matched_answers': sum(1 for q in merged if q.get('answer')),
    }
    json.dump(data, open(out_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'dataset  : {len(known)} + {len(graded)} = {len(merged)}')
    print('saved    →', out_path)


MARGIN = 8.0

if __name__ == '__main__':
    main()
