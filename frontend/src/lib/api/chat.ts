import { apiFetch, apiEventSource } from "./client";
import type { ApiResponse, Conversation, Message, Citation } from "./types";

export async function createConversation(payload: {
  title?: string;
  scope_type: "global" | "folder" | "file";
  scope_ids?: string[];
}): Promise<Conversation> {
  const res = await apiFetch<ApiResponse<Conversation>>("/chat/conversations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function getConversations(params?: { page?: number; page_size?: number }): Promise<{
  items: Conversation[];
}> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));
  const res = await apiFetch<ApiResponse<{ items: Conversation[] }>>(
    `/chat/conversations?${search.toString()}`
  );
  return res.data;
}

export async function getMessages(
  conversationId: string,
  params?: { page?: number; page_size?: number }
): Promise<{ items: Message[] }> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));
  const res = await apiFetch<ApiResponse<{ items: Message[] }>>(
    `/chat/conversations/${conversationId}/messages?${search.toString()}`
  );
  return res.data;
}

export interface ChatStreamCallbacks {
  onChunk?: (content: string) => void;
  onCitation?: (citations: Citation[]) => void;
  onDone?: (metadata?: { token_usage?: number; latency_ms?: number }) => void;
  onError?: (err: Error) => void;
}

export function sendChatMessage(
  conversationId: string,
  content: string,
  callbacks: ChatStreamCallbacks
): { close: () => void } {
  return apiEventSource(`/chat/conversations/${conversationId}/messages`, {
    body: { content, stream: true },
    onMessage: (data: unknown) => {
      const msg = data as { type: string; content?: string; citations?: Citation[]; metadata?: { token_usage?: number; latency_ms?: number } };
      if (msg.type === "chunk" && msg.content) {
        callbacks.onChunk?.(msg.content);
      } else if (msg.type === "citation" && msg.citations) {
        callbacks.onCitation?.(msg.citations);
      } else if (msg.type === "done") {
        callbacks.onDone?.(msg.metadata);
      }
    },
    onError: (err) => callbacks.onError?.(err),
    onDone: () => callbacks.onDone?.(),
  });
}
