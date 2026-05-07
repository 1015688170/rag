import type { ChatRequest, ChatResponse, DocumentUploadResponse, EmbeddingModel, IndexListResponse } from "../types/chat";

const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const API_BASE_URL = (RAW_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

function buildApiUrl(path: string): string {
  // Supports both:
  // - VITE_API_BASE_URL="http://127.0.0.1:8000"  -> /api/chat
  // - VITE_API_BASE_URL="/api" or ".../api"       -> /chat
  const baseHasApi = API_BASE_URL === "/api" || API_BASE_URL.endsWith("/api");
  return `${API_BASE_URL}${baseHasApi ? "" : "/api"}${path}`;
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(buildApiUrl("/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const data = await response.json();
      message = data.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json();
}

export async function fetchIndexes(): Promise<IndexListResponse> {
  const response = await fetch(buildApiUrl("/indexes"));
  if (!response.ok) {
    throw new Error(response.statusText || "Failed to fetch indexes.");
  }
  return response.json();
}

export async function uploadDocument(payload: {
  file: File;
  indexName: string;
  embeddingModel: EmbeddingModel;
}): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("index_name", payload.indexName);
  formData.append("embedding_model", payload.embeddingModel);

  const response = await fetch(buildApiUrl("/documents/upload"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = "Upload failed.";
    try {
      const data = await response.json();
      message = data.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json();
}

export default sendChatMessage;
