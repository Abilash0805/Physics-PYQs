"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BookOpen,
  Home,
  Search,
  BookmarkIcon,
  CheckSquare,
  Atom,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Chapter } from "@/types";

interface SidebarProps {
  chapters: Chapter[];
}

const navItems = [
  { href: "/", icon: Home, label: "Dashboard" },
  { href: "/chapters", icon: BookOpen, label: "All Chapters" },
  { href: "/search", icon: Search, label: "Search" },
  { href: "/bookmarks", icon: BookmarkIcon, label: "Bookmarks" },
  { href: "/progress", icon: CheckSquare, label: "Progress" },
];

export default function Sidebar({ chapters }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-64 shrink-0 h-screen sticky top-0 border-r bg-white dark:bg-gray-950 overflow-hidden">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <Atom className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="font-bold text-sm text-gray-900 dark:text-gray-100">PhysicsPYQ</p>
          <p className="text-xs text-muted-foreground">CBSE Class 12</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="px-3 py-3 border-b">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors mb-0.5",
                active
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Chapter list */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
          Chapters
        </p>
        {chapters.map((chapter, i) => {
          const href = `/chapters/${chapter.slug}`;
          const active = pathname === href;
          return (
            <Link
              key={chapter.slug}
              href={href}
              className={cn(
                "flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition-colors mb-0.5 group",
                active
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
              )}
            >
              <span className="truncate">{chapter.name}</span>
              <span className={cn(
                "text-xs shrink-0 ml-1",
                active ? "text-blue-500" : "text-muted-foreground"
              )}>
                {chapter.count}
              </span>
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
