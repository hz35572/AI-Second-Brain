"use client";

import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/api/types";

interface CitationBadgeProps {
  index: number;
  citation?: Citation;
  active?: boolean;
}

export function CitationBadge({ index, citation, active }: CitationBadgeProps) {
  const { openDrawer } = useUIStore();

  if (!citation) {
    return (
      <sup>
        <span
          className={cn(
            "inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded text-[11px] font-medium border ml-0.5",
            active
              ? "bg-[#4F46E5] text-white border-[#4F46E5]"
              : "bg-white text-[#9CA3AF] border-[#E5E7EB]"
          )}
        >
          {index}
        </span>
      </sup>
    );
  }

  const handleClick = () => {
    const mimeType = citation.file_name?.toLowerCase() || "";
    if (mimeType.endsWith(".pdf")) {
      openDrawer({
        kind: "pdf",
        fileId: citation.file_id,
        page: citation.page,
        start: citation.highlight_positions?.start ?? 0,
        end: citation.highlight_positions?.end ?? 100,
      });
    } else if (
      mimeType.endsWith(".xlsx") ||
      mimeType.endsWith(".xls") ||
      mimeType.endsWith(".csv")
    ) {
      if (citation.locator) {
        openDrawer({
          kind: "excel",
          fileId: citation.file_id,
          sheet: (citation.locator as { sheet: string }).sheet || "Sheet1",
          rowStart: (citation.locator as { row_start?: number }).row_start ?? 1,
          rowEnd: (citation.locator as { row_end?: number }).row_end ?? 50,
          colStart: (citation.locator as { col_start?: number }).col_start ?? 1,
          colEnd: (citation.locator as { col_end?: number }).col_end ?? 10,
        });
      }
    } else {
      openDrawer({
        kind: "markdown",
        fileId: citation.file_id,
        anchorText: citation.text,
      });
    }
  };

  return (
    <sup>
      <button
        onClick={handleClick}
        className={cn(
          "inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded text-[11px] font-medium border transition-colors ml-0.5 cursor-pointer",
          active
            ? "bg-[#4F46E5] text-white border-[#4F46E5]"
            : "bg-white text-[#111827] border-[#E5E7EB] hover:border-[#4F46E5] hover:text-[#4F46E5]"
        )}
        title={`${citation.file_name} - 第 ${citation.page} 页`}
      >
        {index}
      </button>
    </sup>
  );
}
