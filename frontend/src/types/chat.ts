export type EmbeddingModel = "ada-002" | "google-005";
export type ChatModel = "gpt-4o" | "claude-opus-4.5";

export interface ChatRequest {
  question: string;
  index_name?: string;
  embedding_model: EmbeddingModel;
  chat_model: ChatModel;
  top_k: number;
  top_n: number;
  prompt_template?: string;
}

export interface SourceItem {
  doc_id: string;
  filepath: string;
  score: number;
  rerank_score?: number | null;
  recall_score?: number | null;
  score_source?: "rerank" | "recall" | string;
  preview: string;
  content: string;
}

export interface ChatResponse {
  answer: string;
  model: ChatModel;
  embedding_model: EmbeddingModel;
  index_name: string;
  source_count: number;
  sources: SourceItem[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceItem[];
  meta?: string;
  isError?: boolean;
}

export interface IndexListResponse {
  indexes: string[];
  defaults: Record<string, string>;
}

export interface SearchIndexCreateRequest {
  index_name?: string;
  embedding_model: EmbeddingModel;
}

export interface SearchIndexCreateResponse {
  index_name: string;
  status: string;
  message: string;
  embedding_model: EmbeddingModel;
  vector_dimensions: number;
}

export interface DocumentUploadResponse {
  index_name: string;
  filename: string;
  embedding_model: EmbeddingModel;
  document_id: string;
  task_id: string;
  file_hash: string;
  chunk_count: number;
  status: string;
}

export interface DocumentListItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
}

export interface IngestTaskResponse {
  task_id: string;
  document_id: string;
  filename: string;
  status: string;
  stage?: string | null;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDeleteResponse {
  document_id: string;
  status: string;
  deleted_chunks: number;
}
