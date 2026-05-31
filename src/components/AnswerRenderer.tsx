"use client";

import MathRenderer from "@/components/MathRenderer";
import { cn } from "@/lib/utils";

interface AnswerRendererProps {
  answer: string;
  marks: number;
}

// Split answer into logical segments for structured display
function parseAnswerSegments(text: string): { type: "option" | "step" | "note" | "formula" | "plain"; content: string; label?: string }[] {
  const segments: { type: "option" | "step" | "note" | "formula" | "plain"; content: string; label?: string }[] = [];

  // Detect MCQ option answer
  const optionMatch = text.match(/^Option\s*\(([A-Da-d])\)\s+is\s+correct\.?\s*/i);
  if (optionMatch) {
    segments.push({ type: "option", content: `Option (${optionMatch[1].toUpperCase()}) is correct`, label: optionMatch[1].toUpperCase() });
    text = text.slice(optionMatch[0].length).trim();
  }

  // Also handle "(c) Some text" style short MCQ answers
  const shortMcqMatch = !optionMatch && text.match(/^\(([A-Da-d])\)\s+(.{0,120})$/i);
  if (shortMcqMatch) {
    segments.push({ type: "option", content: `(${shortMcqMatch[1].toUpperCase()}) ${shortMcqMatch[2]}`, label: shortMcqMatch[1].toUpperCase() });
    return segments;
  }

  if (!text.trim()) return segments;

  // Split by sentence-like boundaries or "Step" patterns
  // Look for: "Step 1:", "(i)", "(ii)", numbered items, "Note:", "Explanation:"
  const stepRegex = /(?:(?:^|\n)(?:Step\s*\d+[:.)]|(?:\(\s*[ivxIVXa-z]+\s*\))|(?:\d+[.)]\s)))/;

  // Check for "Explanation:" prefix
  const explanationMatch = text.match(/^Explanation[:\s]+/i);
  const noteMatch = text.match(/^Note[:\s]+/i);

  if (explanationMatch) {
    text = text.slice(explanationMatch[0].length).trim();
  }

  // Split into steps/parts if they exist
  const parts = text.split(/\n(?=(?:Step\s*\d|(?:\(\s*[ivxIVXa-z]+\s*\))|(?:\d+[.)]\s)))/);

  if (parts.length > 1) {
    parts.forEach((part, idx) => {
      const stepLabel = part.match(/^(Step\s*\d+[:.)]|\(\s*[ivxIVXa-z]+\s*\)|\d+[.)]\s)/i);
      if (stepLabel) {
        segments.push({
          type: "step",
          label: stepLabel[1].trim(),
          content: part.slice(stepLabel[1].length).trim(),
        });
      } else {
        segments.push({ type: "plain", content: part.trim() });
      }
    });
  } else {
    // Single block — try inline step splitting (e.g., "So, Xl = R For CR circuit...")
    // Just render as plain with note detection
    const noteIdx = text.search(/\bNote\s*:/i);
    if (noteIdx > 0) {
      segments.push({ type: "plain", content: text.slice(0, noteIdx).trim() });
      segments.push({ type: "note", content: text.slice(noteIdx + text.slice(noteIdx).match(/^Note\s*:\s*/i)![0].length).trim() });
    } else {
      segments.push({ type: "plain", content: text });
    }
  }

  return segments.filter(s => s.content.trim());
}

export default function AnswerRenderer({ answer, marks }: AnswerRendererProps) {
  const segments = parseAnswerSegments(answer.trim());

  return (
    <div className="space-y-2.5">
      {segments.map((seg, i) => {
        if (seg.type === "option") {
          return (
            <div key={i} className="flex items-center gap-2">
              <span className={cn(
                "inline-flex items-center justify-center h-7 w-7 rounded-full text-sm font-bold shrink-0",
                "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700"
              )}>
                {seg.label}
              </span>
              <span className="text-sm font-semibold text-green-700 dark:text-green-400">Correct Answer</span>
            </div>
          );
        }

        if (seg.type === "step") {
          return (
            <div key={i} className="flex gap-2.5">
              <span className="mt-0.5 shrink-0 inline-flex items-center justify-center h-5 min-w-5 rounded bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 text-xs font-semibold px-1">
                {seg.label}
              </span>
              <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
                <MathRenderer text={seg.content} />
              </div>
            </div>
          );
        }

        if (seg.type === "note") {
          return (
            <div key={i} className="flex items-start gap-1.5 mt-1 px-2.5 py-2 rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
              <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-400 shrink-0 mt-0.5">Note:</span>
              <div className="text-xs text-yellow-800 dark:text-yellow-300 leading-relaxed">
                <MathRenderer text={seg.content} />
              </div>
            </div>
          );
        }

        // plain
        return (
          <div key={i} className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
            <MathRenderer text={seg.content} />
          </div>
        );
      })}

      {marks >= 3 && (
        <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-800/50 flex items-start gap-1.5">
          <span className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 shrink-0">Exam tip:</span>
          <span className="text-xs text-indigo-600 dark:text-indigo-300">
            {marks === 5
              ? "Write each step clearly with formulae. Derive intermediate results and state units."
              : "Show substitution of values and intermediate steps for full marks."}
          </span>
        </div>
      )}
    </div>
  );
}
