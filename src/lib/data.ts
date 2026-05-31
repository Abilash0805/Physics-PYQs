import type { PyqData, Question, Chapter } from "@/types";
import rawData from "@/data/pyq_data.json";

const data = rawData as PyqData;

export function getAllQuestions(): Question[] {
  return data.questions;
}

export function getAllChapters(): Chapter[] {
  return data.chapters;
}

export function getChapterBySlug(slug: string): Chapter | undefined {
  return data.chapters.find((c) => c.slug === slug);
}

export function getQuestionsByChapter(chapterName: string): Question[] {
  return data.questions.filter((q) => q.chapter === chapterName);
}

export function getQuestionById(id: string): Question | undefined {
  return data.questions.find((q) => q.id === id);
}

export function getAllYears(): number[] {
  const years = new Set<number>();
  data.questions.forEach((q) => {
    if (q.year) years.add(q.year);
  });
  return Array.from(years).sort((a, b) => b - a);
}

export function getStats() {
  const total = data.total;
  const chapters = data.chapters.length;
  const withAnswers = data.matched_answers;
  const years = getAllYears();
  return {
    total,
    chapters,
    withAnswers,
    yearRange: years.length > 0 ? `${years[years.length - 1]}–${years[0]}` : "",
  };
}
