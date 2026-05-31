"use client";

import { useEffect, useRef, memo } from "react";

interface MathRendererProps {
  text: string;
  className?: string;
}

/**
 * Renders a mixed text+LaTeX string.
 * LaTeX segments must be wrapped in $...$ (inline) or $$...$$ (display).
 * Also handles residual Unicode physics symbols not caught by post-processing.
 */
function MathRenderer({ text, className = "" }: MathRendererProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !text) return;

    let cancelled = false;

    (async () => {
      const katex = (await import("katex")).default;

      if (cancelled) return;

      // ── Pre-process any residual Unicode symbols ──────────────────────────
      let processed = text
        // Unicode Greek that slipped through post-processing
        .replace(/ω/g, "$\\omega$")
        .replace(/π/g, "$\\pi$")
        .replace(/α/g, "$\\alpha$")
        .replace(/β/g, "$\\beta$")
        .replace(/γ/g, "$\\gamma$")
        .replace(/Γ/g, "$\\Gamma$")
        .replace(/δ/g, "$\\delta$")
        .replace(/Δ/g, "$\\Delta$")
        .replace(/ε/g, "$\\varepsilon$")
        .replace(/θ/g, "$\\theta$")
        .replace(/λ/g, "$\\lambda$")
        .replace(/μ/g, "$\\mu$")
        .replace(/µ/g, "$\\mu$")
        .replace(/ν/g, "$\\nu$")
        .replace(/ξ/g, "$\\xi$")
        .replace(/ρ/g, "$\\rho$")
        .replace(/σ/g, "$\\sigma$")
        .replace(/τ/g, "$\\tau$")
        .replace(/φ/g, "$\\phi$")
        .replace(/χ/g, "$\\chi$")
        .replace(/ψ/g, "$\\psi$")
        .replace(/Ω/g, "$\\Omega$")
        // Physics units as text
        .replace(/(\d)\s*°/g, "$1^{\\circ}$")
        .replace(/\s*°\s*/g, "$^{\\circ}$")
        // Unicode operators
        .replace(/×/g, "$\\times$")
        .replace(/÷/g, "$\\div$")
        .replace(/→/g, "$\\rightarrow$")
        .replace(/≤/g, "$\\leq$")
        .replace(/≥/g, "$\\geq$")
        .replace(/≠/g, "$\\neq$")
        .replace(/≈/g, "$\\approx$")
        .replace(/∝/g, "$\\propto$")
        .replace(/∞/g, "$\\infty$")
        .replace(/−/g, "-");  // unicode minus → ASCII

      // ── Merge adjacent $ blocks (e.g. "$A$ $B$" with only spaces between) ─
      // Helps display compound expressions as one block
      processed = processed.replace(/\$([^$]+)\$\s*\$([^$]+)\$/g, (_, a, b) => `$${a} ${b}$`);

      // ── Tokenise and render ───────────────────────────────────────────────
      // Split on $...$ and $$...$$ markers
      const DISPLAY_RE = /\$\$([^$]+?)\$\$/gs;
      const INLINE_RE  = /\$([^$\n]+?)\$/g;

      let html = processed;

      // Display math first
      html = html.replace(DISPLAY_RE, (_, math) => {
        try {
          return `<span class="katex-display-block">${katex.renderToString(math.trim(), {
            displayMode: true,
            throwOnError: false,
            trust: false,
          })}</span>`;
        } catch {
          return `<span class="math-error bg-red-50 text-red-500 text-xs px-1 rounded">${_}</span>`;
        }
      });

      // Inline math
      html = html.replace(INLINE_RE, (_, math) => {
        try {
          return katex.renderToString(math.trim(), {
            displayMode: false,
            throwOnError: false,
            trust: false,
          });
        } catch {
          return `<span class="math-error bg-red-50 text-red-500 text-xs px-1 rounded">${_}</span>`;
        }
      });

      // Newlines → line breaks
      html = html.replace(/\n/g, "<br/>");

      if (!cancelled) {
        el.innerHTML = html;
      }
    })();

    return () => { cancelled = true; };
  }, [text]);

  return (
    <div
      ref={ref}
      className={`math-content leading-relaxed ${className}`}
      suppressHydrationWarning
    >
      {/* Show raw text during SSR / before hydration */}
      <span className="sr-only">{text}</span>
    </div>
  );
}

export default memo(MathRenderer);
