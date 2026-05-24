"use client";

import { useRouter, usePathname } from "next/navigation";
import {
  FolderOpen,
  Settings,
  Plus,
  BrainCircuit,
  LogOut,
  LogIn,
  MessageSquare,
  Menu,
  X,
  MoreHorizontal,
  Pencil,
  Trash2,
  Search,
  ChevronDown,
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
      <div className="px-6 pb-6 pt-8">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-[#4F46E5] shadow-[0_10px_28px_rgba(79,70,229,0.16)]">
            <BrainCircuit className="h-7 w-7" />
          </div>
          {!leftNavCollapsed && (
            <h1 className="truncate text-xl font-bold tracking-tight text-[#111827]">
              AI Second Brain
            </h1>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto hidden h-7 w-7 text-[#64748B] hover:bg-[#EEF2FF] lg:flex"
            onClick={toggleLeftNav}
            aria-label="折叠侧边栏"
          >
            <ChevronDown className={cn("h-4 w-4 transition-transform", leftNavCollapsed ? "-rotate-90" : "rotate-90")} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-7 w-7 text-[#64748B] hover:bg-[#EEF2FF] lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="关闭侧边栏"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {isAuthenticated ? (
          <>
            <Button
              className="h-12 w-full rounded-xl bg-[#4F46E5] text-base font-medium text-white shadow-[0_14px_30px_rgba(79,70,229,0.28)] hover:bg-[#4338CA]"
              onClick={handleNewChat}
            >
              <Plus className="h-4 w-4 mr-2" />
              {!leftNavCollapsed && "新建对话"}
            </Button>

            <Button
              variant="ghost"
              className={cn(
                "mt-7 h-11 w-full justify-start gap-3 rounded-xl px-4 text-[15px] font-medium text-[#0F172A] hover:bg-[#EEF2FF]",
                pathname === "/files" && "bg-[#EEF2FF] text-[#4F46E5] shadow-[inset_0_0_0_1px_rgba(79,70,229,0.04)]"
              )}
              onClick={() => router.push("/files")}
            >
              <FolderOpen className="h-4 w-4" />
              {!leftNavCollapsed && "知识库"}
            </Button>
          </>
        ) : (
          <Button
            className="h-12 w-full rounded-xl bg-[#4F46E5] text-base font-medium text-white shadow-[0_14px_30px_rgba(79,70,229,0.28)] hover:bg-[#4338CA]"
            onClick={() => router.push("/login")}
          >
            <LogIn className="h-4 w-4 mr-2" />
            {!leftNavCollapsed && "登录"}
          </Button>
        )}
      </div>

      <Separator className="bg-[#E7EAF3]" />

      {isAuthenticated && (
        <ScrollArea className="flex-1 px-4 py-6">
          <div className="space-y-4">
            <div>
              {!leftNavCollapsed && (
                <div className="mb-4 flex items-center justify-between px-1">
                  <h3 className="text-sm font-medium text-[#7A86A1]">最近对话</h3>
                  <Search className="h-4 w-4 text-[#66708A]" />
                </div>
              )}
              <div className="space-y-2">
                {conversations.slice(0, 20).map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => {
                      setCurrentConversationId(conv.id);
                      router.push(`/chat?conversation=${conv.id}`);
                    }}
                    className={cn(
                      "group flex w-full items-center rounded-xl px-3 py-3 text-left text-sm transition-colors",
                      pathname === `/chat` && conv.id === new URLSearchParams(window.location.search).get("conversation")
                        ? "bg-[#F0EEFF] text-[#4F46E5]"
                        : "text-[#25324D] hover:bg-[#F4F6FF]"
                    )}
                  >
                    <MessageSquare className="mr-2 h-4 w-4 shrink-0" />
                    {!leftNavCollapsed && (
                      <>
                        <span className="flex-1 truncate font-medium">{conv.title}</span>
                        <span className="ml-2 shrink-0 text-xs font-normal text-[#7A86A1]">
                          {new Date(conv.updated_at || conv.created_at).toLocaleTimeString("zh-CN", {
                            hour: "2-digit",
                            minute: "2-digit",
                            hour12: false,
                          })}
                        </span>
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
                  <p className="px-2 py-2 text-xs text-[#7A86A1]">暂无对话</p>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      )}

      {isAuthenticated && <Separator className="bg-[#E7EAF3]" />}

      <div className="p-5">
        {isAuthenticated ? (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <div
                  className={cn(
                    "group/button inline-flex shrink-0 items-center justify-center rounded-2xl border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none hover:bg-[#F4F6FF] aria-expanded:bg-[#F4F6FF] w-full justify-start gap-3 cursor-pointer px-0 py-2",
                    leftNavCollapsed && "px-2"
                  )}
                />
              }
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#4F46E5] text-base font-semibold text-white shadow-[0_10px_24px_rgba(79,70,229,0.24)]">
                {user?.name?.charAt(0)?.toUpperCase() || "A"}
              </div>
              {!leftNavCollapsed && (
                <>
                  <div className="min-w-0 flex-1 text-left">
                    <div className="truncate text-sm font-semibold text-[#111827]">
                      {user?.name || "admin"}
                    </div>
                    <div className="text-xs text-[#7A86A1]">管理员</div>
                  </div>
                  <ChevronDown className="h-4 w-4 text-[#25324D]" />
                </>
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
          className="h-9 w-9 border border-[#E7EAF3] bg-white shadow-sm"
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
          "fixed inset-y-0 left-0 z-50 flex w-[284px] flex-col border-r border-[#E7EAF3] bg-[#FBFCFF] transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {navContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden flex-col border-r border-[#E7EAF3] bg-[#FBFCFF] transition-all duration-300 lg:flex",
          leftNavCollapsed ? "w-20" : "w-[284px]"
        )}
      >
        {navContent}
      </aside>
    </>
  );
}
