import { useState } from "react";

import type { SourceItem } from "../types/chat";

interface SourcesPanelProps {
  sources: SourceItem[];
}

function formatScore(score?: number | null): string {
  return typeof score === "number" ? score.toFixed(4) : "N/A";
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
          <p className="mt-1 text-xs text-slate-500">共 {sources.length} 条，查看切片预览、路径、召回分和重排分</p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-brand-700">
          {open ? "收起" : "展开"}
        </span>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-brand-100 px-4 py-4">
          {sources.map((source, index) => (
            <article key={`${source.doc_id}-${index}`} className="rounded-2xl border border-white bg-white p-4">
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
              </div>
              <p className="mt-3 break-all text-sm font-medium text-ink">{source.filepath}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{source.preview}</p>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}
