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

export interface ChatStreamEvent {
  type: "token" | "sources" | "done" | "error";
  data: string;
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
