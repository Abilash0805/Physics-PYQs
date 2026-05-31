"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { CheckSquare, BookOpen, TrendingUp } from "lucide-react";
import type { Question, Chapter } from "@/types";
import { getSolved } from "@/lib/storage";
import { cn } from "@/lib/utils";

interface ProgressClientProps {
  allQuestions: Question[];
  chapters: Chapter[];
}

export default function ProgressClient({ allQuestions, chapters }: ProgressClientProps) {
  const [solvedIds, setSolvedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSolvedIds(getSolved());
    const handler = () => setSolvedIds(getSolved());
    window.addEventListener("solved-changed", handler);
    return () => window.removeEventListener("solved-changed", handler);
  }, []);

  const totalSolved = solvedIds.size;
  const totalQuestions = allQuestions.length;
  const pct = totalQuestions > 0 ? Math.round((totalSolved / totalQuestions) * 100) : 0;

  const chapterStats = useMemo(() => {
    return chapters.map((ch) => {
      const chQs = allQuestions.filter((q) => q.chapter === ch.name);
      const solved = chQs.filter((q) => solvedIds.has(q.id)).length;
      return {
        ...ch,
        total: chQs.length,
        solved,
        pct: chQs.length > 0 ? Math.round((solved / chQs.length) * 100) : 0,
      };
    });
  }, [chapters, allQuestions, solvedIds]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="h-5 w-5 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Progress Tracker</h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">Track your practice progress across chapters</p>
      </div>

      {/* Overall progress */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 mb-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Overall Progress</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-1">
              {totalSolved}
              <span className="text-xl text-gray-400 dark:text-gray-500">/{totalQuestions}</span>
            </p>
          </div>
          <div className="w-20 h-20 relative">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" strokeWidth="3"
                className="text-gray-100 dark:text-gray-800" />
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" strokeWidth="3"
                strokeDasharray={`${pct} ${100 - pct}`}
                strokeLinecap="round"
                className="text-blue-600" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{pct}%</span>
            </div>
          </div>
        </div>
        <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Per-chapter progress */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-gray-100">Chapter Progress</h2>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {chapterStats.map((ch) => (
            <Link
              key={ch.slug}
              href={`/chapters/${ch.slug}`}
              className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {ch.name}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0 ml-2">
                    {ch.solved}/{ch.total}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      ch.pct === 100 ? "bg-green-500" :
                      ch.pct > 50 ? "bg-blue-500" :
                      ch.pct > 0 ? "bg-amber-500" : "bg-gray-200"
                    )}
                    style={{ width: `${ch.pct}%` }}
                  />
                </div>
              </div>
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 shrink-0 w-8 text-right">
                {ch.pct}%
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
