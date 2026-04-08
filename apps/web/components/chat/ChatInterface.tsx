"use client";

import { useChat } from "@ai-sdk/react";
import { useRef, useEffect, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { UploadDialog } from "@/components/documents/UploadDialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload as UploadIcon } from "lucide-react";

export function ChatInterface() {
  const [aerodrome, setAerodrome] = useState("GLOBAL");
  const [uploadOpen, setUploadOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    data,
  } = useChat({
    api: "/api/chat",
    body: {
      aerodrome_icao: aerodrome,
    },
  });

  // Extract source metadata from stream data annotations
  const latestSources = (() => {
    if (!data || data.length === 0) return undefined;
    // Find the last annotation containing sources
    for (let i = data.length - 1; i >= 0; i--) {
      const item = data[i] as Record<string, unknown>;
      if (item?.sources && Array.isArray(item.sources)) {
        return item.sources as {
          source_index: number;
          doc_name: string;
          doc_type: string;
          section_path: string;
          page_number: number | null;
          chunk_text: string;
          aerodrome_icao: string;
          clause_id: string;
          cited_clause: string;
        }[];
      }
    }
    return undefined;
  })();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">
            Aerodrome:
          </span>
          <Select value={aerodrome} onValueChange={setAerodrome}>
            <SelectTrigger className="h-8 w-32 text-xs" aria-label="Select aerodrome">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="GLOBAL">GLOBAL</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setUploadOpen(true)}
          className="gap-1.5 text-xs"
        >
          <UploadIcon className="h-3.5 w-3.5" />
          Upload Document
        </Button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <div className="rounded-full bg-primary/10 p-4">
              <svg
                className="h-8 w-8 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold">Celestia Memoria</h2>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                Ask questions about ICAO regulations, EASA requirements,
                aerodrome procedures, or any aviation regulatory document in the
                system.
              </p>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-6">
          {messages.map((message, i) => {
            // Pass source metadata to the last assistant message
            const isLastAssistant =
              message.role === "assistant" &&
              i === messages.length - 1;
            return (
              <MessageBubble
                key={message.id}
                message={message}
                sourceData={isLastAssistant ? latestSources : undefined}
              />
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status" aria-label="Loading response">
              <div className="flex gap-1" aria-hidden="true">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce [animation-delay:0.2s]">.</span>
                <span className="animate-bounce [animation-delay:0.4s]">.</span>
              </div>
              Searching documents...
            </div>
          )}

          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {error.message || "An error occurred. Please try again."}
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <ChatInput
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={handleSubmit}
        isLoading={isLoading}
      />

      {/* Upload Dialog */}
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </div>
  );
}
