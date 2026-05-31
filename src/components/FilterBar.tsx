"use client";

import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import type { Chapter } from "@/types";

interface FilterBarProps {
  chapters?: Chapter[];
  years: number[];
  selectedChapter: string;
  selectedYear: string;
  selectedMarks: string;
  onChapterChange: (v: string) => void;
  onYearChange: (v: string) => void;
  onMarksChange: (v: string) => void;
  onClear: () => void;
  showChapterFilter?: boolean;
}

export default function FilterBar({
  chapters,
  years,
  selectedChapter,
  selectedYear,
  selectedMarks,
  onChapterChange,
  onYearChange,
  onMarksChange,
  onClear,
  showChapterFilter = true,
}: FilterBarProps) {
  const hasFilters = selectedChapter || selectedYear || selectedMarks;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {showChapterFilter && chapters && (
        <Select
          value={selectedChapter}
          onChange={(e) => onChapterChange(e.target.value)}
          className="w-auto min-w-[180px] text-sm"
        >
          <option value="">All Chapters</option>
          {chapters.map((ch) => (
            <option key={ch.slug} value={ch.name}>
              {ch.name}
            </option>
          ))}
        </Select>
      )}

      <Select
        value={selectedYear}
        onChange={(e) => onYearChange(e.target.value)}
        className="w-auto min-w-[120px] text-sm"
      >
        <option value="">All Years</option>
        {years.map((y) => (
          <option key={y} value={String(y)}>
            {y}
          </option>
        ))}
      </Select>

      <Select
        value={selectedMarks}
        onChange={(e) => onMarksChange(e.target.value)}
        className="w-auto min-w-[130px] text-sm"
      >
        <option value="">All Marks</option>
        <option value="1">1 Mark (MCQ)</option>
        <option value="2">2 Marks</option>
        <option value="3">3 Marks</option>
        <option value="4">4 Marks</option>
        <option value="5">5 Marks</option>
      </Select>

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={onClear} className="gap-1 text-muted-foreground">
          <X className="h-3.5 w-3.5" />
          Clear
        </Button>
      )}
    </div>
  );
}
