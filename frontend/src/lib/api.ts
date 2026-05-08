import type {
  ChatRequest,
  ChatResponse,
  DocumentDeleteResponse,
  DocumentListResponse,
  DocumentPermissionUpdateResponse,
  DocumentUploadResponse,
  EmbeddingModel,
  IndexListResponse,
  IngestTaskResponse,
  SearchIndexCreateRequest,
  SearchIndexCreateResponse,
} from "../types/chat";

const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const API_BASE_URL = (RAW_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

function buildApiUrl(path: string): string {
  // Supports both:
  // - VITE_API_BASE_URL="http://127.0.0.1:8000"  -> /api/chat
  // - VITE_API_BASE_URL="/api" or ".../api"       -> /chat
  const baseHasApi = API_BASE_URL === "/api" || API_BASE_URL.endsWith("/api");
  return `${API_BASE_URL}${baseHasApi ? "" : "/api"}${path}`;
}

async function parseError(response: Response, fallback: string, emitAuthExpired = true): Promise<string> {
  if (response.status === 401) {
    if (emitAuthExpired && typeof window !== "undefined") {
      window.dispatchEvent(new Event("rag-auth-expired"));
    }
    try {
      const data = await response.json();
      return data.detail ?? "Not authenticated";
    } catch {
      return "Not authenticated";
    }
  }
  try {
    const data = await response.json();
    return data.detail ?? fallback;
  } catch {
    return response.statusText || fallback;
  }
}

export async function login(username: string, password: string): Promise<{ authenticated: boolean; username: string }> {
  const response = await fetch(buildApiUrl("/auth/login"), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Login failed.", false));
  }
  return response.json();
}

export async function logout(): Promise<{ authenticated: boolean }> {
  const response = await fetch(buildApiUrl("/auth/logout"), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Logout failed."));
  }
  return response.json();
}

export async function fetchCurrentUser(): Promise<{ authenticated: boolean; username: string }> {
  const response = await fetch(buildApiUrl("/auth/me"), {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Not authenticated", false));
  }
  return response.json();
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(buildApiUrl("/chat"), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Request failed."));
  }

  return response.json();
}

export async function fetchIndexes(): Promise<IndexListResponse> {
  const response = await fetch(buildApiUrl("/indexes"), {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to fetch indexes."));
  }
  return response.json();
}

export async function createSearchIndex(payload: SearchIndexCreateRequest): Promise<SearchIndexCreateResponse> {
  const response = await fetch(buildApiUrl("/search-index/create"), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Index creation failed."));
  }

  return response.json();
}

export async function uploadDocument(payload: {
  file: File;
  indexName: string;
  embeddingModel: EmbeddingModel;
  visibility?: string;
  ownerId?: string;
  allowedDepartments?: string[] | string;
  allowedRoles?: string[] | string;
}): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("index_name", payload.indexName);
  formData.append("embedding_model", payload.embeddingModel);
  formData.append("visibility", payload.visibility || "public");
  if (payload.ownerId) {
    formData.append("owner_id", payload.ownerId);
  }
  formData.append(
    "allowed_departments",
    Array.isArray(payload.allowedDepartments) ? payload.allowedDepartments.join(",") : payload.allowedDepartments || "[]",
  );
  formData.append(
    "allowed_roles",
    Array.isArray(payload.allowedRoles) ? payload.allowedRoles.join(",") : payload.allowedRoles || "[]",
  );

  const response = await fetch(buildApiUrl("/documents/upload"), {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    if (response.status === 413) {
      throw new Error("File is too large for the server/proxy. Check Nginx client_max_body_size; app limit is 20 MB.");
    }
    if (response.status === 504) {
      throw new Error("Upload request timed out at the gateway. The backend may still be processing; refresh the document list to confirm status.");
    }
    throw new Error(await parseError(response, "Upload failed."));
  }

  return response.json();
}

export async function fetchDocuments(payload?: {
  userId?: string;
  department?: string;
  roles?: string;
}): Promise<DocumentListResponse> {
  const params = new URLSearchParams();
  if (payload?.userId) {
    params.set("user_id", payload.userId);
  }
  if (payload?.department) {
    params.set("department", payload.department);
  }
  if (payload?.roles) {
    params.set("roles", payload.roles);
  }
  const query = params.toString();
  const response = await fetch(buildApiUrl(`/documents${query ? `?${query}` : ""}`), {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to fetch documents."));
  }
  return response.json();
}

export async function fetchIngestTask(taskId: string): Promise<IngestTaskResponse> {
  const response = await fetch(buildApiUrl(`/ingest-tasks/${encodeURIComponent(taskId)}`), {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to fetch ingest task."));
  }
  return response.json();
}

export async function deleteDocument(payload: {
  documentId: string;
  indexName: string;
  embeddingModel: EmbeddingModel;
  userId?: string;
  roles?: string;
}): Promise<DocumentDeleteResponse> {
  const params = new URLSearchParams({
    index_name: payload.indexName,
    embedding_model: payload.embeddingModel,
  });
  if (payload.userId) {
    params.set("user_id", payload.userId);
  }
  if (payload.roles) {
    params.set("roles", payload.roles);
  }
  const response = await fetch(buildApiUrl(`/documents/${encodeURIComponent(payload.documentId)}?${params}`), {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Delete failed."));
  }
  return response.json();
}

export async function updateDocumentPermissions(payload: {
  documentId: string;
  indexName: string;
  embeddingModel: EmbeddingModel;
  visibility: string;
  ownerId?: string;
  allowedDepartments?: string[] | string;
  allowedRoles?: string[] | string;
  userId?: string;
  roles?: string;
}): Promise<DocumentPermissionUpdateResponse> {
  const params = new URLSearchParams({
    index_name: payload.indexName,
    embedding_model: payload.embeddingModel,
  });
  if (payload.userId) {
    params.set("user_id", payload.userId);
  }
  if (payload.roles) {
    params.set("roles", payload.roles);
  }
  const response = await fetch(
    buildApiUrl(`/documents/${encodeURIComponent(payload.documentId)}/permissions?${params}`),
    {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        visibility: payload.visibility,
        owner_id: payload.ownerId || null,
        allowed_departments: Array.isArray(payload.allowedDepartments)
          ? payload.allowedDepartments
          : payload.allowedDepartments
            ? payload.allowedDepartments.split(",").map((item) => item.trim()).filter(Boolean)
            : [],
        allowed_roles: Array.isArray(payload.allowedRoles)
          ? payload.allowedRoles
          : payload.allowedRoles
            ? payload.allowedRoles.split(",").map((item) => item.trim()).filter(Boolean)
            : [],
      }),
    },
  );
  if (!response.ok) {
    throw new Error(await parseError(response, "Permission update failed."));
  }
  return response.json();
}

export default sendChatMessage;
