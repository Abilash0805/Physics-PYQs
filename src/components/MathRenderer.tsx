"use client";

import { useEffect, useRef } from "react";

interface MathRendererProps {
  text: string;
  className?: string;
}

export default function MathRenderer({ text, className = "" }: MathRendererProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const renderMath = async () => {
      // Dynamically import KaTeX to avoid SSR issues
      const katex = await import("katex");

      // Process the text to render LaTeX
      let html = text;

      // Replace display math $$...$$
      html = html.replace(/\$\$([^$]+?)\$\$/gs, (_, math) => {
        try {
          return `<span class="math-display block overflow-x-auto my-2">${katex.default.renderToString(math.trim(), { displayMode: true, throwOnError: false })}</span>`;
        } catch {
          return `<span class="math-error">${_}</span>`;
        }
      });

      // Replace inline math $...$
      html = html.replace(/\$([^$\n]+?)\$/g, (_, math) => {
        try {
          return katex.default.renderToString(math.trim(), { displayMode: false, throwOnError: false });
        } catch {
          return `<span class="math-error">${_}</span>`;
        }
      });

      // Replace \(...\) inline math
      html = html.replace(/\\\((.+?)\\\)/gs, (_, math) => {
        try {
          return katex.default.renderToString(math.trim(), { displayMode: false, throwOnError: false });
        } catch {
          return `<span class="math-error">${_}</span>`;
        }
      });

      // Replace \[...\] display math
      html = html.replace(/\\\[(.+?)\\\]/gs, (_, math) => {
        try {
          return `<span class="block overflow-x-auto my-2">${katex.default.renderToString(math.trim(), { displayMode: true, throwOnError: false })}</span>`;
        } catch {
          return `<span class="math-error">${_}</span>`;
        }
      });

      // Convert newlines to <br> for display
      html = html.replace(/\n/g, "<br/>");

      el.innerHTML = html;
    };

    renderMath();
  }, [text]);

  return (
    <div
      ref={ref}
      className={`math-content leading-relaxed ${className}`}
      suppressHydrationWarning
    />
  );
}
