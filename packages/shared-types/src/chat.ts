import type { SourceReference, DocumentType } from "./documents";

export type MessageRole = "user" | "assistant" | "system";

export type QueryIntent = "regulation_lookup" | "procedure_check" | "general";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceReference[];
  created_at: string;
}

export interface AgentState {
  messages: ChatMessage[];
  intent: QueryIntent | null;
  requires_rag: boolean;
  query_rewrite: string | null;
  retrieved_chunks: ChunkResult[];
  reranked_chunks: ChunkResult[];
  final_response: string | null;
  sources: SourceReference[];
  node_trace: string[];
  model_slug: string;
  aerodrome_icao: string;
}

export interface ChunkResult {
  chunk_id: string;
  chunk_text: string;
  score: number;
  document_id: string;
  doc_name: string;
  doc_type: DocumentType;
  section_path: string;
  page_number: number | null;
  aerodrome_icao: string;
}

export interface RouterOutput {
  intent: QueryIntent;
  requires_rag: boolean;
  query_rewrite: string;
}
