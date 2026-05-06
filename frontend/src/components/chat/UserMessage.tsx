"use client";

interface UserMessageProps {
  content: string;
}

export function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-[#EEF2FF] px-4 py-3 text-[#111827] text-sm leading-relaxed">
        {content}
      </div>
    </div>
  );
}
