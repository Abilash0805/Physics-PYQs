"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, AlertTriangle } from "lucide-react";
import type { Chapter, Question } from "@/types";
import QuestionCard from "@/components/QuestionCard";
import SearchBar from "@/components/SearchBar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChapterQuestionsProps {
  chapter: Chapter;
  questions: Question[];
  years: number[];
}

const MARKS_TABS = [
  { value: "", label: "All" },
  { value: "1", label: "1 Mark" },
  { value: "2", label: "2 Marks" },
  { value: "3", label: "3 Marks" },
  { value: "5", label: "5 Marks" },
];

const PAGE_SIZE = 20;

export default function ChapterQuestions({ chapter, questions, years }: ChapterQuestionsProps) {
  const [search, setSearch] = useState("");
  const [marksFilter, setMarksFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showOutOfSyllabus, setShowOutOfSyllabus] = useState(false);

  const chapterYears = useMemo(
    () => chapter.years.slice().sort((a, b) => b - a),
    [chapter.years]
  );

  const outOfSyllabusCount = useMemo(
    () => questions.filter((q) => q.in_syllabus === false).length,
    [questions]
  );

  const filtered = useMemo(() => {
    let list = showOutOfSyllabus
      ? questions
      : questions.filter((q) => q.in_syllabus !== false);
    if (marksFilter) list = list.filter((q) => String(q.marks) === marksFilter);
    if (yearFilter) list = list.filter((q) => String(q.year) === yearFilter);
    if (search.trim()) {
      const s = search.toLowerCase();
      list = list.filter((q) => q.question.toLowerCase().includes(s));
    }
    return list;
  }, [questions, marksFilter, yearFilter, search, showOutOfSyllabus]);

  const paginated = useMemo(
    () => filtered.slice(0, page * PAGE_SIZE),
    [filtered, page]
  );

  const handleClear = useCallback(() => {
    setSearch("");
    setMarksFilter("");
    setYearFilter("");
    setPage(1);
  }, []);

  const inSyllabusCount = questions.length - outOfSyllabusCount;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6">
      {/* Back + header */}
      <div className="mb-6">
        <Link
          href="/chapters"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All Chapters
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              {chapter.name}
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <BookOpen className="h-3.5 w-3.5" />
                {inSyllabusCount} in-syllabus questions
              </span>
              {outOfSyllabusCount > 0 && (
                <span className="text-amber-600 dark:text-amber-500">
                  +{outOfSyllabusCount} removed from syllabus
                </span>
              )}
              {chapter.years.length > 0 && (
                <span>{Math.min(...chapter.years)}–{Math.max(...chapter.years)}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Sticky filter area */}
      <div className="sticky top-14 z-30 bg-gray-50 dark:bg-gray-950 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 border-b border-gray-200 dark:border-gray-800 mb-6">
        <SearchBar
          value={search}
          onChange={(v) => { setSearch(v); setPage(1); }}
          placeholder={`Search in ${chapter.name}...`}
          className="mb-3"
        />

        {/* Marks tabs + year filter */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1">
          {MARKS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => { setMarksFilter(tab.value); setPage(1); }}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors shrink-0",
                marksFilter === tab.value
                  ? "bg-blue-600 text-white"
                  : "bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
              )}
            >
              {tab.label}
              {tab.value && (
                <span className="ml-1 opacity-60">
                  ({chapter.marks_dist[tab.value] ?? 0})
                </span>
              )}
            </button>
          ))}

          <div className="ml-2 shrink-0">
            <select
              value={yearFilter}
              onChange={(e) => { setYearFilter(e.target.value); setPage(1); }}
              className="h-8 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-xs px-2 text-gray-700 dark:text-gray-300"
            >
              <option value="">All Years</option>
              {chapterYears.map((y) => (
                <option key={y} value={String(y)}>{y}</option>
              ))}
            </select>
          </div>

          {/* Out-of-syllabus toggle */}
          {outOfSyllabusCount > 0 && (
            <button
              onClick={() => { setShowOutOfSyllabus(!showOutOfSyllabus); setPage(1); }}
              className={cn(
                "ml-2 shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                showOutOfSyllabus
                  ? "bg-amber-100 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400"
                  : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-amber-50 dark:hover:bg-amber-900/20"
              )}
            >
              <AlertTriangle className="h-3 w-3" />
              {showOutOfSyllabus ? "Hide removed" : `Show +${outOfSyllabusCount} removed`}
            </button>
          )}
        </div>
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {filtered.length === (showOutOfSyllabus ? questions.length : inSyllabusCount)
            ? `${filtered.length} questions`
            : `${filtered.length} of ${showOutOfSyllabus ? questions.length : inSyllabusCount} questions`}
        </p>
        {(search || marksFilter || yearFilter) && (
          <button
            onClick={handleClear}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Question list */}
      {paginated.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-600">
          <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">No questions found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="space-y-4">
          {paginated.map((q, i) => (
            <QuestionCard key={q.id} question={q} index={i} showChapter={false} />
          ))}
        </div>
      )}

      {/* Load more */}
      {paginated.length < filtered.length && (
        <div className="mt-6 text-center">
          <Button
            variant="outline"
            onClick={() => setPage((p) => p + 1)}
            className="w-full max-w-xs"
          >
            Load more ({filtered.length - paginated.length} remaining)
          </Button>
        </div>
      )}
    </div>
  );
}
