import BookmarksClient from "@/components/BookmarksClient";
import { getAllQuestions } from "@/lib/data";

export const metadata = { title: "Bookmarks | Physics PYQ" };

export default function BookmarksPage() {
  const questions = getAllQuestions();
  return <BookmarksClient allQuestions={questions} />;
}
