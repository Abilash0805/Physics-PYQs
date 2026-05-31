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
    'H|B|C|N|O|F|P|S|K|V|W|U|Y|I'
)

def fix_nuclear(text):
    pat = re.compile(r'\b(\d{1,3})\s+(\d{1,2})\s+(' + ELEMENTS + r')\b')
    return pat.sub(
        lambda m: f'${{}}^{{{m.group(1)}}}_{{{m.group(2)}}}\\text{{{m.group(3)}}}$',
        text
    )


# ── Unicode → raw LaTeX (no $ wrapping yet) ───────────────────────────────────

GREEK = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'Γ': r'\Gamma',
    'δ': r'\delta', 'Δ': r'\Delta', 'ε': r'\varepsilon', 'ζ': r'\zeta',
    'η': r'\eta', 'θ': r'\theta', 'Θ': r'\Theta', 'ι': r'\iota',
    'κ': r'\kappa', 'λ': r'\lambda', 'Λ': r'\Lambda', 'μ': r'\mu',
    'µ': r'\mu', 'ν': r'\nu', 'ξ': r'\xi', 'Ξ': r'\Xi', 'π': r'\pi',
    'Π': r'\Pi', 'ρ': r'\rho', 'σ': r'\sigma', 'Σ': r'\Sigma',
    'τ': r'\tau', 'υ': r'\upsilon', 'φ': r'\phi', 'Φ': r'\Phi',
    'χ': r'\chi', 'ψ': r'\psi', 'Ψ': r'\Psi', 'ω': r'\omega', 'Ω': r'\Omega',
}
OPERATORS = {
    '×': r'\times', '÷': r'\div', '≤': r'\leq', '≥': r'\geq',
    '≠': r'\neq', '≈': r'\approx', '∝': r'\propto', '∞': r'\infty',
    '∫': r'\int', '∑': r'\sum', '∂': r'\partial', '∇': r'\nabla',
    '→': r'\rightarrow', '←': r'\leftarrow', '⇒': r'\Rightarrow',
    '°': r'^\circ', '−': '-',
}
SQRT_TOKEN = '__SQRT__'

def apply_unicode(text):
    text = text.replace('√', SQRT_TOKEN)
    for ch, rep in {**GREEK, **OPERATORS}.items():
        text = text.replace(ch, rep)
    return text


# ── SQRT patterns ─────────────────────────────────────────────────────────────

def fix_sqrt(seg):
    # "NUM __SQRT__ NUM"  →  $\frac{NUM}{\sqrt{NUM}}$
    seg = re.sub(
        r'(?<![A-Za-z_$])(\d+(?:\.\d+)?)\s+' + re.escape(SQRT_TOKEN) + r'\s+(\d+(?:\.\d+)?)(?!\d)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\sqrt{{{m.group(2)}}}}}$',
        seg
    )
    # "NUM __SQRT__ WORD" e.g. "1 √ LC"  →  $\frac{NUM}{\sqrt{WORD}}$
    seg = re.sub(
        r'(?<![A-Za-z_$])(\d+(?:\.\d+)?)\s+' + re.escape(SQRT_TOKEN) + r'\s+([A-Za-z][A-Za-z0-9]*)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\sqrt{{{m.group(2)}}}}}$',
        seg
    )
    # "WORD __SQRT__ NUM"  →  $\frac{WORD}{\sqrt{NUM}}$  (e.g. "V0 √ 2")
    seg = re.sub(
        r'([A-Za-z]\w*)\s+' + re.escape(SQRT_TOKEN) + r'\s+(\d+(?:\.\d+)?)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\sqrt{{{m.group(2)}}}}}$',
        seg
    )
    # "__SQRT__ NUM"  →  $\sqrt{NUM}$
    seg = re.sub(
        re.escape(SQRT_TOKEN) + r'\s*(\d+(?:\.\d+)?)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        seg
    )
    # "__SQRT__ WORD"  →  $\sqrt{WORD}$
    seg = re.sub(
        re.escape(SQRT_TOKEN) + r'\s*([A-Za-z][A-Za-z0-9]*)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        seg
    )
    # bare __SQRT__
    seg = seg.replace(SQRT_TOKEN, r'$\sqrt{\cdot}$')
    return seg


# ── Subscripts ────────────────────────────────────────────────────────────────

