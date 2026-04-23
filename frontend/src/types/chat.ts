export type EmbeddingModel = "ada-002" | "google-005";
export type ChatModel = "gpt-4o" | "claude-opus-4.5";

export interface ChatRequest {
  question: string;
  embedding_model: EmbeddingModel;
  chat_model: ChatModel;
  top_k: number;
  top_n: number;
}

export interface SourceItem {
  doc_id: string;
  filepath: string;
  score: number;
  preview: string;
  content: string;
}

export interface ChatResponse {
  answer: string;
  model: ChatModel;
  embedding_model: EmbeddingModel;
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
