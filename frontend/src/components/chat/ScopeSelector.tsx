"use client";

import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";
import { Globe, FolderOpen, FileText } from "lucide-react";

type ScopeType = "global" | "folder" | "file";

const scopeOptions: { value: ScopeType; label: string; icon: React.ReactNode }[] = [
  { value: "global", label: "全局搜索", icon: <Globe className="h-3.5 w-3.5" /> },
  { value: "folder", label: "选定文件夹", icon: <FolderOpen className="h-3.5 w-3.5" /> },
  { value: "file", label: "选定文档", icon: <FileText className="h-3.5 w-3.5" /> },
];

export function ScopeSelector() {
  const { scope, setScope } = useUIStore();

  const currentType = scope.type;

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-[#F9FAFB] border border-[#E5E7EB] w-fit">
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
            "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
            currentType === option.value
              ? "bg-white text-[#4F46E5] shadow-sm"
              : "text-[#6B7280] hover:text-[#111827]"
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}
