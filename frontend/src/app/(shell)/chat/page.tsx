"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MessageList } from "@/components/chat/MessageList";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { ScopeSelector } from "@/components/chat/ScopeSelector";
import { useStreamingText } from "@/lib/sse/useStreamingText";
import { apiEventSource } from "@/lib/api/client";
import type { Message, Citation } from "@/lib/api/types";
import { Pencil, Share2, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const mockMessages: Message[] = [
  {
    id: "1",
    role: "user",
    content: "总结我的研究论文",
    created_at: "2026-04-26T10:00:00Z",
  },
  {
    id: "2",
    role: "assistant",
    content:
      "根据您的研究论文，主要观点包括：[1] 提出了基于 Transformer 的新型注意力机制；[2] 在多个基准数据集上取得了 SOTA 结果；[3] 分析了计算效率与模型性能之间的权衡关系。",
    citations: [
      {
        index: 1,
        chunk_id: "c1",
        file_id: "f1",
        file_name: "research_paper.pdf",
        page: 3,
        text: "提出了基于 Transformer 的新型注意力机制",
        highlight_positions: { start: 120, end: 180 },
      },
      {
        index: 2,
        chunk_id: "c2",
        file_id: "f1",
        file_name: "research_paper.pdf",
        page: 5,
        text: "在多个基准数据集上取得了 SOTA 结果",
        highlight_positions: { start: 45, end: 95 },
      },
    ],
    created_at: "2026-04-26T10:00:05Z",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [isLoading, setIsLoading] = useState(false);
  const { text: streamingText, append, reset } = useStreamingText();
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const sseRef = useRef<{ close: () => void } | null>(null);
  const streamingContentRef = useRef("");
  const streamingCitationsRef = useRef<Citation[]>([]);

  useEffect(() => {
    streamingContentRef.current = streamingText;
  }, [streamingText]);

  useEffect(() => {
    streamingCitationsRef.current = streamingCitations;
  }, [streamingCitations]);

  const handleSend = useCallback(
    (content: string) => {
      const userMessage: Message = {
        id: `u-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      reset();
      setStreamingCitations([]);
      streamingContentRef.current = "";
      streamingCitationsRef.current = [];

      sseRef.current = apiEventSource("/chat/conversations/test/messages", {
        body: { content, stream: true },
        onMessage: (data: unknown) => {
          const msg = data as { type: string; content?: string; citations?: Citation[] };
          if (msg.type === "chunk" && msg.content) {
            append(msg.content);
          } else if (msg.type === "citation" && msg.citations) {
            setStreamingCitations((prev) => [...prev, ...msg.citations!]);
          } else if (msg.type === "done") {
            setIsLoading(false);
            setMessages((prev) => [
              ...prev,
              {
                id: `a-${Date.now()}`,
                role: "assistant",
                content: streamingContentRef.current || "暂无回答",
                citations: streamingCitationsRef.current,
                created_at: new Date().toISOString(),
              },
            ]);
            reset();
            setStreamingCitations([]);
          }
        },
        onError: () => {
          setIsLoading(false);
        },
        onDone: () => {
          setIsLoading(false);
        },
      });
    },
    [append, reset]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#E5E7EB]">
        <h2 className="text-base font-semibold text-[#111827]">
          新对话
        </h2>
        <div className="flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Pencil className="h-4 w-4 text-[#6B7280]" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>编辑标题</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Share2 className="h-4 w-4 text-[#6B7280]" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>分享</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Download className="h-4 w-4 text-[#6B7280]" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>导出</TooltipContent>
          </Tooltip>
        </div>
      </div>

      <MessageList
        messages={messages}
        streamingContent={isLoading ? streamingText : undefined}
        streamingCitations={streamingCitations}
      />

      <div className="px-4 pb-2">
        <div className="max-w-3xl mx-auto mb-2">
          <ScopeSelector />
        </div>
      </div>
      <ChatComposer onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
