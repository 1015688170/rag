import { useState } from "react";

import { Composer } from "./components/Composer";
import { MessageBubble } from "./components/MessageBubble";
import { SettingsPanel } from "./components/SettingsPanel";
import { createId } from "./lib/id";
import { sendChatMessage } from "./lib/api";
import type { ChatMessage, ChatModel, EmbeddingModel } from "./types/chat";

const initialMessages: ChatMessage[] = [];

const exampleQuestions = [
  "如何判断 Kubernetes Pod 是否发生 OOM？",
  "GitLab CI 扫描发现 HIGH 漏洞后应该怎么处理？",
  "请给我一份生产故障排查 SOP",
  "哪些日志或命令可以辅助定位问题？",
];

const DEFAULT_PROMPT_TEMPLATE = `你是一个严谨的 RAG 问答助手。

请只基于【参考资料】回答用户问题；如果资料不足，请明确说明“当前资料中没有足够依据”。
回答要求：
1. 优先用分段标题、列表和代码块组织内容。
2. 命令、配置、日志、YAML、PromQL 必须放入 Markdown 代码块。
3. 关键结论后尽量标注来源文件，格式如：*(来源: xxx.md)*。
4. 不要编造参考资料里没有的信息。`;

function clampNumber(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(Math.max(value, min), max);
}

function EmptyConversation({ onPickQuestion }: { onPickQuestion: (question: string) => void }) {
  return (
    <div className="flex min-h-[42vh] flex-col items-center justify-center px-6 py-12 text-center">
      <p className="font-display text-3xl font-semibold text-ink">今天想测试什么？</p>
      <div className="mt-8 grid w-full max-w-3xl gap-3 sm:grid-cols-2">
        {exampleQuestions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onPickQuestion(question)}
            className="rounded-2xl border border-line bg-white/80 px-4 py-3 text-left text-sm leading-6 text-slate-700 shadow-sm transition hover:border-brand-500 hover:bg-white hover:text-ink"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [embeddingModel, setEmbeddingModel] = useState<EmbeddingModel>("ada-002");
  const [chatModel, setChatModel] = useState<ChatModel>("claude-opus-4.5");
  const [topK, setTopK] = useState(10);
  const [topN, setTopN] = useState(5);
  const [promptTemplate, setPromptTemplate] = useState(DEFAULT_PROMPT_TEMPLATE);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const hasConversation = messages.length > 0;

  async function handleSubmit() {
    const question = draft.trim();
    if (!question || isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: question,
      meta: `${embeddingModel} / ${chatModel}`,
    };

    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        question,
        embedding_model: embeddingModel,
        chat_model: chatModel,
        top_k: topK,
        top_n: Math.min(topN, topK),
        prompt_template: promptTemplate,
      });

      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          meta: `${response.embedding_model} / ${response.model} / ${response.source_count} sources`,
        },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: message,
          isError: true,
          meta: "后端请求失败",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(22,119,255,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(15,118,110,0.12),_transparent_24%),linear-gradient(180deg,_#f9fbfe_0%,_#eef4fa_100%)] px-4 py-6 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <SettingsPanel
          embeddingModel={embeddingModel}
          chatModel={chatModel}
          topK={topK}
          topN={topN}
          isLoading={isLoading}
          onEmbeddingModelChange={setEmbeddingModel}
          onChatModelChange={setChatModel}
          onTopKChange={(value) => {
            const nextTopK = clampNumber(value, 1, 20);
            setTopK(nextTopK);
            setTopN((current) => clampNumber(current, 1, Math.min(10, nextTopK)));
          }}
          onTopNChange={(value) => setTopN(clampNumber(value, 1, Math.min(10, topK)))}
          promptTemplate={promptTemplate}
          onPromptTemplateChange={setPromptTemplate}
          onPromptTemplateReset={() => setPromptTemplate(DEFAULT_PROMPT_TEMPLATE)}
        />

        <main className="flex h-[calc(100vh-3rem)] min-h-0 flex-col">
          <section
            className={
              hasConversation
                ? "flex min-h-0 flex-1 flex-col rounded-[28px] border border-white/70 bg-white/65 p-5 shadow-panel backdrop-blur"
                : "flex min-h-0 flex-1 items-center justify-center"
            }
          >
            {hasConversation ? (
              <>
                <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-700">Conversation</p>
                    <h2 className="mt-2 font-display text-2xl font-semibold text-ink">对话交互区</h2>
                  </div>
                  <div className="rounded-full bg-slate-100 px-4 py-2 text-xs font-medium text-slate-600">
                    {isLoading ? "RAG pipeline running" : "Ready"}
                  </div>
                </div>

                <div className="mt-5 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                </div>
              </>
            ) : (
              <EmptyConversation onPickQuestion={setDraft} />
            )}
          </section>

          <div className="mt-5 shrink-0">
            <Composer value={draft} isLoading={isLoading} onChange={setDraft} onSubmit={handleSubmit} />
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
