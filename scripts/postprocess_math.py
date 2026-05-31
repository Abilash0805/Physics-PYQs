#!/usr/bin/env python3
"""
Post-processor: convert plain-text physics notation extracted from PDFs to
LaTeX-delimited ($...$) strings suitable for KaTeX rendering.
"""
import json, re, os, shutil


# ── Helpers ───────────────────────────────────────────────────────────────────

def split_math_nonmath(text):
    """Split text into (is_math, segment) pairs."""
    parts = re.split(r'(\$[^$]+?\$)', text)
    result = []
    for p in parts:
        if p.startswith('$') and p.endswith('$') and len(p) > 2:
            result.append((True, p))
        else:
            result.append((False, p))
    return result


def apply_to_nonmath(text, fn):
    """Apply fn only to non-math portions, preserving $...$ blocks."""
    parts = split_math_nonmath(text)
    return ''.join(fn(p) if not is_math else p for is_math, p in parts)


# ── Nuclear notation ──────────────────────────────────────────────────────────

ELEMENTS = (
    'He|Li|Be|Ne|Na|Mg|Al|Si|Cl|Ar|Ca|Sc|Ti|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|'
    'Se|Br|Kr|Rb|Sr|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|In|Sn|Sb|Te|Xe|Cs|Ba|La|Ce|'
    'Nd|Pm|Sm|Eu|Gd|Tb|Dy|Ho|Er|Tm|Yb|Lu|Hf|Ta|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi|'
    'Po|At|Rn|Fr|Ra|Ac|Th|Pa|Np|Pu|Am|Cm|'
    'H|B|C|N|O|F|P|S|K|V|W|U|Y|I'  # single-letter last
)

def fix_nuclear(text):
    """'238 92 U' → '${}^{238}_{92}\\text{U}$'"""
    pat = re.compile(r'\b(\d{1,3})\s+(\d{1,2})\s+(' + ELEMENTS + r')\b')
    return pat.sub(
        lambda m: f'${{}}^{{{m.group(1)}}}_{{{m.group(2)}}}\\text{{{m.group(3)}}}$',
        text
    )


# ── Unicode → LaTeX (produces raw LaTeX, NOT wrapped in $) ───────────────────

GREEK = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'Γ': r'\Gamma',
    'δ': r'\delta', 'Δ': r'\Delta', 'ε': r'\varepsilon', 'ζ': r'\zeta',
    'η': r'\eta', 'θ': r'\theta', 'Θ': r'\Theta', 'ι': r'\iota',
    'κ': r'\kappa', 'λ': r'\lambda', 'Λ': r'\Lambda', 'μ': r'\mu',
    'µ': r'\mu',   # micro sign
    'ν': r'\nu', 'ξ': r'\xi', 'Ξ': r'\Xi', 'π': r'\pi', 'Π': r'\Pi',
    'ρ': r'\rho', 'σ': r'\sigma', 'Σ': r'\Sigma', 'τ': r'\tau',
    'υ': r'\upsilon', 'φ': r'\phi', 'Φ': r'\Phi', 'χ': r'\chi',
    'ψ': r'\psi', 'Ψ': r'\Psi', 'ω': r'\omega', 'Ω': r'\Omega',
}

OPERATORS = {
    '×': r'\times',
    '÷': r'\div',
    '≤': r'\leq',
    '≥': r'\geq',
    '≠': r'\neq',
    '≈': r'\approx',
    '∝': r'\propto',
    '∞': r'\infty',
    '∫': r'\int',
    '∑': r'\sum',
    '∂': r'\partial',
    '∇': r'\nabla',
    '→': r'\rightarrow',
    '←': r'\leftarrow',
    '⇒': r'\Rightarrow',
    '°': r'^\circ',
    '−': '-',  # unicode minus → ascii
}

SQRT_TOKEN = '__SQRT__'

def apply_unicode(text):
    text = text.replace('√', SQRT_TOKEN)
    for ch, rep in {**GREEK, **OPERATORS}.items():
        text = text.replace(ch, rep)
    return text


# ── SQRT patterns ─────────────────────────────────────────────────────────────

def fix_sqrt(seg):
    """Handle SQRT_TOKEN patterns within a non-math segment."""
    # "NUM __SQRT__ NUM" → $\frac{NUM}{\sqrt{NUM}}$
    seg = re.sub(
        r'(?<![A-Za-z_$])(\d+(?:\.\d+)?)\s+' + re.escape(SQRT_TOKEN) + r'\s+(\d+(?:\.\d+)?)(?!\d)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\sqrt{{{m.group(2)}}}}}$',
        seg
    )
    # "__SQRT__ NUM" → $\sqrt{NUM}$
    seg = re.sub(
        re.escape(SQRT_TOKEN) + r'\s*(\d+(?:\.\d+)?)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        seg
    )
    # "__SQRT__ {EXPR}" or bare __SQRT__
    seg = seg.replace(SQRT_TOKEN, r'$\sqrt{}$')
    return seg


# ── Subscripts / superscripts ─────────────────────────────────────────────────

