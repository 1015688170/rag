import { useEffect, useState } from "react";

import { deleteDocument, fetchDocuments, fetchIngestTask, updateDocumentPermissions, uploadDocument } from "../lib/api";
import type { DocumentListItem, DocumentUploadResponse, EmbeddingModel, IngestTaskResponse } from "../types/chat";

interface DocumentManagerProps {
  selectedIndex: string;
  embeddingModel: EmbeddingModel;
  userId: string;
  department: string;
  rolesText: string;
}

const MAX_UPLOAD_SIZE = 20 * 1024 * 1024;

function normalizeRolesText(text: string): string {
  return text.replace(/^roles?\s*[:：]\s*/i, "").trim();
}

function parseTextList(text: string): string[] {
  return text
    .replace(/^[^:：]+[:：]\s*/, "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export function DocumentManager({ selectedIndex, embeddingModel, userId, department, rolesText }: DocumentManagerProps) {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<string>();
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse>();
  const [task, setTask] = useState<IngestTaskResponse>();
  const [visibility, setVisibility] = useState("public");
  const [ownerId, setOwnerId] = useState("");
  const [allowedDepartments, setAllowedDepartments] = useState("");
  const [allowedRoles, setAllowedRoles] = useState("");

  async function loadDocuments(): Promise<DocumentListItem[]> {
    setIsLoading(true);
    try {
      const response = await fetchDocuments({
        userId: userId.trim() || undefined,
        department: department.trim() || undefined,
        roles: normalizeRolesText(rolesText) || undefined,
      });
      setDocuments(response.documents);
      return response.documents;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to load documents.");
      return [];
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, [userId, department, rolesText]);

  async function handleUpload(file: File) {
    if (!selectedIndex || isUploading) {
      setStatus("请先选择 Azure AI Search 索引。");
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE) {
      setStatus(`文件过大：${formatSize(file.size)}，最大支持 20 MB。`);
      return;
    }
    setIsUploading(true);
    setStatus(`正在上传 ${file.name}...`);
    setTask(undefined);
    setUploadResult(undefined);
    try {
      const response = await uploadDocument({
        file,
        indexName: selectedIndex,
        embeddingModel,
        visibility,
        ownerId: ownerId.trim() || undefined,
        allowedDepartments: allowedDepartments.trim() || "[]",
        allowedRoles: allowedRoles.trim() || "[]",
      });
      setUploadResult(response);
      setStatus(`${response.filename}: ${response.status}，${response.chunk_count} 个分片。`);
      const taskResponse = await fetchIngestTask(response.task_id);
      setTask(taskResponse);
      await loadDocuments();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed.";
      const latestDocuments = await loadDocuments();
      const latestMatch = latestDocuments.find((document) => document.filename === file.name);
      if (latestMatch?.status === "success") {
        setStatus(`${file.name}: success，${latestMatch.chunk_count} 个分片。`);
      } else {
        setStatus(message);
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(documentId: string) {
    if (!selectedIndex) {
      setStatus("请先选择 Azure AI Search 索引。");
      return;
    }
    setStatus("正在删除文档...");
    try {
      const response = await deleteDocument({
        documentId,
        indexName: selectedIndex,
        embeddingModel,
        userId: userId.trim() || undefined,
        roles: normalizeRolesText(rolesText) || undefined,
      });
      setStatus(`已从 Azure AI Search 删除 ${response.deleted_chunks} 个分片。`);
      await loadDocuments();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Delete failed.");
    }
  }

  async function handleUpdatePermissions(documentId: string) {
    if (!selectedIndex) {
      setStatus("请先选择 Azure AI Search 索引。");
      return;
    }
    setStatus("正在更新文档权限...");
    try {
      const response = await updateDocumentPermissions({
        documentId,
        indexName: selectedIndex,
        embeddingModel,
        visibility,
        ownerId: ownerId.trim() || undefined,
        allowedDepartments: parseTextList(allowedDepartments),
        allowedRoles: parseTextList(allowedRoles),
        userId: userId.trim() || undefined,
        roles: normalizeRolesText(rolesText) || undefined,
      });
      setStatus(`已更新权限，并同步 ${response.updated_chunks} 个 Azure Search 分片。`);
      await loadDocuments();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "权限更新失败。");
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col rounded-[28px] border border-white/70 bg-white/75 p-5 shadow-panel backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-700">文档管理</p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-ink">知识文档管理</h2>
        </div>
        <button
          type="button"
          onClick={loadDocuments}
          disabled={isLoading || isUploading}
          className="rounded-full border border-line bg-white px-4 py-2 text-xs font-medium text-slate-600 transition hover:border-brand-500 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          刷新
        </button>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto pt-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <section className="rounded-2xl border border-line bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">上传文档</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">索引：{selectedIndex || "未选择"}</p>
            <div className="mt-4 space-y-3">
              <label className="block text-xs font-medium text-slate-500">
                可见范围
                <select
                  value={visibility}
                  disabled={isUploading}
                  onChange={(event) => setVisibility(event.target.value)}
                  className="mt-1 w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-semibold text-ink outline-none focus:border-brand-500"
                >
                  <option value="public">公开：所有人可见</option>
                  <option value="private">私有：仅 owner 可见</option>
                  <option value="department">部门：指定部门可见</option>
                  <option value="role">角色：指定角色可见</option>
                </select>
              </label>
              <input
                type="text"
                value={ownerId}
                disabled={isUploading}
                onChange={(event) => setOwnerId(event.target.value)}
                placeholder="文档所有者，例如 alice"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none placeholder:text-slate-400 focus:border-brand-500"
              />
              <input
                type="text"
                value={allowedDepartments}
                disabled={isUploading}
                onChange={(event) => setAllowedDepartments(event.target.value)}
                placeholder="允许部门，例如 sre,devops"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none placeholder:text-slate-400 focus:border-brand-500"
              />
              <input
                type="text"
                value={allowedRoles}
                disabled={isUploading}
                onChange={(event) => setAllowedRoles(event.target.value)}
                placeholder="允许角色，例如 admin,oncall"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none placeholder:text-slate-400 focus:border-brand-500"
              />
            </div>
            <label className="mt-4 flex cursor-pointer items-center justify-center rounded-2xl border border-dashed border-brand-200 bg-brand-50 px-4 py-8 text-center text-sm font-semibold text-brand-700 transition hover:border-brand-500 hover:bg-white">
              <input
                type="file"
                className="sr-only"
                accept=".json,.md,.txt,.docx,.pdf,application/json,application/pdf"
                disabled={isUploading || !selectedIndex}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.currentTarget.value = "";
                  if (file) {
                    handleUpload(file);
                  }
                }}
              />
              {isUploading ? "上传中..." : "选择文件"}
            </label>
            {status ? <p className="mt-3 text-xs leading-5 text-slate-500">{status}</p> : null}
          </section>

          {uploadResult ? (
            <section className="rounded-2xl border border-brand-100 bg-white p-4 text-sm text-slate-600">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">最近结果</p>
              <dl className="mt-3 space-y-2">
                <div className="flex justify-between gap-3">
                  <dt>状态</dt>
                  <dd className="font-medium text-brand-700">{uploadResult.status}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>分片</dt>
                  <dd>{uploadResult.chunk_count}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>权限</dt>
                  <dd>{uploadResult.visibility}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>Task</dt>
                  <dd className="max-w-[11rem] truncate">{uploadResult.task_id}</dd>
                </div>
              </dl>
              {task ? <p className="mt-3 text-xs leading-5 text-slate-500">Stage: {task.stage || task.status}</p> : null}
            </section>
          ) : null}
        </aside>

        <div className="min-h-0 overflow-x-auto rounded-2xl border border-line bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-[0.12em] text-slate-500">
              <tr>
                <th className="px-4 py-3">文件</th>
                <th className="px-4 py-3">类型</th>
                <th className="px-4 py-3">大小</th>
                <th className="px-4 py-3">分片</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">权限</th>
                <th className="px-4 py-3">创建时间</th>
                <th className="px-4 py-3">错误</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((document) => (
                <tr key={document.id} className="align-top">
                  <td className="max-w-[18rem] px-4 py-3 font-medium text-ink">{document.filename}</td>
                  <td className="px-4 py-3 text-slate-600">{document.file_type}</td>
                  <td className="px-4 py-3 text-slate-600">{formatSize(document.file_size)}</td>
                  <td className="px-4 py-3 text-slate-600">{document.chunk_count}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                      {document.status}
                    </span>
                  </td>
                  <td className="max-w-[16rem] px-4 py-3 text-xs leading-5 text-slate-600">
                    <div className="font-semibold text-ink">{document.visibility}</div>
                    <div>所有者：{document.owner_id || "-"}</div>
                    <div>部门：{document.allowed_departments.join(", ") || "-"}</div>
                    <div>角色：{document.allowed_roles.join(", ") || "-"}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(document.created_at)}</td>
                  <td className="max-w-[16rem] px-4 py-3 text-xs leading-5 text-red-600">{document.error_message}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      disabled={document.status === "deleted" || isUploading}
                      onClick={() => handleUpdatePermissions(document.id)}
                      className="mb-2 rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      应用权限
                    </button>
                    <button
                      type="button"
                      disabled={document.status === "deleted" || isUploading}
                      onClick={() => handleDelete(document.id)}
                      className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-red-300 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-sm text-slate-500">
                    {isLoading ? "加载中..." : "暂无文档"}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
