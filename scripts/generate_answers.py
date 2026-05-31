#!/usr/bin/env python3
"""
Generate exam-ready answers for all questions missing answers.
Uses the claude CLI in batch mode.
Collects all answers in memory, writes pyq_data.json only once at the end.
"""
import json, subprocess, sys, time, re

DATA_PATH = 'src/data/pyq_data.json'
BATCH_SIZE = 8

def call_claude(prompt: str) -> str:
    result = subprocess.run(
        ['claude', '-p', prompt, '--output-format', 'text'],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude error: {result.stderr[:200]}")
    return result.stdout.strip()

def make_prompt(questions: list) -> str:
    lines = [
        "You are a CBSE Class 12 Physics expert. For each 1-mark MCQ below, provide the correct answer.",
        "",
        "Rules:",
        "- State the correct option like: (D) qE0x — is correct.",
        "- Add 1 sentence of reasoning with the key concept or formula.",
        "- Use LaTeX math in $...$ delimiters (e.g. $KE = qE_0x$).",
        "- Keep each answer under 50 words.",
        "- Output ONLY a raw JSON array (no markdown fences): [{\"id\": \"...\", \"answer\": \"...\"}]",
        "",
    ]
    for q in questions:
        lines.append(f'ID: {q["id"]}')
        lines.append(f'Chapter: {q["chapter"]}')
        lines.append(f'Q: {q["question"]}')
        lines.append("")
    return '\n'.join(lines)

def parse_response(text: str) -> list:
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text.strip())

def main():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing = [q for q in data['questions'] if q.get('in_syllabus', True) and not q.get('answer')]
    print(f"Questions needing answers: {len(missing)}")

    q_by_id = {q['id']: q for q in data['questions']}
    answers_collected = {}
    total_batches = (len(missing) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch = missing[batch_num * BATCH_SIZE:(batch_num + 1) * BATCH_SIZE]
        print(f"Batch {batch_num+1}/{total_batches} ({len(batch)} questions)...", end=' ', flush=True)

        for attempt in range(3):
            try:
                prompt = make_prompt(batch)
                response = call_claude(prompt)
                items = parse_response(response)
                for item in items:
                    if item.get('id') and item.get('answer'):
                        answers_collected[item['id']] = item['answer'].strip()
                print(f"OK ({len(items)} answers, total {len(answers_collected)})")
                break
            except Exception as e:
                print(f"attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(4 * (attempt + 1))
                else:
                    print(f"  SKIPPED batch {batch_num+1}")

    # Apply all answers at once
    applied = 0
    for qid, ans in answers_collected.items():
        if qid in q_by_id:
            q_by_id[qid]['answer'] = ans
            applied += 1

    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Applied {applied} answers. Saved to {DATA_PATH}")

if __name__ == '__main__':
    main()
