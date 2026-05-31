#!/usr/bin/env python3
import fitz
import re
import json
import os
from pathlib import Path

PDFS_DIR = Path('/tmp/pyqs/1PYQs')

CHAPTER_MAP = {
    'alternating-current': 'Alternating Current',
    'atoms': 'Atoms',
    'current-electricity': 'Current Electricity',
    'dual-nature': 'Dual Nature of Radiation and Matter',
    'electric-charges-and-fields': 'Electric Charges and Fields',
    'electromagnetic-induction': 'Electromagnetic Induction',
    'electromagnetic-waves': 'Electromagnetic Waves',
    'electrostatic-potential': 'Electrostatic Potential and Capacitance',
    'magnetism-and-matter': 'Magnetism and Matter',
    'moving-charges-and-magnetism': 'Moving Charges and Magnetism',
    'nuclei': 'Nuclei',
    'ray-optics': 'Ray Optics and Optical Instruments',
    'semiconductor-electronics': 'Semiconductor Electronics',
    'wave-optics': 'Wave Optics',
}

CHAPTER_ORDER = [
    'Electric Charges and Fields',
    'Electrostatic Potential and Capacitance',
    'Current Electricity',
    'Moving Charges and Magnetism',
    'Magnetism and Matter',
    'Electromagnetic Induction',
    'Alternating Current',
    'Electromagnetic Waves',
    'Ray Optics and Optical Instruments',
    'Wave Optics',
    'Dual Nature of Radiation and Matter',
    'Atoms',
    'Nuclei',
    'Semiconductor Electronics',
]


def clean_text(text):
    """Remove PDF artifacts and clean text"""
    # Remove page headers/footers
    text = re.sub(r'Collegedunia \| Class 12 Physics\s*\nChapter[^\n]*\n', '', text)
    text = re.sub(r'Previous Year Questions • Free download at collegedunia\.com\s*\nPage \d+', '', text)
    text = re.sub(r'\nPage \d+\s*\n', '\n', text)
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_chapter_questions(pdf_path, chapter_name):
    """Extract questions from a chapter-wise PDF"""
    doc = fitz.open(str(pdf_path))
    full_text = ''
    for page in doc:
        full_text += page.get_text() + '\n'

    full_text = clean_text(full_text)

    questions = []
    year_pat = re.compile(r'\[(\d{4})(?:\s*[•·][^\]]+)?\]')
    marks_section_pat = re.compile(r'(\d+)-Mark Questions', re.IGNORECASE)

    # Split into lines for easier processing
    lines = full_text.split('\n')

    current_marks = 1
    q_id = 1
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect marks section
        mm = marks_section_pat.search(line)
        if mm:
            current_marks = int(mm.group(1))
            i += 1
            continue

        # Detect question start
        qm = re.match(r'^Q(\d+)\.\s+(.*)', line)
        if qm:
            q_num = int(qm.group(1))
            q_lines = [qm.group(2)]
            i += 1

            # Collect until next question or end
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r'^Q\d+\.', next_line):
                    break
                q_lines.append(next_line)
                i += 1

            q_full = '\n'.join(q_lines).strip()

            # Extract year
            year_match = year_pat.search(q_full)
            year = int(year_match.group(1)) if year_match else None

            # Remove year tag from question text
            q_text = year_pat.sub('', q_full).strip()
            q_text = re.sub(r'\s+', ' ', q_text).strip()
            # Remove trailing/leading artifacts
            q_text = re.sub(r'^[\s\n]+|[\s\n]+$', '', q_text)

            if q_text and len(q_text) > 15:
                questions.append({
                    'id': f'{chapter_name.lower().replace(" ", "-")}-{q_id}',
                    'chapter': chapter_name,
                    'marks': current_marks,
                    'year': year or 0,
                    'question': q_text,
                    'answer': None,
                    'bookmarked': False,
                    'solved': False,
                })
                q_id += 1
        else:
            i += 1

    return questions


def extract_solved_paper(pdf_path, year):
    """Extract Q&A pairs from a solved paper PDF"""
    doc = fitz.open(str(pdf_path))
    full_text = ''
    for page in doc:
        full_text += page.get_text() + '\n'

    pairs = []
    lines = full_text.split('\n')

    # Pattern: question number then text, then Ans. answer
    q_pat = re.compile(r'^\s*(\d+)\.\s+(.*)')
    ans_pat = re.compile(r'^\s*Ans\.\s*(.*)')

    i = 0
    while i < len(lines):
        line = lines[i]
        qm = q_pat.match(line)
        if qm:
            q_num = int(qm.group(1))
            if 1 <= q_num <= 35:  # CBSE paper has up to 35 questions
                q_lines = [qm.group(2)]
                i += 1
                ans_text = ''

                # Collect question lines until Ans. or next question
                while i < len(lines):
                    l = lines[i].strip()
                    if ans_pat.match(lines[i]):
                        break
                    if q_pat.match(lines[i]) and int(q_pat.match(lines[i]).group(1)) == q_num + 1:
                        break
                    q_lines.append(l)
                    i += 1

                # Now try to get answer
                if i < len(lines) and ans_pat.match(lines[i]):
                    am = ans_pat.match(lines[i])
                    ans_lines = [am.group(1)]
                    i += 1
                    while i < len(lines):
                        l = lines[i].strip()
                        if q_pat.match(lines[i]) or (l and re.match(r'^\d+\.$', l.split()[0] if l.split() else '')):
                            break
                        ans_lines.append(l)
                        i += 1
                    ans_text = ' '.join(ans_lines).strip()
                    ans_text = re.sub(r'\s+', ' ', ans_text)

                q_text = ' '.join(q_lines).strip()
                q_text = re.sub(r'\s+', ' ', q_text)

                if q_text and len(q_text) > 10:
                    pairs.append({
                        'year': year,
                        'q_num': q_num,
                        'question': q_text,
                        'answer': ans_text if ans_text else None,
                    })
            else:
                i += 1
        else:
            i += 1

    return pairs


