import { notFound } from "next/navigation";
import { getAllChapters, getChapterBySlug, getQuestionsByChapter, getAllYears } from "@/lib/data";
import ChapterQuestions from "@/components/ChapterQuestions";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const chapters = getAllChapters();
  return chapters.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  const chapter = getChapterBySlug(slug);
  return {
    title: chapter ? `${chapter.name} | Physics PYQ` : "Chapter | Physics PYQ",
  };
}

export default async function ChapterPage({ params }: PageProps) {
  const { slug } = await params;
  const chapter = getChapterBySlug(slug);

  if (!chapter) notFound();

  const questions = getQuestionsByChapter(chapter.name);
  const years = getAllYears();

  return <ChapterQuestions chapter={chapter} questions={questions} years={years} />;
}
