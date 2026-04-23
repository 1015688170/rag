import type { ChatModel, EmbeddingModel } from "../types/chat";

interface SettingsPanelProps {
  embeddingModel: EmbeddingModel;
  chatModel: ChatModel;
  topK: number;
  topN: number;
  promptTemplate: string;
  isLoading: boolean;
  onEmbeddingModelChange: (value: EmbeddingModel) => void;
  onChatModelChange: (value: ChatModel) => void;
  onTopKChange: (value: number) => void;
  onTopNChange: (value: number) => void;
  onPromptTemplateChange: (value: string) => void;
  onPromptTemplateReset: () => void;
}

const embeddingOptions: Array<{ value: EmbeddingModel; label: string; hint: string }> = [
  { value: "ada-002", label: "Ada-002", hint: "1536 维，适合当前 Azure 索引" },
  { value: "google-005", label: "Google-005", hint: "768 维，适合 005 索引" },
];

const chatOptions: Array<{ value: ChatModel; label: string; hint: string }> = [
  { value: "claude-opus-4.5", label: "Claude Opus 4.5", hint: "严谨合规，适合溯源问答" },
  { value: "gpt-4o", label: "GPT-4o", hint: "响应更快，适合多轮试验" },
];

export function SettingsPanel(props: SettingsPanelProps) {
  return (
    <aside className="relative overflow-hidden rounded-[28px] border border-white/70 bg-white/75 p-6 shadow-panel backdrop-blur xl:min-h-[calc(100vh-4rem)]">
      <div className="absolute inset-x-0 top-0 h-28 bg-gradient-to-r from-brand-100 via-white to-emerald-50" />
      <div className="relative space-y-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-700">Global Settings</p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-ink">RAG 测试台</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            左侧固定实验参数，右侧专注做问答和结果溯源。每条回复都会挂带检索切片与重排分数。
          </p>
        </div>

        <section className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">检索向量模型</span>
            <select
              value={props.embeddingModel}
              disabled={props.isLoading}
              onChange={(event) => props.onEmbeddingModelChange(event.target.value as EmbeddingModel)}
              className="w-full rounded-2xl border border-line bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:bg-white"
            >
              {embeddingOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              {embeddingOptions.find((item) => item.value === props.embeddingModel)?.hint}
            </p>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">对话大模型</span>
            <select
              value={props.chatModel}
              disabled={props.isLoading}
              onChange={(event) => props.onChatModelChange(event.target.value as ChatModel)}
              className="w-full rounded-2xl border border-line bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:bg-white"
            >
              {chatOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              {chatOptions.find((item) => item.value === props.chatModel)?.hint}
            </p>
          </label>
        </section>

        <section className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Recall Top-K</span>
            <input
              type="number"
              min={1}
              max={20}
              value={props.topK}
              disabled={props.isLoading}
              onChange={(event) => props.onTopKChange(Number(event.target.value))}
              className="w-full rounded-2xl border border-line bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:bg-white"
            />
            <p className="mt-2 text-xs leading-5 text-slate-500">第一阶段从 Azure Search 召回的候选切片数量，越大越全但更慢。</p>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Rerank Top-N</span>
            <input
              type="number"
              min={1}
              max={Math.min(10, props.topK)}
              value={props.topN}
              disabled={props.isLoading}
              onChange={(event) => props.onTopNChange(Number(event.target.value))}
              className="w-full rounded-2xl border border-line bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:bg-white"
            />
            <p className="mt-2 text-xs leading-5 text-slate-500">第二阶段 BGE 重排后送入大模型的切片数量，不能大于 Top-K。</p>
          </label>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-ink">提示词模板</p>
              <p className="mt-1 text-xs text-slate-500">在线调整系统提示词，本次提问会随请求一起发送。</p>
            </div>
            <button
              type="button"
              disabled={props.isLoading}
              onClick={props.onPromptTemplateReset}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-500 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              恢复默认
            </button>
          </div>
          <textarea
            rows={8}
            value={props.promptTemplate}
            disabled={props.isLoading}
            onChange={(event) => props.onPromptTemplateChange(event.target.value)}
            className="w-full resize-y rounded-2xl border border-line bg-slate-50 px-4 py-3 text-xs leading-6 text-ink outline-none transition focus:border-brand-500 focus:bg-white"
          />
        </section>

        <section className="rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 to-white p-5">
          <p className="text-sm font-semibold text-ink">当前实验快照</p>
          <dl className="mt-4 space-y-3 text-sm text-slate-600">
            <div className="flex items-center justify-between gap-4">
              <dt>Embedding</dt>
              <dd className="rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700">{props.embeddingModel}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt>Chat Model</dt>
              <dd className="rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700">{props.chatModel}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt>策略</dt>
              <dd className="text-right text-xs leading-5">Hybrid Search → BGE-M3 Rerank → Grounded Generation</dd>
            </div>
          </dl>
        </section>
      </div>
    </aside>
  );
}
