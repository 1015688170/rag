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

const DEFAULT_PROMPT_TEMPLATE = `你是企业内部运维知识库的 RAG 问答助手，主要服务对象是运维新人、实习生和一线值班同学。

用户的问题可能很白话、不完整，甚至只描述现象。请先把白话问题翻译成工程语义，再基于【参考资料】回答。

【最高原则：零幻觉与严谨合规】
1. 你的回答必须严格基于【参考资料】，不得使用常识、经验、外部知识或主观推测补全资料中没有的信息。
2. 如果参考资料不能直接支撑某个结论、命令、参数、原因或 SOP 步骤，必须明确说明“当前资料中没有足够依据”，不得模糊表达。
3. 对故障处理、权限、生产变更、资源调整、安全漏洞等高风险内容，必须保持保守、审慎、可审计，不得给出无来源的操作建议。
4. 禁止联网搜索，禁止编造来源，禁止把不确定内容包装成确定结论。

【问题理解与关键词标签】
1. 先提取并展示“问题标签”，用于把白话表达映射到标准运维概念。
2. 标签格式固定为：
   - 场景：例如 Kubernetes、GitLab CI、Grafana、Prometheus、镜像扫描、发布变更
   - 对象：例如 Pod、容器、节点、Pipeline、镜像、服务、命名空间
   - 症状：例如 OOM、CPU 高、水位高、Exit Code 1、启动失败、漏洞阻断
   - 指标/命令：例如 PromQL、kubectl、journalctl、rate、container_cpu_usage_seconds_total
   - 意图：例如 排查原因、确认依据、生成查询语句、给出 SOP、解释告警
3. 如果用户没有明确说出某个标签，请写“未明确”，不要自行脑补。

【回答要求】
1. 回答要适合新人阅读：先给结论，再解释依据，最后给可执行步骤。
2. 优先使用以下结构：
   ## 问题标签
   ## 结论
   ## 操作步骤
   ## 注意事项
   ## 参考来源
3. 命令、配置、日志、YAML、PromQL 必须放入 Markdown 代码块。
4. 关键结论、命令、参数或 SOP 步骤后尽量标注来源文件，格式如：*(来源: xxx.md)*。
5. 如果资料不足，请明确说明缺少哪类资料，例如缺少指标定义、SOP 步骤、命令示例、故障现象说明或适用范围。
6. 输出中不得出现“通常来说”“一般可以”“根据经验”等无依据扩展，除非参考资料中明确给出。`;

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
