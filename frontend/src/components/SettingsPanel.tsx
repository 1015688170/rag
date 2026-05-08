import type { ChatModel, EmbeddingModel } from "../types/chat";

interface SettingsPanelProps {
  embeddingModel: EmbeddingModel;
  chatModel: ChatModel;
  selectedIndex: string;
  indexes: string[];
  topK: number;
  topN: number;
  promptTemplate: string;
  isLoading: boolean;
  isCreatingIndex: boolean;
  indexCreateStatus?: string;
  newIndexName: string;
  userId: string;
  department: string;
  rolesText: string;
  onEmbeddingModelChange: (value: EmbeddingModel) => void;
  onChatModelChange: (value: ChatModel) => void;
  onSelectedIndexChange: (value: string) => void;
  onNewIndexNameChange: (value: string) => void;
  onUserIdChange: (value: string) => void;
  onDepartmentChange: (value: string) => void;
  onRolesTextChange: (value: string) => void;
  onCreateIndex: () => void;
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
  { value: "claude-opus-4.5", label: "Claude Opus 4.5", hint: "更严谨，适合溯源问答" },
  { value: "gpt-4o", label: "GPT-4o", hint: "响应更快，适合多轮试验" },
];

function SelectField<T extends string>(props: {
  label: string;
  value: T;
  disabled: boolean;
  options: Array<{ value: T; label: string; hint: string }>;
  onChange: (value: T) => void;
}) {
  const currentOption = props.options.find((option) => option.value === props.value);

  return (
    <label className="block rounded-2xl border border-line bg-white/85 p-3 transition focus-within:border-brand-500">
      <span className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{props.label}</span>
      <div className="mt-2 rounded-2xl bg-slate-50 px-3 py-2">
        <select
          value={props.value}
          disabled={props.disabled}
          onChange={(event) => props.onChange(event.target.value as T)}
          className="w-full border-none bg-transparent p-0 text-sm font-semibold text-ink outline-none"
        >
          {props.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs leading-5 text-slate-500">{currentOption?.hint}</p>
      </div>
    </label>
  );
}

export function SettingsPanel(props: SettingsPanelProps) {
  const indexOptions = Array.from(
    new Set([...(props.selectedIndex ? [props.selectedIndex] : []), ...props.indexes]),
  );

  return (
    <aside className="relative overflow-hidden rounded-[28px] border border-white/70 bg-white/80 shadow-panel backdrop-blur xl:sticky xl:top-6 xl:h-[calc(100vh-3rem)]">
      <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-r from-brand-100 via-white to-emerald-50" />
      <div className="relative flex h-full flex-col">
        <div className="border-b border-slate-200/80 px-5 pb-4 pt-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-700">全局设置</p>
          <h1 className="mt-3 font-display text-[2rem] font-semibold text-ink">RAG 测试台</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">把实验参数收在左侧，右边专注问答和结果验证。</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <section className="space-y-3">
            <label className="block rounded-2xl border border-line bg-white/85 p-3 transition focus-within:border-brand-500">
              <span className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Search Index</span>
              <div className="mt-2 rounded-2xl bg-slate-50 px-3 py-2">
                <select
                  value={props.selectedIndex}
                  disabled={props.isLoading || indexOptions.length === 0}
                  onChange={(event) => props.onSelectedIndexChange(event.target.value)}
                  className="w-full border-none bg-transparent p-0 text-sm font-semibold text-ink outline-none"
                >
                  {indexOptions.length === 0 ? <option value="">No indexes</option> : null}
                  {indexOptions.map((indexName) => (
                    <option key={indexName} value={indexName}>
                      {indexName}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs leading-5 text-slate-500">当前索引用于检索和上传。</p>
                <input
                  type="text"
                  value={props.newIndexName}
                  disabled={props.isLoading || props.isCreatingIndex}
                  onChange={(event) => props.onNewIndexNameChange(event.target.value)}
                  placeholder="新索引名称"
                  className="mt-3 w-full rounded-full border border-line bg-white px-3 py-2 text-xs font-medium text-ink outline-none transition placeholder:text-slate-400 focus:border-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
                />
                <button
                  type="button"
                  disabled={props.isLoading || props.isCreatingIndex || !props.newIndexName.trim()}
                  onClick={props.onCreateIndex}
                  className="mt-3 w-full rounded-full border border-brand-200 bg-white px-3 py-2 text-xs font-semibold text-brand-700 transition hover:border-brand-500 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {props.isCreatingIndex ? "创建中..." : "创建索引"}
                </button>
                {props.indexCreateStatus ? (
                  <p className="mt-2 text-xs leading-5 text-slate-500">{props.indexCreateStatus}</p>
                ) : null}
              </div>
            </label>
            <SelectField
              label="Embedding"
              value={props.embeddingModel}
              disabled={props.isLoading}
              options={embeddingOptions}
              onChange={props.onEmbeddingModelChange}
            />
            <SelectField
              label="Chat Model"
              value={props.chatModel}
              disabled={props.isLoading}
              options={chatOptions}
              onChange={props.onChatModelChange}
            />
          </section>

          <section className="rounded-2xl border border-line bg-white/85 p-3">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">当前用户身份</p>
            <div className="mt-3 space-y-3">
              <input
                type="text"
                value={props.userId}
                disabled={props.isLoading}
                onChange={(event) => props.onUserIdChange(event.target.value)}
                placeholder="用户ID，例如 alice"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none transition placeholder:text-slate-400 focus:border-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
              />
              <input
                type="text"
                value={props.department}
                disabled={props.isLoading}
                onChange={(event) => props.onDepartmentChange(event.target.value)}
                placeholder="部门，例如 sre"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none transition placeholder:text-slate-400 focus:border-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
              />
              <input
                type="text"
                value={props.rolesText}
                disabled={props.isLoading}
                onChange={(event) => props.onRolesTextChange(event.target.value)}
                placeholder="角色，例如 admin,oncall"
                className="w-full rounded-full border border-line bg-slate-50 px-3 py-2 text-xs font-medium text-ink outline-none transition placeholder:text-slate-400 focus:border-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
              />
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-white/85 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Retrieval</p>
                <p className="mt-1 text-sm text-slate-600">先召回，再重排。</p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <label className="block rounded-2xl bg-slate-50 px-3 py-2">
                <span className="block text-xs font-medium text-slate-500">Recall Top-K</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={props.topK}
                  disabled={props.isLoading}
                  onChange={(event) => props.onTopKChange(Number(event.target.value))}
                  className="mt-1 w-full border-none bg-transparent p-0 text-lg font-semibold text-ink outline-none"
                />
                <p className="mt-1 text-[11px] leading-4 text-slate-500">召回候选数量</p>
              </label>

              <label className="block rounded-2xl bg-slate-50 px-3 py-2">
                <span className="block text-xs font-medium text-slate-500">Rerank Top-N</span>
                <input
                  type="number"
                  min={1}
                  max={Math.min(10, props.topK)}
                  value={props.topN}
                  disabled={props.isLoading}
                  onChange={(event) => props.onTopNChange(Number(event.target.value))}
                  className="mt-1 w-full border-none bg-transparent p-0 text-lg font-semibold text-ink outline-none"
                />
                <p className="mt-1 text-[11px] leading-4 text-slate-500">送入大模型数量</p>
              </label>
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-white/85 p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Prompt</p>
                <p className="mt-1 text-sm text-slate-600">在线调系统提示词。</p>
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
              rows={7}
              value={props.promptTemplate}
              disabled={props.isLoading}
              onChange={(event) => props.onPromptTemplateChange(event.target.value)}
              className="mt-3 h-52 w-full resize-none rounded-2xl border border-line bg-slate-50 px-3 py-3 text-xs leading-6 text-ink outline-none transition focus:border-brand-500 focus:bg-white"
            />
          </section>

          <section className="rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50 to-white p-4">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Snapshot</p>
            <dl className="mt-3 space-y-2 text-sm text-slate-600">
              <div className="flex items-center justify-between gap-4">
                <dt>Embedding</dt>
                <dd className="rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700">{props.embeddingModel}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt>Index</dt>
                <dd className="max-w-[12rem] truncate rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700">{props.selectedIndex || "Not selected"}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt>Chat</dt>
                <dd className="rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700">{props.chatModel}</dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt>策略</dt>
                <dd className="max-w-[11rem] text-right text-xs leading-5">Hybrid Search → BGE-M3 Rerank → Grounded Generation</dd>
              </div>
            </dl>
          </section>
        </div>
      </div>
    </aside>
  );
}
