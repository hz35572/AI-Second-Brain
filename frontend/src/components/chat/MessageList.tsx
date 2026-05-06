"use client";

import { useRef, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import type { Message } from "@/lib/api/types";

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  streamingCitations?: Message["citations"];
}

export function MessageList({ messages, streamingContent, streamingCitations }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  return (
    <ScrollArea className="flex-1" ref={scrollRef}>
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {messages.map((message) => (
          <div key={message.id}>
            {message.role === "user" ? (
              <UserMessage content={message.content} />
            ) : (
              <AssistantMessage
                content={message.content}
                citations={message.citations}
              />
            )}
          </div>
        ))}

        {streamingContent && (
          <AssistantMessage
            content={streamingContent}
            citations={streamingCitations}
            streaming
          />
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
