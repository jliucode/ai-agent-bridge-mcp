"""LLM-based local routing for MCP Proxy."""
import json
import asyncio
from typing import Optional
import httpx

from config import config


LOCAL_ROUTE_PROMPT = """本机收到一个远程任务，需要分配给本机 Agent。

## 任务信息
{task_json}

## 本机 Agent 列表
{local_agents_json}

## 选择标准
1. 项目相关性：项目名匹配的优先
2. 状态优先：IDLE > BUSY
3. 技能匹配：有所需技能的优先

输出 JSON：
{"selected_agent_id": "xxx", "reason": "选择理由"}
"""


RESULT_FORMAT_PROMPT = """将以下技术结果格式化为用户友好的摘要。

## 原始结果
{raw_result}

## 任务描述
{task_description}

## 输出要求
- 保留关键信息，省略冗余细节
- 用自然语言描述
- 突出重要发现或问题
- 控制在 200 字以内
"""


class LocalLLMRouter:
    """LLM for local agent selection and result formatting."""

    def __init__(self):
        self.enabled = config.llm_enabled
        self.provider = config.llm_provider
        self.api_key = config.dashscope_api_key
        self.model = config.dashscope_model_name
        self.timeout = 3.0

    async def select_local_agent(
        self,
        task: dict,
        local_agents: list[dict],
    ) -> Optional[dict]:
        """Select local agent with LLM."""
        if not self.enabled or not local_agents:
            return None

        prompt = LOCAL_ROUTE_PROMPT.format(
            task_json=json.dumps(task, ensure_ascii=False, indent=2),
            local_agents_json=json.dumps(local_agents, ensure_ascii=False, indent=2),
        )

        try:
            result = await self._call_llm(prompt)
            decision = json.loads(result)
            agent_id = decision.get("selected_agent_id")

            for a in local_agents:
                if a["agent_id"] == agent_id:
                    return a

            return None
        except Exception:
            return None

    async def format_result(self, raw_result: str, task_description: str) -> str:
        """Format technical result for user."""
        if not self.enabled:
            return raw_result

        prompt = RESULT_FORMAT_PROMPT.format(
            raw_result=raw_result[:1000],
            task_description=task_description,
        )

        try:
            return await self._call_llm(prompt)
        except Exception:
            return raw_result

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.provider == "qwen":
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model,
                "input": {"prompt": prompt},
                "parameters": {"result_format": "text"},
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, headers=headers, json=body, timeout=self.timeout
                )
                data = resp.json()
                return data["output"]["text"]

        raise ValueError(f"Unknown provider: {self.provider}")

    def fallback_select(self, local_agents: list[dict], task: dict) -> dict:
        """Fallback selection without LLM."""
        task_project = task.get("project")

        if task_project:
            matching = [a for a in local_agents if a["project"] == task_project]
            if matching:
                idle = [a for a in matching if a["status"] == "IDLE"]
                return idle[0] if idle else matching[0]

        idle = [a for a in local_agents if a["status"] == "IDLE"]
        return idle[0] if idle else local_agents[0]


local_llm_router = LocalLLMRouter()