def fix_subscripts(seg):
    seg = re.sub(r'\bX([LCR])\b', r'$X_{\1}$', seg)
    seg = re.sub(r'\bV([LCR])\b', r'$V_{\1}$', seg)
    seg = re.sub(r'\b([VIEvBbi])0\b', r'$\1_0$', seg)
    seg = re.sub(r'\b([VIEvi])m\b', r'$\1_m$', seg)
    seg = re.sub(r'\b([CLRilrn])([12345])\b', r'$\1_\2$', seg)
    return seg


# ── Scientific notation ───────────────────────────────────────────────────────

def fix_sci_notation(seg):
    # "N \times 10^M" or "N \times 10 M"
    seg = re.sub(
        r'(\d+(?:\.\d+)?)\s*\\times\s*10\s*\^?\s*\{?(-?\d+)\}?',
        lambda m: f'${m.group(1)} \\times 10^{{{m.group(2)}}}$',
        seg
    )
    # "10-N" meaning 10^{-N}
    seg = re.sub(r'\b10-(\d+)\b', lambda m: f'$10^{{-{m.group(1)}}}$', seg)
    # "10^N / denom\pi" patterns
    seg = re.sub(
        r'10\^?\{?(\d+)\}?\s+(\d*)\\pi',
        lambda m: f'$\\frac{{10^{{{m.group(1)}}}}}{{{m.group(2)}\\pi}}$',
        seg
    )
    return seg


# ── Wrap bare LaTeX commands ──────────────────────────────────────────────────

LATEX_CMD_RE = re.compile(
    r'\\(?:alpha|beta|gamma|delta|varepsilon|epsilon|zeta|eta|theta|iota|kappa|'
    r'lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|'
    r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|'
    r'times|div|leq|geq|neq|approx|propto|rightarrow|leftarrow|Rightarrow|'
    r'infty|pm|mp|cdot|partial|nabla|sin|cos|tan|log|ln|exp|'
    r'int|sum|sqrt|frac|circ|text)(?:\{[^}]*\})*'
)

def wrap_bare_latex(seg):
    return LATEX_CMD_RE.sub(lambda m: f'${m.group(0).strip()}$', seg)


# ── Fix fractions: $expr$ DIGIT (denominator) ─────────────────────────────────

def fix_denominator_fractions(text):
    """
    Convert patterns like "$V_0$ 2", "$i_0 v_0$ 2", "$\pi$ 3" to fractions.
    These arise from PDF fraction flattening: A/B extracted as "A B".
    Only apply when the digit appears isolated (followed by space/comma/paren).
    """
    # "$math$ DIGIT" where DIGIT is 2,3,4,6,8 and followed by word boundary
    text = re.sub(
        r'\$([^$]+)\$ (\d)(?=[\s,)(.\n]|$)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{{m.group(2)}}}$',
        text
    )
    return text


# ── Fix $\pi$ N and N$\pi$ M fraction patterns ───────────────────────────────

def fix_pi_fractions(text):
    # "N$\pi$ M" or "N $\pi$ M"  →  "$\frac{N\pi}{M}$"  (run FIRST, more specific)
    text = re.sub(
        r'(\d)\s*\$\\pi\$ (\d+)(?=[\s,)(.;:]|$)',
        lambda m: f'$\\frac{{{m.group(1)}\\pi}}{{{m.group(2)}}}$',
        text
    )
    # "$\pi$ N"  →  "$\frac{\pi}{N}$"
    text = re.sub(
        r'\$\\pi\$ (\d+)(?=[\s,)(.;:]|$)',
        lambda m: f'$\\frac{{\\pi}}{{{m.group(1)}}}$',
        text
    )
    # "$expr$ $\pi$"  →  "$\frac{expr}{\pi}$"  (adjacent math block with pi as denominator)
    text = re.sub(
        r'\$([^$]+)\$ \$\\pi\$(?=[\s,)(.;:]|$)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\pi}}$',
        text
    )
    # "N$\frac{\pi}{M}$"  →  "$\frac{N\pi}{M}$"  (coefficient before pi fraction)
    text = re.sub(
        r'(\d)\$\\frac\{\\pi\}\{(\d+)\}\$',
        lambda m: f'$\\frac{{{m.group(1)}\\pi}}{{{m.group(2)}}}$',
        text
    )
    return text


# ── Fix $\omega$N (superscript) ───────────────────────────────────────────────

