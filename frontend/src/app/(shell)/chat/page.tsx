"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/store/chat";
import { useUIStore } from "@/store/ui";
import { useAuthStore } from "@/store/auth";
import { createConversation, getConversations, getMessages, sendChatMessage } from "@/lib/api/chat";
import { MessageList } from "@/components/chat/MessageList";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { ScopeSelector } from "@/components/chat/ScopeSelector";
import { AlertCircle, Bot, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Message } from "@/lib/api/types";

function NewChatHero({ userName }: { userName: string }) {
  return (
    <div className="mx-auto grid w-full max-w-[1160px] items-center gap-8 px-8 pb-8 pt-10 lg:grid-cols-[1fr_420px]">
      <div>
        <h1 className="text-[36px] font-bold leading-[1.25] tracking-normal text-[#07143B]">
          嗨， <span className="text-[#4F46E5]">{userName}</span>
          <br />
          有什么可以帮您?
        </h1>
        <p className="mt-5 text-base text-[#596783]">
          基于您的知识库，我可以帮您查找信息、解答问题、分析文档内容
        </p>
      </div>
      <div className="hidden justify-end lg:flex">
        <div className="relative h-[210px] w-[360px] max-w-full opacity-95">
          <div className="absolute left-8 top-9 h-28 w-56 rotate-[-18deg] rounded-[34px] border border-[#DCE1FF] bg-[#F4F6FF]/70 shadow-[0_28px_70px_rgba(79,70,229,0.18)]" />
          <div className="absolute left-20 top-3 h-32 w-56 rotate-[26deg] rounded-[30px] bg-gradient-to-br from-[#F7F8FF] to-[#E9ECFF] opacity-80 shadow-[0_20px_60px_rgba(79,70,229,0.12)]" />
          <div className="absolute left-[110px] top-12 flex h-24 w-28 items-center justify-center rounded-[32px] bg-gradient-to-br from-[#A7AAFF] via-[#6960F6] to-[#4438D9] shadow-[0_18px_44px_rgba(79,70,229,0.28)]">
            <Bot className="h-14 w-14 text-white/80" />
          </div>
          <div className="absolute left-7 top-2 h-2 w-2 rounded-full bg-[#5B50F1]" />
          <div className="absolute right-9 top-15 h-2 w-2 rounded-full bg-[#5B50F1]" />
          <div className="absolute right-17 bottom-12 h-2 w-2 rounded-full bg-[#5B50F1]" />
          <div className="absolute left-2 top-20 h-px w-40 rotate-[-24deg] bg-[#CDD3FF]" />
          <div className="absolute right-10 top-25 h-px w-32 rotate-[24deg] bg-[#CDD3FF]" />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const searchParams = useSearchParams();
  const conversationIdFromUrl = searchParams.get("conversation");

  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    streamingContent,
    streamingCitations,
    setConversations,
    addConversation,
    setCurrentConversationId,
    setMessages,
    addMessage,
    setIsLoading,
    appendStreamingContent,
    addStreamingCitations,
    resetStreaming,
  } = useChatStore();
  const { scope } = useUIStore();

  const [error, setError] = useState("");
  const streamingContentRef = useRef("");
  const streamingCitationsRef = useRef(streamingCitations);
  const sseRef = useRef<{ close: () => void } | null>(null);

  useEffect(() => {
    streamingContentRef.current = streamingContent;
  }, [streamingContent]);

  useEffect(() => {
    streamingCitationsRef.current = streamingCitations;
  }, [streamingCitations]);

  useEffect(() => {
    if (conversationIdFromUrl) {
      setCurrentConversationId(conversationIdFromUrl);
    }
  }, [conversationIdFromUrl, setCurrentConversationId]);

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

  useQuery({
    queryKey: ["messages", currentConversationId],
    queryFn: async () => {
      if (!currentConversationId) return { items: [] };
      const data = await getMessages(currentConversationId, { page: 1, page_size: 100 });
      setMessages(data.items);
      return data;
    },
    enabled: !!currentConversationId && isAuthenticated,
    staleTime: 30 * 1000,
  });

  const handleSend = useCallback(
    async (content: string) => {
      setError("");
      let convId = currentConversationId;

      if (!convId) {
        try {
          const conv = await createConversation({
            title: content.slice(0, 50) || "新对话",
            scope_type: scope.type,
            scope_ids: scope.type === "global" ? [] : (scope as { ids: string[] }).ids,
          });
          addConversation(conv);
          convId = conv.id;
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
        } catch (err) {
          setError(err instanceof Error ? err.message : "创建对话失败");
          return;
        }
      }

      const userMessage: Message = {
        id: `u-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);
      setIsLoading(true);
      resetStreaming();
      streamingContentRef.current = "";
      streamingCitationsRef.current = [];

      sseRef.current = sendChatMessage(convId, content, {
        onChunk: (chunk) => {
          streamingContentRef.current += chunk;
          appendStreamingContent(chunk);
        },
        onCitation: (citations) => {
          addStreamingCitations(citations);
          streamingCitationsRef.current = [...streamingCitationsRef.current, ...citations];
        },
        onDone: (metadata) => {
          setIsLoading(false);
          const assistantMessage: Message = {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: streamingContentRef.current || "暂无回答",
            citations: streamingCitationsRef.current,
            created_at: new Date().toISOString(),
          };
          addMessage(assistantMessage);
          resetStreaming();
          queryClient.invalidateQueries({ queryKey: ["messages", convId] });
          if (metadata) {
            console.log("Chat metadata:", metadata);
          }
        },
        onError: (err) => {
          setIsLoading(false);
          setError(err.message || "发送消息失败");
        },
      });
    },
    [
      currentConversationId,
      scope,
      addConversation,
      addMessage,
      setIsLoading,
      resetStreaming,
      appendStreamingContent,
      addStreamingCitations,
      queryClient,
    ]
  );

  const handleStop = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
      setIsLoading(false);
    }
  }, [setIsLoading]);

  const displayMessages = currentConversationId
    ? messages
    : messages.filter((m) => m.id.startsWith("u-") || m.id.startsWith("a-"));
  const currentTitle = currentConversationId
    ? conversations.find((c) => c.id === currentConversationId)?.title || "对话"
    : "新对话";
  const showNewChatHero = !currentConversationId && displayMessages.length === 0 && !streamingContent;
  const userName = user?.name || "admin";

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-[72px] items-center justify-between border-b border-[#E7EAF3] bg-white/90 px-9">
        <h2 className="text-lg font-bold text-[#07143B]">{currentTitle}</h2>
      </div>

      {error && (
        <Alert variant="destructive" className="mx-4 mt-3 shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="min-h-0 flex-1 overflow-hidden px-8 py-0">
        <div className="h-full bg-white">
          {showNewChatHero && <NewChatHero userName={userName} />}
          <MessageList
            messages={displayMessages}
            streamingContent={streamingContent}
            streamingCitations={streamingCitations}
          />
        </div>
      </div>

      <div className="shrink-0 bg-[#FBFCFF] px-8 pb-9 pt-4">
        {isLoading && (
          <div className="mx-auto mb-2 flex max-w-[1060px] items-center gap-2 text-xs text-[#6B7280]">
            <Loader2 className="h-3 w-3 animate-spin" />
            AI 正在思考...
            <button
              onClick={handleStop}
              className="text-[#EF4444] hover:underline ml-2"
            >
              停止生成
            </button>
          </div>
        )}
        <div className="mb-5 flex justify-center">
          <ScopeSelector />
        </div>
        <ChatComposer onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}
