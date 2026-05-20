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
import { AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Message } from "@/lib/api/types";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const conversationIdFromUrl = searchParams.get("conversation");

  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
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

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB] bg-white">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-[#111827]">
            {currentConversationId
              ? conversations.find((c) => c.id === currentConversationId)?.title || "对话"
              : "新对话"}
          </h2>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mx-4 mt-3 shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={displayMessages}
          streamingContent={streamingContent}
          streamingCitations={streamingCitations}
        />
      </div>

      <div className="shrink-0 border-t border-[#E5E7EB] bg-white px-4 py-3">
        {isLoading && (
          <div className="flex items-center gap-2 mb-2 text-xs text-[#6B7280]">
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
        <div className="mb-2">
          <ScopeSelector />
        </div>
        <ChatComposer onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}
