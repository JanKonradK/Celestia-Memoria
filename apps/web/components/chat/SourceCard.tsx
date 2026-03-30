"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface SourceCardProps {
  source: {
    index: number;
    label: string;
    doc_name?: string;
    section_path?: string;
    page_number?: number | null;
    chunk_text?: string;
    doc_type?: string;
    aerodrome_icao?: string;
  };
}

export function SourceCard({ source }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-md border bg-background text-foreground">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-muted/50"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="font-medium">[{source.label}]</span>
        {source.doc_name && (
          <span className="truncate text-muted-foreground">
            {source.doc_name}
            {source.section_path && ` — ${source.section_path}`}
          </span>
        )}
        {source.page_number != null && (
          <span className="ml-auto shrink-0 text-muted-foreground">
            p. {source.page_number}
          </span>
        )}
      </button>

      {expanded && source.chunk_text && (
        <div className="border-t px-3 py-2">
          <p className="text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap">
            {source.chunk_text}
          </p>
          {(source.doc_type || source.aerodrome_icao) && (
            <div className="mt-2 flex gap-2">
              {source.doc_type && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                  {source.doc_type}
                </span>
              )}
              {source.aerodrome_icao && source.aerodrome_icao !== "GLOBAL" && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                  {source.aerodrome_icao}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
