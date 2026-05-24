"use client";

import { useState, useRef, useCallback } from "react";
import { ChevronDown, Paperclip, Send } from "lucide-react";
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
    <div className="mx-auto w-full max-w-[1060px]">
      <div className="relative min-h-[118px] rounded-2xl border border-[#DDE3F0] bg-white px-5 py-4 shadow-[0_18px_42px_rgba(30,41,59,0.10)]">
        <Button
          variant="ghost"
          size="icon"
          className="absolute bottom-4 left-4 h-9 w-9 text-[#52617A] hover:bg-[#F3F5FF]"
          disabled={disabled}
          aria-label="添加附件"
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
            "min-h-[62px] max-h-[200px] resize-none border-0 bg-transparent px-0 pb-10 pt-0 text-base leading-7 text-[#111827] shadow-none placeholder:text-[#8792AB] focus-visible:border-transparent focus-visible:ring-0",
            disabled && "opacity-50"
          )}
        />
        <div className="absolute bottom-4 right-4 flex items-center overflow-hidden rounded-2xl border border-[#DDE3F0] bg-[#F8FAFF] shadow-[0_8px_18px_rgba(79,70,229,0.10)]">
          <Button
            onClick={handleSend}
            disabled={!content.trim() || disabled}
            size="icon"
            className={cn(
              "h-11 w-12 rounded-none border-0 transition-colors",
              content.trim() && !disabled
                ? "bg-[#F0EEFF] text-[#4F46E5] hover:bg-[#E4E0FF]"
                : "bg-[#F0EEFF] text-[#4F46E5]/50"
            )}
            aria-label="发送消息"
          >
            <Send className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-11 w-10 rounded-none border-l border-[#DDE3F0] text-[#25324D] hover:bg-[#EEF2FF]"
            disabled={disabled}
            aria-label="发送选项"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
