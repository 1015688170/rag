interface ComposerProps {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function Composer(props: ComposerProps) {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="rounded-[24px] border border-line bg-white/90 p-3 shadow-panel backdrop-blur focus-within:border-brand-500">
        <textarea
          rows={3}
          value={props.value}
          disabled={props.isLoading}
          onChange={(event) => props.onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
              props.onSubmit();
            }
          }}
          placeholder="输入你的 RAG 测试问题。支持 Ctrl/Cmd + Enter 快速发送。"
          className="max-h-40 min-h-20 w-full resize-none border-none bg-transparent px-2 py-1 text-sm leading-7 text-ink outline-none placeholder:text-slate-400"
        />
        <div className="mt-2 flex items-center justify-between gap-4 border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-500">按当前左侧参数发送到 `/api/chat`</p>
          <button
            type="button"
            disabled={props.isLoading || !props.value.trim()}
            onClick={props.onSubmit}
            className="rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {props.isLoading ? "处理中..." : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}
