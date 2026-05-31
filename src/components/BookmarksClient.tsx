"use client";

import { useState, useEffect, useMemo } from "react";
import { BookmarkIcon } from "lucide-react";
import type { Question } from "@/types";
import QuestionCard from "@/components/QuestionCard";
import { getBookmarks } from "@/lib/storage";

interface BookmarksClientProps {
  allQuestions: Question[];
}

export default function BookmarksClient({ allQuestions }: BookmarksClientProps) {
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setBookmarkedIds(getBookmarks());
    const handler = () => setBookmarkedIds(getBookmarks());
    window.addEventListener("bookmarks-changed", handler);
    return () => window.removeEventListener("bookmarks-changed", handler);
  }, []);

  const bookmarked = useMemo(
    () => allQuestions.filter((q) => bookmarkedIds.has(q.id)),
    [allQuestions, bookmarkedIds]
  );

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <BookmarkIcon className="h-5 w-5 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Bookmarks</h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          {bookmarked.length} bookmarked question{bookmarked.length !== 1 ? "s" : ""}
        </p>
      </div>

      {bookmarked.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-600">
          <BookmarkIcon className="h-14 w-14 mx-auto mb-3 opacity-20" />
          <p className="text-lg font-medium text-gray-500 dark:text-gray-400">No bookmarks yet</p>
          <p className="text-sm">Click the bookmark icon on any question to save it here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {bookmarked.map((q, i) => (
            <QuestionCard key={q.id} question={q} index={i} showChapter={true} />
          ))}
        </div>
      )}
    </div>
  );
}
