from __future__ import annotations

import os
from typing import Any, Optional

import requests

from app.core.config import Settings
from app.schemas.chat import ChatModel


SYSTEM_PROMPT = """你是企业内部运维知识库的 RAG 问答助手，主要服务对象是运维新人、实习生和一线值班同学。

用户的问题可能很白话、不完整，甚至只描述现象。请先把白话问题翻译成工程语义，再基于【参考资料】回答。

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
5. 只基于【参考资料】回答；如果资料不足，请明确说明“当前资料中没有足够依据”，并指出缺少哪类资料。
6. 不要编造参考资料里没有的信息，不要联网搜索。
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
        prompt_template: str | None = None,
    ) -> str:
        system_prompt = prompt_template.strip() if prompt_template and prompt_template.strip() else SYSTEM_PROMPT
        context_text = "\n\n".join(
            [
                f"--- 来源文档: {doc.get('filepath', '未知文件')} ---\n{doc['content']}"
                for doc in context_chunks
            ]
        )
        if chat_model == ChatModel.gpt_4o:
            return self._generate_with_gpt(user_question, context_text, system_prompt)
        if chat_model == ChatModel.claude_opus_45:
            return self._generate_with_claude(user_question, context_text, system_prompt)
        raise ValueError(f"Unsupported chat model: {chat_model}")

    def _generate_with_gpt(self, user_question: str, context_text: str, system_prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "api-key": self.settings.nexus_api_key,
        }
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
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

    def _generate_with_claude(self, user_question: str, context_text: str, system_prompt: str) -> str:
        client = self._get_claude_client()
        combined_prompt = f"{system_prompt}\n\n【参考资料】:\n{context_text}\n\n【问题】: {user_question}"
        response = client.converse(
            modelId=self.settings.claude_model_id,
            messages=[{"role": "user", "content": [{"text": combined_prompt}]}],
        )
        return response["output"]["message"]["content"][0]["text"]

    def _get_claude_client(self) -> Any:
        if self._claude_client is not None:
            return self._claude_client

        bearer_token = self.settings.nexus_api_key.strip() or self.settings.aws_bearer_token_bedrock.strip()
        if bearer_token:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = bearer_token

        import boto3

        self._claude_client = boto3.client(
            service_name="bedrock-runtime",
            endpoint_url=self.settings.claude_endpoint,
            region_name="nexus",
        )
        return self._claude_client
