"use client";

import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";

interface CitationBadgeProps {
  index: number;
  citation: {
    file_id: string;
    file_name: string;
    page: number;
    highlight_positions?: { start: number; end: number };
  };
  active?: boolean;
}

export function CitationBadge({ index, citation, active }: CitationBadgeProps) {
  const { openDrawer } = useUIStore();

  return (
    <sup>
      <button
        onClick={() =>
          openDrawer({
            kind: "pdf",
            fileId: citation.file_id,
            page: citation.page,
            start: citation.highlight_positions?.start ?? 0,
            end: citation.highlight_positions?.end ?? 100,
          })
        }
        className={cn(
          "inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded text-[11px] font-medium border transition-colors ml-0.5",
          active
            ? "bg-[#4F46E5] text-white border-[#4F46E5]"
            : "bg-white text-[#111827] border-[#E5E7EB] hover:border-[#4F46E5] hover:text-[#4F46E5]"
        )}
      >
        {index}
      </button>
    </sup>
  );
}
