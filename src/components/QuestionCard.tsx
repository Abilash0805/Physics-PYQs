"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookmarkIcon,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  Lightbulb,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Question } from "@/types";
import MathRenderer from "@/components/MathRenderer";
import AnswerRenderer from "@/components/AnswerRenderer";
import { toggleBookmark, isBookmarked, toggleSolved, isSolved } from "@/lib/storage";

interface QuestionCardProps {
  question: Question;
  index?: number;
  showChapter?: boolean;
}

const MARKS_COLOR: Record<number, string> = {
  1: "blue",
  2: "green",
  3: "purple",
  4: "amber",
  5: "rose",
};

const YEAR_COLORS = [
  "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/20 dark:text-sky-300 dark:border-sky-800",
  "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-900/20 dark:text-violet-300 dark:border-violet-800",
  "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800",
  "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-800",
  "bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-900/20 dark:text-pink-300 dark:border-pink-800",
];

function getYearColor(year: number) {
  return YEAR_COLORS[year % YEAR_COLORS.length];
}

export default function QuestionCard({ question, index = 0, showChapter = true }: QuestionCardProps) {
  const [answerVisible, setAnswerVisible] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [solved, setSolved] = useState(false);

  useEffect(() => {
    setBookmarked(isBookmarked(question.id));
    setSolved(isSolved(question.id));
  }, [question.id]);

  const handleBookmark = () => {
    const next = toggleBookmark(question.id);
    setBookmarked(next);
    window.dispatchEvent(new CustomEvent("bookmarks-changed"));
  };

  const handleSolved = () => {
    const next = toggleSolved(question.id);
    setSolved(next);
    window.dispatchEvent(new CustomEvent("solved-changed"));
  };

  const marksColor = MARKS_COLOR[question.marks] ?? "blue";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.03, 0.5) }}
      className={cn(
        "group relative rounded-xl border bg-white dark:bg-gray-900 shadow-sm hover:shadow-md transition-shadow duration-200",
        solved && "border-green-200 dark:border-green-800",
        bookmarked && !solved && "border-blue-200 dark:border-blue-800"
      )}
    >
      {/* Top accent line */}
      <div className={cn(
        "h-0.5 rounded-t-xl",
        question.marks === 1 ? "bg-blue-500" :
        question.marks === 2 ? "bg-green-500" :
        question.marks === 3 ? "bg-purple-500" :
        question.marks === 5 ? "bg-rose-500" : "bg-amber-500"
      )} />

      <div className="p-5">

        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex flex-wrap items-center gap-2">
            {question.year > 0 && (
              <span className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                getYearColor(question.year)
              )}>
                {question.year}
              </span>
            )}
            <Badge variant={marksColor as "blue" | "green" | "purple" | "amber" | "rose"}>
              {question.marks} {question.marks === 1 ? "Mark" : "Marks"}
            </Badge>
            {showChapter && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                {question.chapter}
              </span>
            )}
            {question.answer && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <Lightbulb className="h-3 w-3" />
                Answer available
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleBookmark}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                bookmarked
                  ? "text-blue-600 bg-blue-50 dark:bg-blue-900/30"
                  : "text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30"
              )}
              title={bookmarked ? "Remove bookmark" : "Bookmark"}
            >
              <BookmarkIcon className="h-4 w-4" fill={bookmarked ? "currentColor" : "none"} />
            </button>
            <button
              onClick={handleSolved}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                solved
                  ? "text-green-600 bg-green-50 dark:bg-green-900/30"
                  : "text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30"
              )}
              title={solved ? "Mark as unsolved" : "Mark as solved"}
            >
              <CheckCircle2 className="h-4 w-4" fill={solved ? "currentColor" : "none"} />
            </button>
          </div>
        </div>

        {/* Question text */}
        <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed mb-4">
          <MathRenderer text={question.question} />
        </div>

        {/* Answer toggle — always shown */}
        <div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAnswerVisible(!answerVisible)}
            className={cn(
              "gap-2 transition-all",
              answerVisible
                ? "bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/20 dark:border-indigo-800 dark:text-indigo-300"
                : "text-gray-600 dark:text-gray-400"
            )}
          >
            {answerVisible ? (
              <>
                <EyeOff className="h-3.5 w-3.5" /> Hide Answer
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5" /> Show Answer
              </>
            )}
            <ChevronDown
              className={cn("h-3.5 w-3.5 transition-transform", answerVisible && "rotate-180")}
            />
          </Button>

          <AnimatePresence>
            {answerVisible && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="mt-3 p-4 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800">
                  {question.answer ? (
                    <>
                      <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-3 uppercase tracking-wide flex items-center gap-1.5">
                        <Lightbulb className="h-3.5 w-3.5" />
                        Exam-Ready Answer
                      </p>
                      <AnswerRenderer answer={question.answer} marks={question.marks} />
                    </>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                      Answer not available — refer to the official CBSE solved paper for this year.
                    </p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
