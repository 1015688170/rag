interface ComposerProps {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function Composer(props: ComposerProps) {
  return (
    <div className="rounded-[28px] border border-white/70 bg-white/80 p-4 shadow-panel backdrop-blur">
      <div className="rounded-[22px] border border-line bg-slate-50 p-3 focus-within:border-brand-500 focus-within:bg-white">
        <textarea
          rows={4}
          value={props.value}
          disabled={props.isLoading}
          onChange={(event) => props.onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
              props.onSubmit();
            }
          }}
          placeholder="输入你的 RAG 测试问题。支持 Ctrl/Cmd + Enter 快速发送。"
          className="w-full resize-none border-none bg-transparent text-sm leading-7 text-ink outline-none placeholder:text-slate-400"
        />
      </div>
      <div className="mt-3 flex items-center justify-between gap-4">
        <p className="text-xs text-slate-500">问题会按左侧设置直接送往后端 `/api/chat`。</p>
        <button
          type="button"
          disabled={props.isLoading || !props.value.trim()}
          onClick={props.onSubmit}
          className="rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {props.isLoading ? "处理中..." : "发送问题"}
        </button>
      </div>
    </div>
  );
}