def normalize(text):
    """Normalize text for matching"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def match_answers(chapter_questions, solved_pairs):
    """Try to match answers to chapter questions"""
    # Build lookup: (year, normalized_q_text[:80]) -> answer
    solved_lookup = {}
    for p in solved_pairs:
        if p['answer']:
            key = (p['year'], normalize(p['question'])[:80])
            solved_lookup[key] = p['answer']

    for q in chapter_questions:
        key = (q['year'], normalize(q['question'])[:80])
        if key in solved_lookup:
            q['answer'] = solved_lookup[key]

    return chapter_questions


def main():
    all_questions = []

    # Extract from chapter PDFs
    chapter_files = sorted(PDFS_DIR.glob('class-12-physics-*.pdf'))
    print(f"Found {len(chapter_files)} chapter PDFs")

    for pdf_path in chapter_files:
        name = pdf_path.stem
        # Determine chapter name from filename
        chapter_name = None
        for key, val in CHAPTER_MAP.items():
            if key in name:
                chapter_name = val
                break

        if not chapter_name:
            # Fallback: parse from filename
            parts = name.replace('class-12-physics-', '').replace('-pyq-1779702121', '').replace('-pyq-1779702122', '').replace('-pyq-1779702123', '').replace('-pyq-1779702124', '').replace('-pyq-1779702125', '').replace('-pyq-1779702126', '').replace('-pyq-1779702127', '')
            chapter_name = parts.replace('-', ' ').title()

        print(f"  Extracting: {chapter_name}")
        qs = extract_chapter_questions(pdf_path, chapter_name)
        print(f"    -> {len(qs)} questions")
        all_questions.extend(qs)

    print(f"\nTotal questions from chapters: {len(all_questions)}")

    # Extract from solved papers
    solved_year_map = {
        'Solved Paper 2013.pdf': 2013,
        'Solved Paper 2014.pdf': 2014,
        'Solved Paper 2015.pdf': 2015,
        'Solved Paper 2016.pdf': 2016,
        'Solved Paper 2017.pdf': 2017,
        'Solved Paper 2018.pdf': 2018,
        'Solved Paper 2019.pdf': 2019,
        'Solved Paper 2022 Term I.pdf': 2022,
        'Solved Paper 2022 Term II.pdf': 2022,
        'Solved Paper 2023.pdf': 2023,
        'Physics 2020.pdf': 2020,
        'Physics 2025.pdf': 2025,
    }

    all_solved = []
    print("\nExtracting solved papers:")
    for fname, year in sorted(solved_year_map.items()):
        fpath = PDFS_DIR / fname
        if fpath.exists():
            pairs = extract_solved_paper(fpath, year)
            print(f"  {fname}: {len(pairs)} Q&A pairs")
            all_solved.extend(pairs)

    print(f"\nTotal solved Q&A pairs: {len(all_solved)}")

    # Match answers
    all_questions = match_answers(all_questions, all_solved)
    matched = sum(1 for q in all_questions if q['answer'])
    print(f"Matched answers: {matched}/{len(all_questions)}")

    # Build chapter summary
    chapters = {}
    for q in all_questions:
        ch = q['chapter']
        if ch not in chapters:
            chapters[ch] = {'name': ch, 'count': 0, 'years': set(), 'marks_dist': {}}
        chapters[ch]['count'] += 1
        chapters[ch]['years'].add(q['year'])
        m = str(q['marks'])
        chapters[ch]['marks_dist'][m] = chapters[ch]['marks_dist'].get(m, 0) + 1

    # Convert sets to lists for JSON
    chapters_list = []
    for ch_name in CHAPTER_ORDER:
        if ch_name in chapters:
            ch = chapters[ch_name]
            chapters_list.append({
                'name': ch_name,
                'count': ch['count'],
                'years': sorted(ch['years']),
                'marks_dist': ch['marks_dist'],
                'slug': ch_name.lower().replace(' ', '-').replace(',', '').replace('/', '-')
            })

    # Add any missing chapters
    for ch_name, ch in chapters.items():
        if ch_name not in CHAPTER_ORDER:
            chapters_list.append({
                'name': ch_name,
                'count': ch['count'],
                'years': sorted(ch['years']),
                'marks_dist': ch['marks_dist'],
                'slug': ch_name.lower().replace(' ', '-').replace(',', '').replace('/', '-')
            })

    output = {
        'chapters': chapters_list,
        'questions': all_questions,
        'total': len(all_questions),
        'matched_answers': matched,
    }

    out_path = '/tmp/pyqs/pyq_data.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {out_path}")
    print(f"File size: {os.path.getsize(out_path) / 1024:.1f} KB")

    # Print sample
    print("\nSample questions:")
    for q in all_questions[:3]:
        print(f"  [{q['chapter']}] [{q['year']}] [{q['marks']}m] {q['question'][:80]}...")
        if q['answer']:
            print(f"    ANS: {q['answer'][:60]}...")

if __name__ == '__main__':
    main()
