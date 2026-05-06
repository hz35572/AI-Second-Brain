"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ChatComposerProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatComposer({ onSend, disabled, placeholder }: ChatComposerProps) {
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = content.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setContent("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [content, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  return (
    <div className="border-t border-[#E5E7EB] bg-white p-4">
      <div className="relative flex items-end gap-2 max-w-3xl mx-auto">
        <Button
          variant="ghost"
          size="icon"
          className="flex-shrink-0 h-9 w-9 text-[#6B7280]"
          disabled={disabled}
        >
          <Paperclip className="h-5 w-5" />
        </Button>
        <Textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "针对您的知识库，提出任何问题..."}
          disabled={disabled}
          rows={1}
          className={cn(
            "min-h-[44px] max-h-[200px] resize-none py-2.5 px-3 text-sm rounded-xl border-[#E5E7EB] focus-visible:ring-[#4F46E5]",
            disabled && "opacity-50"
          )}
        />
        <Button
          onClick={handleSend}
          disabled={!content.trim() || disabled}
          size="icon"
          className={cn(
            "flex-shrink-0 h-9 w-9 rounded-xl transition-colors",
            content.trim() && !disabled
              ? "bg-[#4F46E5] hover:bg-[#4338CA] text-white"
              : "bg-[#E5E7EB] text-[#6B7280]"
          )}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
