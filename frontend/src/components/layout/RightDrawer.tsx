"use client";

import { X, ChevronLeft, ChevronRight, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getFileChunks } from "@/lib/api/files";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function PdfPreview({ target }: { target: { kind: "pdf"; fileId: string; page: number; start: number; end: number } }) {
  const { data, isLoading } = useQuery({
    queryKey: ["file-chunks", target.fileId],
    queryFn: () => getFileChunks(target.fileId, { page: 1, page_size: 100 }),
    enabled: !!target.fileId,
  });

  const relevantChunk = data?.items.find(
    (c) => c.page_number === target.page || (c.start_pos <= target.end && c.end_pos >= target.start)
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-[#6B7280]">
        <span>第 {target.page} 页</span>
        <span>·</span>
        <span>位置 {target.start} - {target.end}</span>
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-[#6B7280]" />
        </div>
      ) : relevantChunk ? (
        <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB]">
          <div className="text-xs text-[#6B7280] mb-2">文件 ID: {target.fileId}</div>
          <div className="p-3 rounded bg-[#FEF08A] text-[#111827] text-sm leading-relaxed">
            {relevantChunk.content.slice(target.start, target.end) || relevantChunk.content}
          </div>
        </div>
      ) : (
        <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[200px] flex items-center justify-center">
          <div className="text-center text-[#6B7280]">
            <FileText className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">PDF 预览区域</p>
            <p className="text-xs mt-1">文件 ID: {target.fileId}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function MarkdownPreview({ target }: { target: { kind: "markdown"; fileId: string; anchorText?: string } }) {
  const { data, isLoading } = useQuery({
    queryKey: ["file-chunks", target.fileId],
    queryFn: () => getFileChunks(target.fileId, { page: 1, page_size: 100 }),
    enabled: !!target.fileId,
  });

  const content = data?.items.map((c) => c.content).join("\n\n") || "";

  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-[#6B7280]" />
        </div>
      ) : content ? (
        <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB]">
          <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-sm max-w-none">
            {content}
          </ReactMarkdown>
          {target.anchorText && (
            <div className="mt-4 p-3 rounded bg-[#FEF08A] text-[#111827] text-sm">
              [高亮] {target.anchorText}
            </div>
          )}
        </div>
      ) : (
        <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[200px] flex items-center justify-center">
          <div className="text-center text-[#6B7280]">
            <FileText className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">Markdown 预览区域</p>
            <p className="text-xs mt-1">文件 ID: {target.fileId}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function ExcelPreview({ target }: { target: { kind: "excel"; fileId: string; sheet: string; rowStart: number; rowEnd: number; colStart: number; colEnd: number } }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-[#6B7280]">
        <span>Sheet: {target.sheet}</span>
        <span>·</span>
        <span>行 {target.rowStart}-{target.rowEnd}, 列 {target.colStart}-{target.colEnd}</span>
      </div>
      <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[200px] flex items-center justify-center">
        <div className="text-center text-[#6B7280]">
          <FileText className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">Excel 预览区域</p>
          <p className="text-xs mt-1">文件 ID: {target.fileId}</p>
        </div>
      </div>
    </div>
  );
}

export function RightDrawer() {
  const { drawerOpen, previewTarget, closeDrawer } = useUIStore();
  const [matchIndex, setMatchIndex] = useState(1);
  const totalMatches = 3;

  useEffect(() => {
    if (drawerOpen) {
      setMatchIndex(1);
    }
  }, [drawerOpen, previewTarget]);

  return (
    <aside
      className={cn(
        "border-l border-[#E5E7EB] bg-white flex flex-col transition-all duration-300 ease-in-out shrink-0",
        drawerOpen ? "w-[380px] opacity-100" : "w-0 opacity-0 overflow-hidden"
      )}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB]">
        <h3 className="text-sm font-semibold text-[#111827] truncate">
          {previewTarget ? "来源文档" : "文档预览"}
        </h3>
        <div className="flex items-center gap-1">
          {drawerOpen && previewTarget && (
            <div className="flex items-center gap-1 mr-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setMatchIndex((i) => Math.max(1, i - 1))}
                disabled={matchIndex <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-xs text-[#6B7280]">
                {matchIndex} / {totalMatches}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setMatchIndex((i) => Math.min(totalMatches, i + 1))}
                disabled={matchIndex >= totalMatches}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={closeDrawer}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        {previewTarget ? (
          <div className="space-y-4">
            {previewTarget.kind === "pdf" && <PdfPreview target={previewTarget} />}
            {previewTarget.kind === "markdown" && <MarkdownPreview target={previewTarget} />}
            {previewTarget.kind === "excel" && <ExcelPreview target={previewTarget} />}

            <div className="pt-4 border-t border-[#E5E7EB]">
              <div className="text-xs text-[#6B7280] space-y-2">
                <div className="flex justify-between">
                  <span>文件 ID</span>
                  <span className="truncate max-w-[200px]">{previewTarget.fileId}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span>类型</span>
                  <Badge variant="secondary" className="text-xs uppercase">{previewTarget.kind}</Badge>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center text-[#6B7280] py-12">
            点击引用角标查看来源文档
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}
