"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { BookOpen, ChevronRight } from "lucide-react";
import type { Chapter } from "@/types";
import { cn } from "@/lib/utils";

interface ChapterCardProps {
  chapter: Chapter;
  index: number;
}

const CHAPTER_ICONS: Record<string, string> = {
  "Electric Charges and Fields": "⚡",
  "Electrostatic Potential and Capacitance": "🔋",
  "Current Electricity": "💡",
  "Moving Charges and Magnetism": "🧲",
  "Magnetism and Matter": "🔮",
  "Electromagnetic Induction": "🌊",
  "Alternating Current": "〰️",
  "Electromagnetic Waves": "📡",
  "Ray Optics and Optical Instruments": "🔭",
  "Wave Optics": "🌈",
  "Dual Nature of Radiation and Matter": "⚛️",
  "Atoms": "🔬",
  "Nuclei": "☢️",
  "Semiconductor Electronics": "💻",
};

const CHAPTER_COLORS = [
  "from-blue-500 to-blue-600",
  "from-violet-500 to-violet-600",
  "from-emerald-500 to-emerald-600",
  "from-amber-500 to-amber-600",
  "from-rose-500 to-rose-600",
  "from-cyan-500 to-cyan-600",
  "from-indigo-500 to-indigo-600",
  "from-teal-500 to-teal-600",
  "from-orange-500 to-orange-600",
  "from-pink-500 to-pink-600",
  "from-sky-500 to-sky-600",
  "from-lime-500 to-lime-600",
  "from-red-500 to-red-600",
  "from-purple-500 to-purple-600",
];

export default function ChapterCard({ chapter, index }: ChapterCardProps) {
  const icon = CHAPTER_ICONS[chapter.name] ?? "📚";
  const gradient = CHAPTER_COLORS[index % CHAPTER_COLORS.length];
  const yearRange = chapter.years.length > 0
    ? `${Math.min(...chapter.years)}–${Math.max(...chapter.years)}`
    : "";

  const marks1 = chapter.marks_dist["1"] ?? 0;
  const marks2 = chapter.marks_dist["2"] ?? 0;
  const marks3 = chapter.marks_dist["3"] ?? 0;
  const marks5 = chapter.marks_dist["5"] ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
    >
      <Link href={`/chapters/${chapter.slug}`} className="block group">
        <div className="rounded-xl border bg-white dark:bg-gray-900 shadow-sm hover:shadow-lg transition-all duration-200 hover:-translate-y-1 overflow-hidden">
          {/* Gradient header */}
          <div className={cn("h-1.5 bg-gradient-to-r", gradient)} />

          <div className="p-5">
            {/* Icon + title */}
            <div className="flex items-start gap-3 mb-4">
              <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center text-xl shrink-0 bg-gradient-to-br",
                gradient
              )}>
                {icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm leading-snug group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {chapter.name}
                </h3>
                {yearRange && (
                  <p className="text-xs text-muted-foreground mt-0.5">{yearRange}</p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-blue-500 transition-colors shrink-0 mt-1" />
            </div>

            {/* Stats */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  {chapter.count}
                </span>
                <span className="text-xs text-muted-foreground">questions</span>
              </div>

              {/* Marks breakdown */}
              <div className="flex items-center gap-1">
                {marks1 > 0 && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded-full">
                    {marks1}×1m
                  </span>
                )}
                {marks2 > 0 && (
                  <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-1.5 py-0.5 rounded-full">
                    {marks2}×2m
                  </span>
                )}
                {marks3 > 0 && (
                  <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-1.5 py-0.5 rounded-full">
                    {marks3}×3m
                  </span>
                )}
                {marks5 > 0 && (
                  <span className="text-xs bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 px-1.5 py-0.5 rounded-full">
                    {marks5}×5m
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
