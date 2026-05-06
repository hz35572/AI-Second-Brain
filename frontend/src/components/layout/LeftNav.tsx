"use client";

import { useRouter } from "next/navigation";
import {
  FolderOpen,
  Settings,
  Plus,
  ChevronDown,
  BrainCircuit,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUIStore } from "@/store/ui";

const mockConversations = [
  { id: "c1", title: "关于第三季度预算的讨论", updated_at: "2026-04-26" },
  { id: "c2", title: "研究论文摘要总结", updated_at: "2026-04-25" },
];

export function LeftNav() {
  const router = useRouter();
  const { leftNavCollapsed, toggleLeftNav } = useUIStore();

  if (leftNavCollapsed) {
    return (
      <div className="w-14 border-r border-[#E5E7EB] bg-[#F9FAFB] flex flex-col items-center py-4 gap-3">
        <Button variant="ghost" size="icon" onClick={toggleLeftNav}>
          <BrainCircuit className="h-5 w-5 text-[#4F46E5]" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/files")}
        >
          <FolderOpen className="h-5 w-5" />
        </Button>
      </div>
    );
  }

  return (
    <aside className="w-[260px] border-r border-[#E5E7EB] bg-[#F9FAFB] flex flex-col">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <BrainCircuit className="h-6 w-6 text-[#4F46E5]" />
          <h1 className="text-lg font-semibold text-[#111827]">
            AI Second Brain
          </h1>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-7 w-7"
            onClick={toggleLeftNav}
          >
            <ChevronDown className="h-4 w-4 rotate-90" />
          </Button>
        </div>

        <Button
          className="w-full bg-[#4F46E5] hover:bg-[#4338CA] text-white"
          onClick={() => router.push("/chat")}
        >
          <Plus className="h-4 w-4 mr-2" />
          新建对话
        </Button>

        <Button
          variant="ghost"
          className="w-full justify-start gap-2 mt-2 text-[#111827] hover:bg-[#EEF2FF]"
          onClick={() => router.push("/files")}
        >
          <FolderOpen className="h-4 w-4" />
          知识库
        </Button>
      </div>

      <Separator className="bg-[#E5E7EB]" />

      <ScrollArea className="flex-1 px-3 py-3">
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-medium text-[#6B7280] uppercase tracking-wider mb-2 px-2">
              近期对话
            </h3>
            <div className="space-y-0.5">
              {mockConversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => router.push(`/chat?conversation=${conv.id}`)}
                  className="flex flex-col w-full rounded-md px-2 py-1.5 text-sm text-[#111827] hover:bg-[#EEF2FF] transition-colors text-left"
                >
                  <span className="truncate">{conv.title}</span>
                  <span className="text-xs text-[#6B7280]">{conv.updated_at}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>

      <Separator className="bg-[#E5E7EB]" />

      <div className="p-3">
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button variant="ghost" className="w-full justify-start gap-2">
              <div className="h-7 w-7 rounded-full bg-[#4F46E5] flex items-center justify-center text-white text-xs font-medium">
                U
              </div>
              <span className="text-sm text-[#111827]">用户</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => router.push("/settings")}>
              <Settings className="h-4 w-4 mr-2" />
              设置
            </DropdownMenuItem>
            <DropdownMenuItem>
              <LogOut className="h-4 w-4 mr-2" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}
