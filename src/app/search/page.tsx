import SearchPageClient from "@/components/SearchPageClient";
import { getAllQuestions, getAllChapters, getAllYears } from "@/lib/data";

export const metadata = { title: "Search | Physics PYQ" };

export default function SearchPage() {
  const questions = getAllQuestions();
  const chapters = getAllChapters();
  const years = getAllYears();

  return <SearchPageClient questions={questions} chapters={chapters} years={years} />;
}
