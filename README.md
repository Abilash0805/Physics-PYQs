# Physics PYQ — CBSE Class 12

A professional web app for practicing CBSE Class 12 Physics Previous Year Questions, built with Next.js, TypeScript, Tailwind CSS, Framer Motion, and KaTeX.

## Features

- **3,115 questions** extracted from 14 chapter-wise PDFs (2003–2026)
- **Chapter-wise browsing** with question counts and marks distribution
- **Show/Hide answers** with smooth animations
- **Search** across all questions instantly
- **Filter** by chapter, year, and marks
- **Bookmark** questions for later review
- **Progress tracker** — mark questions as solved, track per-chapter progress
- **Dark mode** toggle
- **Math rendering** via KaTeX for equations and formulas
- **Responsive** — works on mobile, tablet, and desktop
- **100% static** — no backend required

## Tech Stack

| Tech | Purpose |
|------|---------|
| Next.js 16 (App Router) | Framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Framer Motion | Animations |
| KaTeX | Math equation rendering |
| Lucide React | Icons |

## Setup

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Data

All question data is pre-extracted from PDFs and embedded in `src/data/pyq_data.json`.

The extraction script is at `/scripts/extract.py` and uses `pymupdf` to parse the PDFs.

### Chapters covered

1. Electric Charges and Fields
2. Electrostatic Potential and Capacitance
3. Current Electricity
4. Moving Charges and Magnetism
5. Magnetism and Matter
6. Electromagnetic Induction
7. Alternating Current
8. Electromagnetic Waves
9. Ray Optics and Optical Instruments
10. Wave Optics
11. Dual Nature of Radiation and Matter
12. Atoms
13. Nuclei
14. Semiconductor Electronics

## Deployment

This app is fully static — deploy to Vercel, Netlify, or any static host:

```bash
npm run build
# Deploy the .next folder or use `next export` for static output
```
