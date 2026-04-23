import type { ChatMessage } from "../types/chat";
import { MarkdownContent } from "./MarkdownContent";
import { SourcesPanel } from "./SourcesPanel";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  const wrapperClass = isUser ? "justify-end" : "justify-start";
  const bubbleClass = isUser
    ? "bg-ink text-white"
    : isSystem
      ? "bg-warm/10 text-slate-700 border border-warm/20"
      : message.isError
        ? "border border-red-200 bg-red-50 text-red-700"
        : "border border-white bg-white text-ink";

  return (
    <div className={`flex ${wrapperClass}`}>
      <div className={`${isUser ? "max-w-3xl" : "w-full max-w-none"} rounded-[24px] px-5 py-4 shadow-sm ${bubbleClass}`}>
        {isUser || isSystem || message.isError ? (
          <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
        ) : (
          <MarkdownContent content={message.content} />
        )}
        {message.meta ? <p className="mt-3 text-xs opacity-75">{message.meta}</p> : null}
        {!isUser && !isSystem && message.sources ? <SourcesPanel sources={message.sources} /> : null}
      </div>
    </div>
  );
}
