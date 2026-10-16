/**
 * MarkdownView Component
 * High-readability Markdown renderer powered by react-markdown and remark-gfm.
 *
 * Rationale:
 * Transforms raw LLM Markdown (tables, headings, bullet lists, blockquotes, code)
 * into beautifully formatted porcelain typography, matching the clarity of the
 * Midday Meal Ledger notes engine.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewProps {
  content: string;
  className?: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({ content, className = '' }) => {
  // Normalize escaped newlines if any
  const normalizedContent = content ? content.replace(/\\n/g, '\n') : '';

  return (
    <div
      className={`prose prose-stone max-w-none text-ink-primary font-sans leading-relaxed text-sm
        prose-headings:font-serif prose-headings:font-semibold prose-headings:text-ink-primary prose-headings:tracking-tight
        prose-h1:text-xl prose-h1:mt-5 prose-h1:mb-3 prose-h1:border-b prose-h1:border-stone-200 prose-h1:pb-2
        prose-h2:text-lg prose-h2:mt-5 prose-h2:mb-2.5 prose-h2:border-b prose-h2:border-stone-200/80 prose-h2:pb-1.5
        prose-h3:text-base prose-h3:mt-4 prose-h3:mb-2
        prose-h4:text-sm prose-h4:font-semibold prose-h4:mt-3 prose-h4:mb-1.5
        prose-p:my-2 prose-p:leading-relaxed
        prose-table:w-full prose-table:border-collapse prose-table:my-4 prose-table:text-xs sm:prose-table:text-sm
        prose-thead:bg-stone-100/80
        prose-th:border prose-th:border-stone-300 prose-th:p-2.5 prose-th:font-semibold prose-th:text-ink-primary prose-th:text-left
        prose-td:border prose-td:border-stone-200 prose-td:p-2.5 prose-td:text-stone-700
        prose-tr:even:bg-stone-50/50 hover:prose-tr:bg-stone-50 transition-colors
        prose-ul:list-disc prose-ul:pl-5 prose-ul:my-2.5
        prose-ol:list-decimal prose-ol:pl-5 prose-ol:my-2.5
        prose-li:my-1 prose-li:leading-relaxed
        prose-strong:text-ink-primary prose-strong:font-semibold
        prose-em:italic prose-em:text-stone-700
        prose-blockquote:border-l-4 prose-blockquote:border-amber-400 prose-blockquote:bg-amber-50/50 prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:rounded-r-xl prose-blockquote:my-3 prose-blockquote:text-stone-700
        prose-code:text-amber-900 prose-code:bg-stone-100 prose-code:border prose-code:border-stone-200/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-xs prose-code:font-mono
        prose-pre:bg-stone-900 prose-pre:text-stone-100 prose-pre:p-4 prose-pre:rounded-2xl prose-pre:my-3 prose-pre:shadow-xs prose-pre:overflow-x-auto
        prose-hr:my-5 prose-hr:border-stone-200
        ${className}`}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
};
