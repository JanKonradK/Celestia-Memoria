export type DocumentType =
  | "AIP"
  | "AIP_SUP"
  | "UNIT_MANUAL"
  | "ICAO_DOC"
  | "EASA_REG"
  | "PROCEDURE_CHANGE"
  | "LOA";

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export interface DocumentMetadata {
  document_id: string;
  doc_name: string;
  doc_type: DocumentType;
  aerodrome_icao: string;
  effective_date: string | null;
  expiry_date: string | null;
  is_current: boolean;
  status: DocumentStatus;
  chunk_count: number | null;
  storage_path: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  section_path: string;
  page_number: number | null;
  token_count: number;
  clause_id: string;
  clause_references: string[];
}

export interface ChunkWithScore extends DocumentChunk {
  score: number;
  doc_name: string;
  doc_type: DocumentType;
  aerodrome_icao: string;
}

export interface SourceReference {
  source_index: number;
  doc_name: string;
  doc_type: DocumentType;
  section_path: string;
  page_number: number | null;
  chunk_text: string;
  aerodrome_icao: string;
  clause_id: string;
  cited_clause: string;
}
