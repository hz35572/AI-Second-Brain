"use client";

import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";
import { useState } from "react";

function PdfPreview({ target }: { target: { kind: "pdf"; fileId: string; page: number; start: number; end: number } }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-[#6B7280]">
        <span>第 {target.page} 页</span>
        <span>·</span>
        <span>位置 {target.start} - {target.end}</span>
      </div>
      <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[300px]">
        <div className="text-center text-[#6B7280] py-12">
          PDF 预览区域
          <div className="text-xs mt-2">文件 ID: {target.fileId}</div>
        </div>
        <div className="mt-4 p-3 rounded bg-[#FEF08A] text-[#111827] text-sm">
          [高亮区域] 这是被引用的段落内容预览...
        </div>
      </div>
    </div>
  );
}

function MarkdownPreview({ target }: { target: { kind: "markdown"; fileId: string; anchorText?: string } }) {
  return (
    <div className="space-y-4">
      <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[300px]">
        <div className="text-center text-[#6B7280] py-12">
          Markdown 预览区域
          <div className="text-xs mt-2">文件 ID: {target.fileId}</div>
        </div>
        {target.anchorText && (
          <div className="mt-4 p-3 rounded bg-[#FEF08A] text-[#111827] text-sm">
            [高亮] {target.anchorText}
          </div>
        )}
      </div>
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
      <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F9FAFB] min-h-[300px]">
        <div className="text-center text-[#6B7280] py-12">
          Excel 预览区域
          <div className="text-xs mt-2">文件 ID: {target.fileId}</div>
        </div>
      </div>
    </div>
  );
}

export function RightDrawer() {
  const { drawerOpen, previewTarget, closeDrawer } = useUIStore();
  const [matchIndex, setMatchIndex] = useState(1);
  const totalMatches = 3;

  return (
    <aside
      className={cn(
        "border-l border-[#E5E7EB] bg-white flex flex-col transition-all duration-300 ease-in-out",
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
                  <span>上传日期</span>
                  <span>2026-04-20</span>
                </div>
                <div className="flex justify-between">
                  <span>文件大小</span>
                  <span>2.4 MB</span>
                </div>
                <div className="flex items-center gap-2">
                  <span>标签</span>
                  <div className="flex gap-1">
                    <Badge variant="secondary" className="text-xs">研究</Badge>
                    <Badge variant="secondary" className="text-xs">AI</Badge>
                  </div>
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
