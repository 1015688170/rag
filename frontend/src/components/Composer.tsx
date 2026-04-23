interface ComposerProps {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function Composer(props: ComposerProps) {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="rounded-[28px] border border-line bg-white/95 p-3 shadow-panel backdrop-blur">
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
          placeholder="有问题，尽管问"
          className="h-28 w-full resize-none border-none bg-transparent px-3 py-2 text-sm leading-7 text-ink outline-none placeholder:text-slate-400"
        />
        <div className="flex items-center justify-between gap-4 border-t border-slate-100 px-2 pt-3">
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
