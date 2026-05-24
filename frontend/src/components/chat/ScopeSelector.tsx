"use client";

import { useEffect, useState } from "react";
import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";
import { Globe, FolderOpen, FileText, Check } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getFolderTree } from "@/lib/api/files";
import { useFilesStore } from "@/store/files";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

type ScopeType = "global" | "folder" | "file";

const scopeOptions: { value: ScopeType; label: string; icon: React.ReactNode }[] = [
  { value: "global", label: "全局搜索", icon: <Globe className="h-3.5 w-3.5" /> },
  { value: "folder", label: "选定文件夹", icon: <FolderOpen className="h-3.5 w-3.5" /> },
  { value: "file", label: "选定文档", icon: <FileText className="h-3.5 w-3.5" /> },
];

export function ScopeSelector() {
  const { scope, setScope } = useUIStore();
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [tempSelection, setTempSelection] = useState<string[]>(
    scope.type === "global" ? [] : (scope as { ids: string[] }).ids
  );

  const { files, setFolders } = useFilesStore();
  const { data: folderData } = useQuery({
    queryKey: ["folders"],
    queryFn: () => getFolderTree(),
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (!folderData) return;
    queueMicrotask(() => setFolders(folderData));
  }, [folderData, setFolders]);

  const currentType = scope.type;

  const handleOpenSelector = () => {
    setTempSelection(scope.type === "global" ? [] : (scope as { ids: string[] }).ids);
    setSelectorOpen(true);
  };

  const handleConfirmSelection = () => {
    if (currentType === "folder" || currentType === "file") {
      setScope({ type: currentType, ids: tempSelection } as { type: "folder"; ids: string[] } | { type: "file"; ids: string[] });
    }
    setSelectorOpen(false);
  };

  const toggleSelection = (id: string) => {
    setTempSelection((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const renderSelectionDialog = () => {
    if (currentType === "folder") {
      const folders = folderData || [];
      return (
        <Dialog open={selectorOpen} onOpenChange={setSelectorOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>选择文件夹</DialogTitle>
            </DialogHeader>
            <ScrollArea className="max-h-[300px] mt-2">
              <div className="space-y-1">
                {folders.map((folder) => (
                  <button
                    key={folder.id}
                    onClick={() => toggleSelection(folder.id)}
                    className={cn(
                      "flex items-center justify-between w-full px-3 py-2 rounded-md text-sm transition-colors",
                      tempSelection.includes(folder.id)
                        ? "bg-[#EEF2FF] text-[#4F46E5]"
                        : "hover:bg-[#F9FAFB] text-[#111827]"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <FolderOpen className="h-4 w-4" />
                      {folder.name}
                    </span>
                    {tempSelection.includes(folder.id) && <Check className="h-4 w-4" />}
                  </button>
                ))}
                {folders.length === 0 && (
                  <p className="text-sm text-[#6B7280] text-center py-4">暂无文件夹</p>
                )}
              </div>
            </ScrollArea>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" size="sm" onClick={() => setSelectorOpen(false)}>
                取消
              </Button>
              <Button size="sm" className="bg-[#4F46E5] hover:bg-[#4338CA] text-white" onClick={handleConfirmSelection}>
                确认 ({tempSelection.length})
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      );
    }

    if (currentType === "file") {
      return (
        <Dialog open={selectorOpen} onOpenChange={setSelectorOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>选择文档</DialogTitle>
            </DialogHeader>
            <ScrollArea className="max-h-[300px] mt-2">
              <div className="space-y-1">
                {files.map((file) => (
                  <button
                    key={file.id}
                    onClick={() => toggleSelection(file.id)}
                    className={cn(
                      "flex items-center justify-between w-full px-3 py-2 rounded-md text-sm transition-colors",
                      tempSelection.includes(file.id)
                        ? "bg-[#EEF2FF] text-[#4F46E5]"
                        : "hover:bg-[#F9FAFB] text-[#111827]"
                    )}
                  >
                    <span className="flex items-center gap-2 truncate">
                      <FileText className="h-4 w-4 shrink-0" />
                      <span className="truncate">{file.name}</span>
                    </span>
                    {tempSelection.includes(file.id) && <Check className="h-4 w-4 shrink-0" />}
                  </button>
                ))}
                {files.length === 0 && (
                  <p className="text-sm text-[#6B7280] text-center py-4">暂无文件，请先上传</p>
                )}
              </div>
            </ScrollArea>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" size="sm" onClick={() => setSelectorOpen(false)}>
                取消
              </Button>
              <Button size="sm" className="bg-[#4F46E5] hover:bg-[#4338CA] text-white" onClick={handleConfirmSelection}>
                确认 ({tempSelection.length})
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      );
    }

    return null;
  };

  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <div className="flex w-fit items-center gap-1 rounded-xl border border-[#DDE3F0] bg-white/90 p-1 shadow-[0_10px_28px_rgba(30,41,59,0.06)]">
        {scopeOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => {
              if (option.value === "global") {
                setScope({ type: "global" });
              } else if (option.value === "folder") {
                setScope({ type: "folder", ids: [] });
              } else {
                setScope({ type: "file", ids: [] });
              }
            }}
            className={cn(
              "flex h-9 items-center gap-2 rounded-lg px-4 text-sm font-medium transition-colors",
              currentType === option.value
                ? "bg-[#F0EEFF] text-[#4F46E5] shadow-[0_6px_16px_rgba(79,70,229,0.10)]"
                : "text-[#52617A] hover:bg-[#F8FAFF] hover:text-[#111827]"
            )}
          >
            {option.icon}
            {option.label}
          </button>
        ))}
      </div>

      {(currentType === "folder" || currentType === "file") && (
        <Button
          variant="ghost"
          size="sm"
          className="h-9 rounded-lg text-sm text-[#4F46E5] hover:bg-[#EEF2FF]"
          onClick={handleOpenSelector}
        >
          {(scope as { ids: string[] }).ids.length > 0
            ? `已选 ${(scope as { ids: string[] }).ids.length} 个`
            : "选择..."}
        </Button>
      )}

      {renderSelectionDialog()}
    </div>
  );
}
