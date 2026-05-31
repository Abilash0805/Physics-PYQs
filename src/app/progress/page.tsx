import ProgressClient from "@/components/ProgressClient";
import { getAllQuestions, getAllChapters } from "@/lib/data";

export const metadata = { title: "Progress | Physics PYQ" };

export default function ProgressPage() {
  const questions = getAllQuestions();
  const chapters = getAllChapters();
  return <ProgressClient allQuestions={questions} chapters={chapters} />;
}
