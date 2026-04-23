from __future__ import annotations

import os
from typing import Any, Optional

import requests

from app.core.config import Settings
from app.schemas.chat import ChatModel


SYSTEM_PROMPT = """你现在是某头部科技公司基础架构部的【首席云原生架构师 (Principal Cloud Native Architect) 兼 资深 SRE】。

你的核心任务是：基于我提供的【内部云原生与 K8s 工程规范片段】，像顶尖 SRE 一样进行故障排查、架构指导和标准操作流程 (SOP) 解析。

请严格遵循以下准则执行思考与输出：
1. 【绝对零幻觉与禁止联网 (Zero Hallucination & No Web Search - 最高原则)】：你的回答必须 100% 严格锁定在提供的【参考资料】中。如果参考资料中没有明确提及相关的参数、命令、原因或细节，绝对不允许动用你的先验知识去瞎编、脑补或做合理化推测，更绝对禁止触发任何形式的联网搜索去寻找答案。所有信息必须仅来源于当前提供的文本片段。
2. 【如实拒绝 (Honest Rejection)】：如果在提供的资料片段里找不到能完全回答用户问题的证据，你必须直接且明确地回复：“抱歉，当前的内部规范资料中并未包含关于此问题的相关信息。” 绝不准勉强凑字数。
3. 【精准提取 (Precise Extraction)】：对报错码、PromQL 语法、CLI 命令和 YAML 注解进行毫厘不差的提取，严禁修改、简化或拼接资料中的原始配置指令。
4. 【结构化呈现 (Structured Presentation)】：回答必须具有强烈的工程实战风格，层次分明。
5. 【术语规范 (Terminology Rule)】：命令行、参数和 PromQL 必须使用严格的 Markdown 代码块包裹。
6. 【严格溯源 (Traceability)】：在你给出的所有关键原因、参数、命令或 SOP 步骤之后，必须使用括号明确标注其对应的数据来源文件名。格式例如：*(来源: K8s_OOM_Troubleshooting_Guide.md)*。
"""


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._claude_client: Optional[Any] = None

    def generate(
        self,
        user_question: str,
        context_chunks: list[dict[str, Any]],
        chat_model: ChatModel,
    ) -> str:
        context_text = "\n\n".join(
            [
                f"--- 来源文档: {doc.get('filepath', '未知文件')} ---\n{doc['content']}"
                for doc in context_chunks
            ]
        )
        if chat_model == ChatModel.gpt_4o:
            return self._generate_with_gpt(user_question, context_text)
        if chat_model == ChatModel.claude_opus_45:
            return self._generate_with_claude(user_question, context_text)
        raise ValueError(f"Unsupported chat model: {chat_model}")

    def _generate_with_gpt(self, user_question: str, context_text: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "api-key": self.settings.nexus_api_key,
        }
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"【参考资料】:\n{context_text}\n\n【问题】: {user_question}",
                },
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        response = requests.post(
            self.settings.gpt4o_api_url,
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _generate_with_claude(self, user_question: str, context_text: str) -> str:
        client = self._get_claude_client()
        combined_prompt = f"{SYSTEM_PROMPT}\n\n【参考资料】:\n{context_text}\n\n【问题】: {user_question}"
        response = client.converse(
            modelId=self.settings.claude_model_id,
            messages=[{"role": "user", "content": [{"text": combined_prompt}]}],
        )
        return response["output"]["message"]["content"][0]["text"]

    def _get_claude_client(self) -> Any:
        if self._claude_client is not None:
            return self._claude_client

        if self.settings.aws_bearer_token_bedrock:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self.settings.aws_bearer_token_bedrock
        elif self.settings.nexus_api_key:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self.settings.nexus_api_key

        import boto3

        self._claude_client = boto3.client(
            service_name="bedrock-runtime",
            endpoint_url=self.settings.claude_endpoint,
            region_name="nexus",
        )
        return self._claude_client