def fix_subscripts(seg):
    """Convert physics subscript patterns in plain text."""
    # XL, XC, XR reactance
    seg = re.sub(r'\bX([LCR])\b', r'$X_{\1}$', seg)
    # VL, VC, VR, VR
    seg = re.sub(r'\bV([LCR])\b', r'$V_{\1}$', seg)
    # Peak/amplitude: V0, I0, E0, B0, v0, i0
    seg = re.sub(r'\b([VIEvBbi])0\b', r'$\1_0$', seg)
    # vm, im, Em, Vm — amplitude with subscript m
    seg = re.sub(r'\b([VIEvi])m\b', r'$\1_m$', seg)
    # Component labels C1,C2,L1,L2,R1,R2,i1,i2,v1,v2
    seg = re.sub(r'\b([CLRilrn])([12345])\b', r'$\1_\2$', seg)
    # C1/C2 ratio keeps as fraction
    return seg


# ── Scientific notation & fractions ──────────────────────────────────────────

def fix_sci_notation(seg):
    # "4.5 \times 10^9" (after unicode replacement)
    seg = re.sub(
        r'(\d+(?:\.\d+)?)\s*\\times\s*10\s*\^?\s*\{?(-?\d+)\}?',
        lambda m: f'${m.group(1)} \\times 10^{{{m.group(2)}}}$',
        seg
    )
    # "10-3" meaning 10^{-3}
    seg = re.sub(
        r'\b10-(\d+)\b',
        lambda m: f'$10^{{-{m.group(1)}}}$',
        seg
    )
    # "10^5 4\pi" from fraction → $\frac{10^5}{4\pi}$
    seg = re.sub(
        r'10\^?\{?(\d+)\}?\s+(\d*)\\pi',
        lambda m: f'$\\frac{{10^{{{m.group(1)}}}}}{{{m.group(2)}\\pi}}$',
        seg
    )
    return seg


# ── Wrap bare LaTeX commands in $ ─────────────────────────────────────────────

LATEX_CMDS = (
    r'\\(?:alpha|beta|gamma|delta|varepsilon|epsilon|zeta|eta|theta|iota|kappa|'
    r'lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|'
    r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|'
    r'vec\{[^}]+\}|hat\{[^}]+\}|bar\{[^}]+\}|'
    r'times|div|leq|geq|neq|approx|propto|rightarrow|leftarrow|Rightarrow|'
    r'infty|pm|mp|cdot|partial|nabla|sin|cos|tan|log|ln|exp|int|sum|sqrt|frac|circ)'
)

def wrap_bare_latex(seg):
    """Wrap LaTeX commands that appear bare (not inside $...$) in $...$."""
    # Find the longest contiguous math expression around each command
    # Heuristic: grab surrounding math-like tokens
    MATH_TOKEN = r'(?:\\[A-Za-z]+(?:\{[^}]*\})*|[A-Za-z0-9_^{}\[\]()\+\-\*\/\.,\s])'

    def replacer(m):
        return f'${m.group(0).strip()}$'

    # Simple: each bare \cmd → $\cmd$
    seg = re.sub(LATEX_CMDS, replacer, seg)

    # Merge adjacent $...$ blocks separated only by whitespace or simple tokens
    # e.g. "$\omega$ t" → "$\omega t$" is not always right, keep separate for safety
    return seg


def merge_adjacent_math(text):
    """Merge '$A$ $B$' → '$A B$' when they form a single expression."""
    # Merge cases like "$\omega$ t" into "$\omega t$" only if t is a simple variable
    text = re.sub(r'\$([^$]+)\$\s+([a-zA-Z])\b(?!\s*=)', r'$\1 \2$', text)
    return text


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process(text):
    if not text:
        return text

    # 1. Nuclear notation first (outputs $...$)
    text = fix_nuclear(text)

    # 2. Unicode normalisation (operates only on non-math parts)
    text = apply_to_nonmath(text, apply_unicode)

    # 3. SQRT patterns (non-math parts only)
    text = apply_to_nonmath(text, fix_sqrt)

    # 4. Subscripts (non-math only)
    text = apply_to_nonmath(text, fix_subscripts)

    # 5. Scientific notation (non-math only)
    text = apply_to_nonmath(text, fix_sci_notation)

    # 6. Wrap bare LaTeX commands (non-math only)
    text = apply_to_nonmath(text, wrap_bare_latex)

    # 7. Merge adjacent math blocks
    text = merge_adjacent_math(text)

    # 8. Clean up empty $$ and double $$
    text = re.sub(r'\$\s*\$', '', text)
    text = re.sub(r'\$\$([^$]+?)\$\$', r'$\1$', text)
    # Remove $ that wraps only whitespace
    text = re.sub(r'\$\s+\$', '', text)

    return text


def main():
    data_path = 'src/data/pyq_data.json'
    raw_path  = 'src/data/pyq_data_raw.json'

    # Use original raw backup if available
    src = raw_path if os.path.exists(raw_path) else data_path
    print(f'Loading from {src}')
    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = 0
    for q in data['questions']:
        orig_q = q['question']
        orig_a = q.get('answer')
        q['question'] = process(q['question'])
        if q.get('answer'):
            q['answer'] = process(q['answer'])
        if q['question'] != orig_q or q.get('answer') != orig_a:
            modified += 1

    total = len(data['questions'])
    print(f'Processed {total} questions, modified {modified}')

    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Saved → {data_path}  ({os.path.getsize(data_path)//1024} KB)')

    # Print samples with math
    print('\n── Sample output ──')
    samples = [q for q in data['questions'] if '$' in q['question']][:8]
    for q in samples:
        print(f"  {q['question'][:220]}")
        print()


if __name__ == '__main__':
    main()
