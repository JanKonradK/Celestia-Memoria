"use client";

import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChangeEvent, FormEvent } from "react";

interface ChatInputProps {
  input: string;
  handleInputChange: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (e: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
}

export function ChatInput({
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
}: ChatInputProps) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form && input.trim()) {
        form.requestSubmit();
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="relative flex-1">
          <textarea
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about aviation regulations, procedures, or aerodrome information..."
            rows={1}
            className="w-full resize-none rounded-md border border-input bg-background px-3 py-2.5 pr-12 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            style={{ maxHeight: "200px" }}
            disabled={isLoading}
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !input.trim()}
          className="shrink-0"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-center text-[10px] text-muted-foreground">
        Celestia Memoria searches indexed aviation documents. Always verify
        critical information against official sources.
      </p>
    </form>
  );
}
