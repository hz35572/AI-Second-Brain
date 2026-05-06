"use client";

import { useState, useRef, useCallback } from "react";
import {
  FolderOpen,
  Upload,
  Grid3X3,
  List,
  Search,
  MoreVertical,
  FileText,
  Image,
  Table,
  ChevronRight,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { FileItem } from "@/lib/api/types";

const mockFiles: FileItem[] = [
  {
    id: "1",
    name: "研究论文.pdf",
    file_size: 2457600,
    mime_type: "application/pdf",
    page_count: 50,
    summary: "关于 Transformer 注意力机制的改进研究",
    tags: ["AI", "研究"],
    status: "ready",
    created_at: "2026-04-20T10:00:00Z",
  },
  {
    id: "2",
    name: "会议纪要.docx",
    file_size: 512000,
    mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    summary: "第三季度预算讨论会议纪要",
    tags: ["会议", "预算"],
    status: "ready",
    created_at: "2026-04-22T14:30:00Z",
  },
  {
    id: "3",
    name: "数据分析.xlsx",
    file_size: 1048576,
    mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    summary: "用户行为数据分析报表",
    tags: ["数据", "分析"],
    status: "parsing",
    created_at: "2026-04-25T09:00:00Z",
  },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon({ mimeType }: { mimeType: string }) {
  if (mimeType.includes("pdf")) return <FileText className="h-8 w-8 text-red-500" aria-label="PDF" />;
  if (mimeType.includes("spreadsheet") || mimeType.includes("excel"))
    return <Table className="h-8 w-8 text-green-500" aria-label="Spreadsheet" />;
  if (mimeType.includes("image")) return <Image className="h-8 w-8 text-blue-500" aria-label="Image" />;
  return <FileText className="h-8 w-8 text-[#6B7280]" aria-label="File" />;
}

function StatusBadge({ status }: { status: FileItem["status"] }) {
  const config = {
    ready: { label: "已完成", className: "bg-green-50 text-green-700 border-green-200" },
    pending: { label: "待处理", className: "bg-yellow-50 text-yellow-700 border-yellow-200" },
    parsing: { label: "处理中", className: "bg-yellow-50 text-yellow-700 border-yellow-200" },
    failed: { label: "失败", className: "bg-red-50 text-red-700 border-red-200" },
  };
  const c = config[status];
  return (
    <Badge variant="outline" className={cn("text-xs", c.className)}>
      {c.label}
    </Badge>
  );
}

export default function FilesPage() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [files] = useState<FileItem[]>(mockFiles);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [folderName, setFolderName] = useState("");

  const filteredFiles = files.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      console.log("Dropped files:", droppedFiles.map((f) => f.name));
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files ? Array.from(e.target.files) : [];
    if (selectedFiles.length > 0) {
      console.log("Selected files:", selectedFiles.map((f) => f.name));
    }
  }, []);

  const handleCreateFolder = useCallback(() => {
    const trimmed = folderName.trim();
    if (!trimmed) return;
    console.log("Create folder:", trimmed);
    setFolderName("");
    setCreateFolderOpen(false);
  }, [folderName]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E7EB]">
        <div>
          <div className="flex items-center gap-2 text-sm text-[#6B7280] mb-1">
            <span>所有文件</span>
            <ChevronRight className="h-3.5 w-3.5" />
            <span>工作文档</span>
          </div>
          <h2 className="text-lg font-semibold text-[#111827]">知识库</h2>
        </div>
        <div className="flex items-center gap-2">
          <Button
            className="bg-[#4F46E5] hover:bg-[#4338CA] text-white"
            onClick={() => setUploadOpen(true)}
          >
            <Upload className="h-4 w-4 mr-2" />
            上传
          </Button>
          <Button variant="outline" onClick={() => setCreateFolderOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            新建文件夹
          </Button>
        </div>
      </div>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>上传文件</DialogTitle>
          </DialogHeader>
          <div
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
              isDragging
                ? "border-[#4F46E5] bg-[#EEF2FF]"
                : "border-[#E5E7EB] hover:border-[#4F46E5]"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-8 w-8 text-[#6B7280] mx-auto mb-3" />
            <p className="text-sm text-[#111827] mb-1">将文件拖放到此处</p>
            <p className="text-xs text-[#6B7280]">或点击选择文件</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={createFolderOpen} onOpenChange={setCreateFolderOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建文件夹</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              placeholder="请输入文件夹名称"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateFolder();
              }}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateFolderOpen(false)}>
              取消
            </Button>
            <Button
              className="bg-[#4F46E5] hover:bg-[#4338CA] text-white"
              onClick={handleCreateFolder}
              disabled={!folderName.trim()}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex items-center gap-3 px-6 py-3 border-b border-[#E5E7EB]">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6B7280]" />
          <Input
            placeholder="搜索文件..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1 border border-[#E5E7EB] rounded-lg p-0.5">
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="icon"
            className="h-8 w-8"
            onClick={() => setViewMode("grid")}
          >
            <Grid3X3 className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="icon"
            className="h-8 w-8"
            onClick={() => setViewMode("list")}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {viewMode === "grid" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredFiles.map((file) => (
              <div
                key={file.id}
                className="group border border-[#E5E7EB] rounded-xl p-4 hover:shadow-md transition-shadow bg-white"
              >
                <div className="flex items-start justify-between mb-3">
                  <FileIcon mimeType={file.mime_type} />
                  <DropdownMenu>
                    <DropdownMenuTrigger>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>打开</DropdownMenuItem>
                      <DropdownMenuItem>重命名</DropdownMenuItem>
                      <DropdownMenuItem>移动</DropdownMenuItem>
                      <DropdownMenuItem className="text-red-600">删除</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <h3 className="text-sm font-medium text-[#111827] truncate mb-1">
                  {file.name}
                </h3>
                {file.summary && (
                  <p className="text-xs text-[#6B7280] line-clamp-2 mb-2">{file.summary}</p>
                )}
                <div className="flex flex-wrap gap-1 mb-3">
                  {file.tags?.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      #{tag}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center justify-between text-xs text-[#6B7280]">
                  <span>{formatFileSize(file.file_size)}</span>
                  <StatusBadge status={file.status} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-[#E5E7EB] rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-[#F9FAFB]">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-[#6B7280]">名称</th>
                  <th className="text-left px-4 py-3 font-medium text-[#6B7280]">摘要</th>
                  <th className="text-left px-4 py-3 font-medium text-[#6B7280]">标签</th>
                  <th className="text-left px-4 py-3 font-medium text-[#6B7280]">状态</th>
                  <th className="text-left px-4 py-3 font-medium text-[#6B7280]">大小</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredFiles.map((file) => (
                  <tr
                    key={file.id}
                    className="border-t border-[#E5E7EB] hover:bg-[#F9FAFB] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileIcon mimeType={file.mime_type} />
                        <span className="font-medium text-[#111827]">{file.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#6B7280] max-w-xs truncate">
                      {file.summary}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {file.tags?.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            #{tag}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={file.status} />
                    </td>
                    <td className="px-4 py-3 text-[#6B7280]">
                      {formatFileSize(file.file_size)}
                    </td>
                    <td className="px-4 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger>
                          <Button variant="ghost" size="icon" className="h-7 w-7">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>打开</DropdownMenuItem>
                          <DropdownMenuItem>重命名</DropdownMenuItem>
                          <DropdownMenuItem>移动</DropdownMenuItem>
                          <DropdownMenuItem className="text-red-600">删除</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {filteredFiles.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="h-12 w-12 text-[#E5E7EB] mx-auto mb-3" />
            <p className="text-[#6B7280]">暂无文件</p>
            <p className="text-sm text-[#6B7280] mt-1">将文件拖放到此处，或点击&quot;上传&quot;以开始使用</p>
          </div>
        )}
      </div>
    </div>
  );
}
