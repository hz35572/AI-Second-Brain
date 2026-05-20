"use client";

import { useRouter, usePathname } from "next/navigation";
import {
  FolderOpen,
  Settings,
  Plus,
  ChevronDown,
  BrainCircuit,
  LogOut,
  LogIn,
  MessageSquare,
  Menu,
  X,
  MoreHorizontal,
  Pencil,
  Trash2,
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
import { useAuthStore } from "@/store/auth";
import { useChatStore } from "@/store/chat";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { deleteConversation, getConversations, renameConversation } from "@/lib/api/chat";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function LeftNav() {
  const router = useRouter();
  const pathname = usePathname();
  const { leftNavCollapsed, toggleLeftNav } = useUIStore();
  const { user, isAuthenticated, logout } = useAuthStore();
  const { conversations, setConversations, setCurrentConversationId, updateConversationTitle } = useChatStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null);
  const [renameTitle, setRenameTitle] = useState("");

  useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const data = await getConversations({ page: 1, page_size: 50 });
      setConversations(data.items);
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
  });

  // Close the mobile drawer whenever route changes.
  // The lint rule in this repo discourages setState in effects; use a microtask to break sync render chains.
  useEffect(() => {
    if (!mobileOpen) return;
    queueMicrotask(() => setMobileOpen(false));
  }, [pathname, mobileOpen]);

  const handleNewChat = () => {
    setCurrentConversationId(null);
    router.push("/chat");
  };

  const openRename = (conversationId: string) => {
    const current = conversations.find((c) => c.id === conversationId);
    setRenameConversationId(conversationId);
    setRenameTitle(current?.title || "");
    setRenameOpen(true);
  };

  const submitRename = async () => {
    if (!renameConversationId) return;
    const title = renameTitle.trim();
    if (!title) return;
    await renameConversation(renameConversationId, title);
    updateConversationTitle(renameConversationId, title);
    setRenameOpen(false);
    setRenameConversationId(null);
  };

  const navContent = (
    <>
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <BrainCircuit className="h-6 w-6 text-[#4F46E5]" />
          {!leftNavCollapsed && (
            <h1 className="text-lg font-semibold text-[#111827] truncate">
              AI Second Brain
            </h1>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-7 w-7 hidden lg:flex"
            onClick={toggleLeftNav}
          >
            <ChevronDown className={cn("h-4 w-4 transition-transform", leftNavCollapsed ? "-rotate-90" : "rotate-90")} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-7 w-7 lg:hidden"
            onClick={() => setMobileOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {isAuthenticated ? (
          <>
            <Button
              className="w-full bg-[#4F46E5] hover:bg-[#4338CA] text-white"
              onClick={handleNewChat}
            >
              <Plus className="h-4 w-4 mr-2" />
              {!leftNavCollapsed && "新建对话"}
            </Button>

            <Button
              variant="ghost"
              className={cn(
                "w-full justify-start gap-2 mt-2 text-[#111827] hover:bg-[#EEF2FF]",
                pathname === "/files" && "bg-[#EEF2FF] text-[#4F46E5]"
              )}
              onClick={() => router.push("/files")}
            >
              <FolderOpen className="h-4 w-4" />
              {!leftNavCollapsed && "知识库"}
            </Button>
          </>
        ) : (
          <Button
            className="w-full bg-[#4F46E5] hover:bg-[#4338CA] text-white"
            onClick={() => router.push("/login")}
          >
            <LogIn className="h-4 w-4 mr-2" />
            {!leftNavCollapsed && "登录"}
          </Button>
        )}
      </div>

      <Separator className="bg-[#E5E7EB]" />

      {isAuthenticated && (
        <ScrollArea className="flex-1 px-3 py-3">
          <div className="space-y-4">
            <div>
              {!leftNavCollapsed && (
                <h3 className="text-xs font-medium text-[#6B7280] uppercase tracking-wider mb-2 px-2">
                  近期对话
                </h3>
              )}
              <div className="space-y-0.5">
                {conversations.slice(0, 20).map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => {
                      setCurrentConversationId(conv.id);
                      router.push(`/chat?conversation=${conv.id}`);
                    }}
                    className={cn(
                      "group flex items-center w-full rounded-md px-2 py-1.5 text-sm transition-colors text-left",
                      pathname === `/chat` && conv.id === new URLSearchParams(window.location.search).get("conversation")
                        ? "bg-[#EEF2FF] text-[#4F46E5]"
                        : "text-[#111827] hover:bg-[#EEF2FF]"
                    )}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 mr-2" />
                    {!leftNavCollapsed && (
                      <>
                        <span className="truncate flex-1">{conv.title}</span>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="ml-1 h-7 w-7 opacity-0 group-hover:opacity-100"
                                onClick={(e) => e.stopPropagation()}
                              />
                            }
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-36">
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                openRename(conv.id);
                              }}
                            >
                              <Pencil className="h-4 w-4 mr-2" />
                              重命名
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              variant="destructive"
                              onClick={async (e) => {
                                e.stopPropagation();
                                await deleteConversation(conv.id);
                                // Refresh list (simple + consistent)
                                const data = await getConversations({ page: 1, page_size: 50 });
                                setConversations(data.items);
                                const currentId = new URLSearchParams(window.location.search).get("conversation");
                                if (currentId === conv.id) {
                                  setCurrentConversationId(null);
                                  router.push("/chat");
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </>
                    )}
                  </button>
                ))}
                {conversations.length === 0 && !leftNavCollapsed && (
                  <p className="text-xs text-[#6B7280] px-2 py-2">暂无对话</p>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      )}

      {isAuthenticated && <Separator className="bg-[#E5E7EB]" />}

      <div className="p-3">
        {isAuthenticated ? (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <div
                  className={cn(
                    "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground w-full justify-start gap-2 cursor-pointer",
                    leftNavCollapsed && "px-2"
                  )}
                />
              }
            >
              <div className="h-7 w-7 rounded-full bg-[#4F46E5] flex items-center justify-center text-white text-xs font-medium shrink-0">
                {user?.name?.charAt(0)?.toUpperCase() || "U"}
              </div>
              {!leftNavCollapsed && (
                <span className="text-sm text-[#111827] truncate">
                  {user?.name || "用户"}
                </span>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <Settings className="h-4 w-4 mr-2" />
                设置
              </DropdownMenuItem>
              <DropdownMenuItem onClick={logout}>
                <LogOut className="h-4 w-4 mr-2" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button
            variant="ghost"
            className="w-full justify-start gap-2"
            onClick={() => router.push("/login")}
          >
            <LogIn className="h-4 w-4" />
            {!leftNavCollapsed && <span className="text-sm text-[#111827]">登录</span>}
          </Button>
        )}
      </div>

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>重命名对话</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <input
              type="text"
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              placeholder="对话标题"
              className="w-full px-3 py-2 border border-[#E5E7EB] rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#4F46E5] focus:border-transparent"
              onKeyDown={(e) => {
                if (e.key === "Enter") submitRename();
              }}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setRenameOpen(false)}>
                取消
              </Button>
              <Button
                size="sm"
                className="bg-[#4F46E5] hover:bg-[#4338CA] text-white"
                onClick={submitRename}
                disabled={!renameTitle.trim()}
              >
                保存
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 bg-white shadow-sm border border-[#E5E7EB]"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/30 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "lg:hidden fixed inset-y-0 left-0 z-50 w-[260px] border-r border-[#E5E7EB] bg-[#F9FAFB] flex flex-col transition-transform duration-300",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {navContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden lg:flex border-r border-[#E5E7EB] bg-[#F9FAFB] flex-col transition-all duration-300",
          leftNavCollapsed ? "w-16" : "w-[260px]"
        )}
      >
        {navContent}
      </aside>
    </>
  );
}
