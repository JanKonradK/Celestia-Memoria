import type { DocumentType, DocumentMetadata } from "./documents";

export interface IngestRequest {
  document_id: string;
  storage_path: string;
  doc_name: string;
  doc_type: DocumentType;
  aerodrome_icao: string;
  effective_date?: string;
  expiry_date?: string;
}

export interface IngestResponse {
  status: "processing" | "error";
  document_id: string;
  message?: string;
}

export interface ChatRequest {
  message: string;
  aerodrome_icao?: string;
  model_slug?: string;
}

/** LangServe streaming event (JSONPatch format). */
export interface ChatStreamEvent {
  ops: Array<{
    path: string;
    op: "replace" | "add" | "remove";
    value?: unknown;
  }>;
}

export interface HealthResponse {
  status: "ok";
  version: string;
  mode: "production" | "local";
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  total: number;
}

export interface ErrorResponse {
  detail: string;
  status_code: number;
}
