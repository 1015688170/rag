import type { ChatRequest, ChatResponse } from "../types/chat";

const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const API_BASE_URL = (RAW_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

function buildChatUrl(): string {
  // Supports both:
  // - VITE_API_BASE_URL="http://127.0.0.1:8000"  -> /api/chat
  // - VITE_API_BASE_URL="/api" or ".../api"       -> /chat
  const baseHasApi = API_BASE_URL === "/api" || API_BASE_URL.endsWith("/api");
  return `${API_BASE_URL}${baseHasApi ? "" : "/api"}/chat`;
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(buildChatUrl(), {
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

export default sendChatMessage;
