import Link from "next/link";
import { getAllChapters, getStats } from "@/lib/data";
import ChapterCard from "@/components/ChapterCard";
import { BookOpen, Zap, Award, Clock } from "lucide-react";

export default function HomePage() {
  const chapters = getAllChapters();
  const stats = getStats();

  const statCards = [
    { icon: BookOpen, label: "Total Questions", value: stats.total.toLocaleString(), color: "blue" },
    { icon: Zap, label: "Chapters", value: stats.chapters, color: "violet" },
    { icon: Award, label: "With Answers", value: stats.withAnswers.toLocaleString(), color: "emerald" },
    { icon: Clock, label: "Year Range", value: stats.yearRange, color: "amber" },
  ];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          CBSE Class 12 Physics
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-3">
          Previous Year Questions
        </h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 max-w-2xl">
          Master Class 12 Physics with chapter-wise PYQs from 2003–2026.
          Practice smarter with answers, solutions, and progress tracking.
        </p>
        <div className="flex flex-wrap gap-3 mt-5">
          <Link
            href="/chapters"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <BookOpen className="h-4 w-4" />
            Browse Chapters
          </Link>
          <Link
            href="/search"
            className="inline-flex items-center gap-2 px-5 py-2.5 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg transition-colors"
          >
            Search Questions
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {statCards.map((stat) => (
          <div key={stat.label} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
            <div className={`w-9 h-9 rounded-lg mb-3 flex items-center justify-center ${
              stat.color === "blue" ? "bg-blue-100 dark:bg-blue-900/30" :
              stat.color === "violet" ? "bg-violet-100 dark:bg-violet-900/30" :
              stat.color === "emerald" ? "bg-emerald-100 dark:bg-emerald-900/30" :
              "bg-amber-100 dark:bg-amber-900/30"
            }`}>
              <stat.icon className={`h-5 w-5 ${
                stat.color === "blue" ? "text-blue-600 dark:text-blue-400" :
                stat.color === "violet" ? "text-violet-600 dark:text-violet-400" :
                stat.color === "emerald" ? "text-emerald-600 dark:text-emerald-400" :
                "text-amber-600 dark:text-amber-400"
              }`} />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stat.value}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Chapters grid */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Browse by Chapter</h2>
          <Link href="/chapters" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
            View all →
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {chapters.map((chapter, i) => (
            <ChapterCard key={chapter.slug} chapter={chapter} index={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
