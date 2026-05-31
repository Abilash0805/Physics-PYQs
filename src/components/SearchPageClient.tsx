"use client";

import { useState, useMemo, useCallback } from "react";
import { Search } from "lucide-react";
import type { Question, Chapter } from "@/types";
import QuestionCard from "@/components/QuestionCard";
import SearchBar from "@/components/SearchBar";
import FilterBar from "@/components/FilterBar";
import { Button } from "@/components/ui/button";

interface SearchPageClientProps {
  questions: Question[];
  chapters: Chapter[];
  years: number[];
}

const PAGE_SIZE = 15;

export default function SearchPageClient({ questions, chapters, years }: SearchPageClientProps) {
  const [search, setSearch] = useState("");
  const [chapterFilter, setChapterFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [marksFilter, setMarksFilter] = useState("");
  const [page, setPage] = useState(1);
  const [hasSearched, setHasSearched] = useState(false);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    const hasFilter = s || chapterFilter || yearFilter || marksFilter;
    if (!hasFilter) return [];

    let list = questions;
    if (chapterFilter) list = list.filter((q) => q.chapter === chapterFilter);
    if (yearFilter) list = list.filter((q) => String(q.year) === yearFilter);
    if (marksFilter) list = list.filter((q) => String(q.marks) === marksFilter);
    if (s) list = list.filter((q) => q.question.toLowerCase().includes(s));
    return list;
  }, [questions, search, chapterFilter, yearFilter, marksFilter]);

  const paginated = useMemo(() => filtered.slice(0, page * PAGE_SIZE), [filtered, page]);

  const handleSearch = useCallback((v: string) => {
    setSearch(v);
    setPage(1);
    setHasSearched(true);
  }, []);

  const handleClear = useCallback(() => {
    setSearch("");
    setChapterFilter("");
    setYearFilter("");
    setMarksFilter("");
    setPage(1);
    setHasSearched(false);
  }, []);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <Search className="h-5 w-5 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Search Questions</h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          Search across {questions.length.toLocaleString()} questions from all chapters
        </p>
      </div>

      <div className="max-w-3xl">
        <SearchBar
          value={search}
          onChange={handleSearch}
          placeholder="Search by keyword, formula, concept..."
          className="mb-4 text-base"
        />
        <FilterBar
          chapters={chapters}
          years={years}
          selectedChapter={chapterFilter}
          selectedYear={yearFilter}
          selectedMarks={marksFilter}
          onChapterChange={(v) => { setChapterFilter(v); setPage(1); setHasSearched(true); }}
          onYearChange={(v) => { setYearFilter(v); setPage(1); setHasSearched(true); }}
          onMarksChange={(v) => { setMarksFilter(v); setPage(1); setHasSearched(true); }}
          onClear={handleClear}
        />
      </div>

      <div className="mt-6">
        {!hasSearched ? (
          <div className="text-center py-20 text-gray-400 dark:text-gray-600">
            <Search className="h-14 w-14 mx-auto mb-3 opacity-20" />
            <p className="text-lg font-medium text-gray-500 dark:text-gray-400">
              Start searching for questions
            </p>
            <p className="text-sm">Enter keywords or apply filters above</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-lg font-medium text-gray-500 dark:text-gray-400">No results found</p>
            <p className="text-sm text-gray-400 mt-1">Try different keywords or clear some filters</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              {filtered.length.toLocaleString()} result{filtered.length !== 1 ? "s" : ""} found
            </p>
            <div className="space-y-4">
              {paginated.map((q, i) => (
                <QuestionCard key={q.id} question={q} index={i} showChapter={true} />
              ))}
            </div>
            {paginated.length < filtered.length && (
              <div className="mt-6 text-center">
                <Button variant="outline" onClick={() => setPage((p) => p + 1)} className="w-full max-w-xs">
                  Load more ({filtered.length - paginated.length} remaining)
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
