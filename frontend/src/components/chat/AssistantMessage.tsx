"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CitationBadge } from "./CitationBadge";
import type { Citation } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface AssistantMessageProps {
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

function parseContentWithCitations(content: string, citations: Citation[] = []) {
  const citationMap = new Map(citations.map((c) => [c.index, c]));
  const parts: Array<{ type: "text"; content: string } | { type: "citation"; index: number }> = [];

  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: "citation", index: parseInt(match[1], 10) });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", content: content.slice(lastIndex) });
  }

  return { parts, citationMap };
}

export function AssistantMessage({ content, citations, streaming }: AssistantMessageProps) {
  parseContentWithCitations(content, citations);

  return (
    <div className={cn("flex gap-3", streaming && "opacity-90")}>
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#4F46E5] flex items-center justify-center">
        <span className="text-white text-xs font-medium">AI</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="prose prose-sm max-w-none text-[#111827]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="mb-3 list-disc pl-5">{children}</ul>,
              ol: ({ children }) => <ol className="mb-3 list-decimal pl-5">{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              code: ({ children }) => (
                <code className="bg-[#F9FAFB] px-1.5 py-0.5 rounded text-sm font-mono border border-[#E5E7EB]">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="bg-[#F9FAFB] p-3 rounded-lg overflow-x-auto border border-[#E5E7EB] mb-3">
                  {children}
                </pre>
              ),
              h1: ({ children }) => <h1 className="text-lg font-semibold mb-3">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-semibold mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold mb-2">{children}</h3>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {citations && citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
            <div className="text-xs text-[#6B7280] mb-2">来源</div>
            <div className="flex flex-wrap gap-2">
              {citations.map((citation) => (
                <CitationBadge
                  key={citation.index}
                  index={citation.index}
                  citation={citation}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
