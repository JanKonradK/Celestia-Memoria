"use client";

import type { Message } from "ai";
import ReactMarkdown from "react-markdown";
import { SourceCard } from "./SourceCard";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Extract [Source N] references from assistant messages
  const sources = !isUser ? extractSources(message.content) : [];

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback
          className={cn(
            "text-xs font-medium",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground"
          )}
        >
          {isUser ? "You" : "CM"}
        </AvatarFallback>
      </Avatar>

      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {sources.length > 0 && (
          <div className="mt-3 space-y-2 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">
              Sources
            </p>
            {sources.map((source) => (
              <SourceCard key={source.index} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ParsedSource {
  index: number;
  label: string;
}

function extractSources(content: string): ParsedSource[] {
  const matches = content.matchAll(/\[Source\s+(\d+)\]/g);
  const seen = new Set<number>();
  const sources: ParsedSource[] = [];

  for (const match of matches) {
    const idx = parseInt(match[1], 10);
    if (!seen.has(idx)) {
      seen.add(idx);
      sources.push({ index: idx, label: `Source ${idx}` });
    }
  }

  return sources;
}
