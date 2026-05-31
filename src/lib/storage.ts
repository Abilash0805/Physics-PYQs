"use client";

const BOOKMARKS_KEY = "pyq_bookmarks";
const SOLVED_KEY = "pyq_solved";

export function getBookmarks(): Set<string> {
  if (typeof window === "undefined") return new Set();
  const raw = localStorage.getItem(BOOKMARKS_KEY);
  return raw ? new Set(JSON.parse(raw)) : new Set();
}

export function toggleBookmark(id: string): boolean {
  const bookmarks = getBookmarks();
  if (bookmarks.has(id)) {
    bookmarks.delete(id);
  } else {
    bookmarks.add(id);
  }
  localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(Array.from(bookmarks)));
  return bookmarks.has(id);
}

export function isBookmarked(id: string): boolean {
  return getBookmarks().has(id);
}

export function getSolved(): Set<string> {
  if (typeof window === "undefined") return new Set();
  const raw = localStorage.getItem(SOLVED_KEY);
  return raw ? new Set(JSON.parse(raw)) : new Set();
}

export function toggleSolved(id: string): boolean {
  const solved = getSolved();
  if (solved.has(id)) {
    solved.delete(id);
  } else {
    solved.add(id);
  }
  localStorage.setItem(SOLVED_KEY, JSON.stringify(Array.from(solved)));
  return solved.has(id);
}

export function isSolved(id: string): boolean {
  return getSolved().has(id);
}
