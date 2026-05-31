import { getAllChapters } from "@/lib/data";
import ChapterCard from "@/components/ChapterCard";
import { BookOpen } from "lucide-react";

export const metadata = {
  title: "All Chapters | Physics PYQ",
};

export default function ChaptersPage() {
  const chapters = getAllChapters();

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen className="h-5 w-5 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">All Chapters</h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          {chapters.length} chapters · {chapters.reduce((s, c) => s + c.count, 0).toLocaleString()} questions total
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {chapters.map((chapter, i) => (
          <ChapterCard key={chapter.slug} chapter={chapter} index={i} />
        ))}
      </div>
    </div>
  );
}