def fix_omega_superscript(text):
    # "$\omega$2" meaning ω²
    text = re.sub(r'\$\\omega\$(\d)', lambda m: f'$\\omega^{m.group(1)}$', text)
    # "$\omega$0" as resonant frequency ω₀
    text = re.sub(r'\$\\omega\$0\b', r'$\\omega_0$', text)
    return text


# ── Fix subscripts inside existing math blocks ───────────────────────────────

def fix_subscripts_inside_math(text):
    """Fix V0 → V_0 etc. inside already-formed $...$ blocks."""
    def fix_block(m):
        inner = m.group(1)
        # Variable+digit subscript patterns inside math
        inner = re.sub(r'([A-Za-z])0\b', r'\1_0', inner)
        inner = re.sub(r'([A-Za-z])m\b', r'\1_m', inner)
        return f'${inner}$'
    return re.sub(r'\$([^$]+)\$', fix_block, text)


# ── Fix empty sqrt: "$\sqrt{}$ WORD"  →  "$\sqrt{WORD}$" ────────────────────

def fix_empty_sqrt(text):
    # "$\sqrt{}$ WORD" or "N $\sqrt{}$ WORD"
    text = re.sub(
        r'(\d+) \$\\sqrt\{\}?\$\s*([A-Za-z][A-Za-z0-9]*)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{\\sqrt{{{m.group(2)}}}}}$',
        text
    )
    text = re.sub(
        r'\$\\sqrt\{\}?\$ ([A-Za-z][A-Za-z0-9]*)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        text
    )
    text = re.sub(
        r'\$\\sqrt\{\}\$',
        r'$\\sqrt{\\cdot}$',
        text
    )
    return text


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process(text):
    if not text:
        return text

    # 0. Strip PDF control characters and normalise whitespace
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'  +', ' ', text)

    # 1. Nuclear notation first (outputs $...$)
    text = fix_nuclear(text)

    # 2. Unicode normalisation (non-math only)
    text = apply_to_nonmath(text, apply_unicode)

    # 3. SQRT patterns (non-math only)
    text = apply_to_nonmath(text, fix_sqrt)

    # 4. Subscripts (non-math only)
    text = apply_to_nonmath(text, fix_subscripts)

    # 5. Scientific notation (non-math only)
    text = apply_to_nonmath(text, fix_sci_notation)

    # 6. Wrap bare LaTeX commands (non-math only)
    text = apply_to_nonmath(text, wrap_bare_latex)

    # 7. Fix $expr$ N denominator fractions (whole text - needs $ context)
    text = fix_denominator_fractions(text)

    # 8. Fix $\pi$ N patterns
    text = fix_pi_fractions(text)

    # 9. Fix $\omega$N superscripts
    text = fix_omega_superscript(text)

    # 10. Fix empty $\sqrt{}$ patterns
    text = fix_empty_sqrt(text)

    # 11. Fix subscripts inside math blocks (V0 → V_0 in fractions etc.)
    text = fix_subscripts_inside_math(text)

    # 12. Clean up: remove truly empty math $$ (NOT adjacent blocks)
    text = re.sub(r'\$\$', '', text)     # literal $$ with nothing → remove
    text = re.sub(r'\$ \$', ' ', text)   # "$ $" (space only) → space

    return text


def main():
    data_path = 'src/data/pyq_data.json'
    raw_path  = 'src/data/pyq_data_raw.json'

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

    # Audit
    print('\n── Audit ──')
    qs = data['questions']
    empty_sq = sum(1 for q in qs if r'$\sqrt{}$' in q['question'])
    denom_remaining = sum(1 for q in qs if re.search(r'\$[^$]+\$ \d(?=[\s,).]|$)', q['question']))
    pi_frac = sum(1 for q in qs if re.search(r'\$\\pi\$ \d', q['question']))
    omega_sup = sum(1 for q in qs if re.search(r'\$\\omega\$\d', q['question']))
    odd_dollar = sum(1 for q in qs if q['question'].count('$') % 2 != 0)
    print(f'  Odd dollar signs: {odd_dollar}')
    print(f'  Empty sqrt remaining: {empty_sq}')
    print(f'  $pi$ N fractions: {pi_frac}')
    print(f'  $omega$digit: {omega_sup}')
    print(f'  $expr$ digit (denom): {denom_remaining}')

    print('\n── Samples ──')
    samples = [q for q in qs if '$\\frac' in q['question']][:5]
    for q in samples:
        print(f'  {q["question"][:220]}')
        print()


if __name__ == '__main__':
    main()
