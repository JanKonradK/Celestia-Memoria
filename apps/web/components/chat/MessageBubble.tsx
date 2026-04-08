"use client";

import { memo } from "react";
import type { Message } from "ai";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { SourceCard } from "./SourceCard";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

interface SourceMetadata {
  source_index: number;
  doc_name: string;
  doc_type: string;
  section_path: string;
  page_number: number | null;
  chunk_text: string;
  aerodrome_icao: string;
  clause_id: string;
  cited_clause: string;
}

interface MessageBubbleProps {
  message: Message;
  sourceData?: SourceMetadata[];
}

export const MessageBubble = memo(function MessageBubble({ message, sourceData }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Extract [Source N] references from assistant messages and merge with metadata
  const sources = !isUser ? extractSources(message.content, sourceData) : [];

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
            <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
              {message.content}
            </ReactMarkdown>
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
});

interface ParsedSource {
  index: number;
  label: string;
  doc_name?: string;
  doc_type?: string;
  section_path?: string;
  page_number?: number | null;
  chunk_text?: string;
  aerodrome_icao?: string;
  clause_id?: string;
  cited_clause?: string;
}

function extractSources(
  content: string,
  sourceData?: SourceMetadata[]
): ParsedSource[] {
  const matches = content.matchAll(/\[Source\s+(\d+)(?:,\s*([^\]]+))?\]/g);
  const seen = new Set<number>();
  const sources: ParsedSource[] = [];

  // Build lookup from backend source metadata
  const metaByIndex = new Map<number, SourceMetadata>();
  if (sourceData) {
    for (const s of sourceData) {
      metaByIndex.set(s.source_index, s);
    }
  }

  for (const match of matches) {
    const idx = parseInt(match[1], 10);
    if (!seen.has(idx)) {
      seen.add(idx);
      const meta = metaByIndex.get(idx);
      sources.push({
        index: idx,
        label: `Source ${idx}`,
        doc_name: meta?.doc_name,
        doc_type: meta?.doc_type,
        section_path: meta?.section_path,
        page_number: meta?.page_number,
        chunk_text: meta?.chunk_text,
        aerodrome_icao: meta?.aerodrome_icao,
        clause_id: meta?.clause_id,
        cited_clause: match[2]?.trim() || meta?.cited_clause || "",
      });
    }
  }

  return sources;
}
