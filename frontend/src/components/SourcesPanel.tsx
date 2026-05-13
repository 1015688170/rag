import { useState } from "react";

import type { SourceItem } from "../types/chat";

interface SourcesPanelProps {
  sources: SourceItem[];
}

function formatScore(score?: number | null): string {
  return typeof score === "number" ? score.toFixed(4) : "N/A";
}

function formatPageRange(source: SourceItem): string | null {
  if (typeof source.page_start !== "number" && typeof source.page_end !== "number") {
    return null;
  }
  if (source.page_start === source.page_end || typeof source.page_end !== "number") {
    return `p.${source.page_start}`;
  }
  if (typeof source.page_start !== "number") {
    return `p.${source.page_end}`;
  }
  return `p.${source.page_start}-${source.page_end}`;
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [open, setOpen] = useState(false);

  if (!sources.length) {
    return null;
  }

  return (
    <div className="mt-4 rounded-2xl border border-brand-100 bg-brand-50/60">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <p className="text-sm font-semibold text-ink">参考数据源 (Sources)</p>
          <p className="mt-1 text-xs text-slate-500">共 {sources.length} 条，查看切片预览、章节、页码、召回分和重排分</p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-brand-700">
          {open ? "收起" : "展开"}
        </span>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-brand-100 px-4 py-4">
          {sources.map((source, index) => {
            const pageRange = formatPageRange(source);
            return (
              <article key={`${source.doc_id}-${index}`} className="rounded-lg border border-white bg-white p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    #{index + 1}
                  </span>
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-accent">
                    {source.score_source === "recall" ? "召回分" : "重排分"} {formatScore(source.score)}
                  </span>
                  <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                    recall {formatScore(source.recall_score)}
                  </span>
                  {source.rerank_score == null ? (
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                      重排不可用
                    </span>
                  ) : null}
                  {source.source_type ? (
                    <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium uppercase text-blue-700">
                      {source.source_type}
                    </span>
                  ) : null}
                  {pageRange ? (
                    <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
                      {pageRange}
                    </span>
                  ) : null}
                </div>

                <div className="mt-3 space-y-1">
                  <p className="break-all text-sm font-medium text-ink">{source.filename || source.filepath}</p>
                  {source.filename ? <p className="break-all text-xs text-slate-500">{source.filepath}</p> : null}
                  {source.section_title || source.section_path ? (
                    <p className="text-xs text-slate-500">
                      {source.section_title || source.section_path}
                      {source.chunk_index != null ? ` · chunk #${source.chunk_index}` : ""}
                    </p>
                  ) : null}
                  {source.source_doc_id ? (
                    <p className="break-all text-xs text-slate-400">doc {source.source_doc_id}</p>
                  ) : null}
                </div>

                <p className="mt-2 text-sm leading-6 text-slate-600">{source.preview}</p>
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
