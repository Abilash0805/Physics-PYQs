export interface Question {
  id: string;
  chapter: string;
  marks: number;
  year: number;
  question: string;
  answer: string | null;
  bookmarked: boolean;
  solved: boolean;
}

export interface Chapter {
  name: string;
  count: number;
  years: number[];
  marks_dist: Record<string, number>;
  slug: string;
}

export interface PyqData {
  chapters: Chapter[];
  questions: Question[];
  total: number;
  matched_answers: number;
}

export interface FilterState {
  chapter: string;
  year: string;
  marks: string;
  search: string;
}
